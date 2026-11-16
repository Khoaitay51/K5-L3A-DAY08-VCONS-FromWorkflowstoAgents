"""Ablation variants for R1 (Scaling / Investigator overhead) on top of Shape C.

Used with `python -m lab8.benchmark --extra-shape ...` to keep model, seed,
corpus, pricing, and evaluator identical while varying one component at a time.
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


def _run_orchestrator_variant(
    shape_name: str,
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
    use_llm: bool,
    extra_investigator_tools: bool,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _execute(
            conn,
            shape_name,
            claim_id,
            seed=seed,
            crash_at=crash_at,
            use_llm=use_llm,
            extra_investigator_tools=extra_investigator_tools,
        )
    finally:
        conn.close()


def _execute(
    conn: sqlite3.Connection,
    shape_name: str,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
    use_llm: bool,
    extra_investigator_tools: bool,
) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(shape_name, claim_id, seed))

    budget.add_tool(tool_cost())
    claim_view = get_claim_view(conn, claim_id)
    if not claim_view.get("found"):
        trace.add("error", {"reason": "unknown_claim", "claim_id": claim_id})
        return finish(
            conn,
            shape=shape_name,
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
    if use_llm:
        complete(
            budget,
            seed=seed,
            purpose="plan",
            prompt=f"claim_id={claim_id}|has_order={bool(order_id)}|ticket={claim_view['ticket']}",
        )
    trace.add("plan", {"claim_id": claim_id, "has_order_id": bool(order_id)})

    if not order_id:
        if use_llm:
            complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        trace.add("decision", {"status": "needs_info", "reason": "missing_order_id"})
        return finish(
            conn,
            shape=shape_name,
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_order_id",
        )

    allowed_tools = ["lookup_order"]
    if extra_investigator_tools:
        allowed_tools.extend(["lookup_policy", "lookup_refund_history"])

    handoff = make_handoff(
        request_id=f"REQ-{claim_id}-s{seed}",
        claim_id=claim_id,
        task="investigate_order",
        facts={},
        allowed_tools=allowed_tools,
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
    trace.add("investigator", {"lookup_order": safe_dump(order_view)})

    if not order_view.get("visible"):
        if use_llm:
            complete(budget, seed=seed, purpose="draft", prompt="escalated")
        trace.add("decision", {"status": "escalated", "reason": order_view.get("reason")})
        return finish(
            conn,
            shape=shape_name,
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

    if use_llm:
        complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")

    if proposal <= 0:
        trace.add("decision", {"status": "denied", "reason": quote_payload.get("reason")})
        return finish(
            conn,
            shape=shape_name,
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
        trace.add("host_outcome", {"ok": False, "status": status, "reason": outcome.get("reason")})
        return finish(
            conn,
            shape=shape_name,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=outcome.get("reason"),
        )

    trace.add("host_outcome", {"ok": True, "status": "resolved", "reason": outcome.get("reason")})
    return finish(
        conn,
        shape=shape_name,
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )


def orchestrator_min_tools(
    claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None
) -> RunResult:
    """Ablation 1: keep MockLLM plan/draft, drop redundant policy & refund_history investigator calls."""
    return _run_orchestrator_variant(
        "orchestrator_min_tools",
        claim_id,
        seed=seed,
        store_path=store_path,
        crash_at=crash_at,
        use_llm=True,
        extra_investigator_tools=False,
    )


def orchestrator_no_llm(
    claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None
) -> RunResult:
    """Ablation 2: also remove MockLLM plan/draft calls, keeping only the handoff + investigator boundary."""
    return _run_orchestrator_variant(
        "orchestrator_no_llm",
        claim_id,
        seed=seed,
        store_path=store_path,
        crash_at=crash_at,
        use_llm=False,
        extra_investigator_tools=False,
    )
