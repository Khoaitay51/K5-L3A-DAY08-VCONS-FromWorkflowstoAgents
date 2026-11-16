"""Shape C — orchestrator plus read-only investigators. Student work.

1. Build a handoff with `lab8.handoff.make_handoff`. Allowed tools are read-only.
   Never put parent_secret, raw headers, or the full claim row into facts.
2. `lab8.runtime.run_readonly_investigators` runs those tools.
3. The orchestrator quotes from the investigator's order view and calls
   `durability.issue_refund`. Investigators have no write registry.
   Pass the full quote; the host subtracts earlier refunds on the same order.
   `lookup_refund_history` is a read-only tool you may hand to an investigator.
4. Trace the sanitized handoff, not the parent context.

An LLM summary of the parent context is not a sanitizer. Use the allowlist.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import compute_compensation, get_claim_view, tool_cost
from lab8.trace import Trace


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    """Run Shape C (orchestrator + read-only investigators) for one claim."""
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id("orchestrator", claim_id, seed))

    budget.add_tool(tool_cost())
    claim_view = get_claim_view(conn, claim_id)
    if not claim_view.get("found"):
        trace.add("error", {"reason": "unknown_claim", "claim_id": claim_id})
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )

    principal_id = str(claim_view["principal_id"])
    order_id = claim_view.get("order_id")
    complete(
        budget,
        seed=seed,
        purpose="plan",
        prompt=f"claim_id={claim_id}|has_order={bool(order_id)}|ticket={claim_view['ticket']}",
    )
    trace.add("plan", {"claim_id": claim_id, "has_order_id": bool(order_id)})

    if not order_id:
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        trace.add("decision", {"status": "needs_info", "reason": "missing_order_id"})
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_order_id",
        )

    handoff = make_handoff(
        request_id=f"REQ-{claim_id}-s{seed}",
        claim_id=claim_id,
        task="investigate_order_policy_and_refund_history",
        facts={},
        allowed_tools=[
            "lookup_order",
            "lookup_policy",
            "lookup_refund_history",
        ],
    )
    trace.add("handoff", safe_dump(handoff))

    investigated = run_readonly_investigators(
        conn,
        budget,
        handoff,
        principal_id=principal_id,
    )
    tools_out = investigated.get("tools") or {}
    order_view = tools_out.get("lookup_order") or {}
    policy_view = tools_out.get("lookup_policy") or {}
    history_view = tools_out.get("lookup_refund_history") or {}

    trace.add(
        "investigator",
        {
            "claim_view": safe_dump(investigated.get("claim_view") or {}),
            "lookup_order": safe_dump(order_view),
            "policy_count": len(policy_view.get("policies") or []),
            "refund_history": safe_dump(history_view),
        },
    )

    if not order_view.get("visible"):
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        trace.add(
            "decision",
            {"status": "escalated", "reason": order_view.get("reason")},
        )
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status="escalated",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=order_view.get("reason"),
        )

    order = dict(order_view["order"])
    budget.add_tool(tool_cost())
    quote_payload = compute_compensation(conn, order)
    proposal = int(quote_payload["amount_vnd"])
    trace.add("quote", safe_dump(quote_payload))

    prior_refunded = int(history_view.get("refunded_vnd") or 0)
    complete(
        budget,
        seed=seed,
        purpose="draft",
        prompt=f"proposal={proposal}|prior_refunded={prior_refunded}",
    )

    if proposal <= 0:
        trace.add(
            "decision",
            {
                "status": "denied",
                "reason": quote_payload.get("reason"),
                "proposal_amount": 0,
            },
        )
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status="denied",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=quote_payload.get("reason"),
        )

    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        trace.add(
            "host_outcome",
            {
                "ok": False,
                "status": status,
                "reason": outcome.get("reason"),
                "conflict": bool(outcome.get("conflict")),
            },
        )
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=outcome.get("reason"),
        )

    trace.add(
        "host_outcome",
        {"ok": True, "status": "resolved", "reason": outcome.get("reason")},
    )
    return finish(
        conn,
        shape="orchestrator",
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )
