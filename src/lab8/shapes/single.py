"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import compute_compensation, get_claim_view, tool_cost


class _Trace:
    """Local alias so a crash can still flush. Wraps lab8.trace.Trace."""

    def __init__(self, run_id: str) -> None:
        from lab8.trace import Trace

        self._inner = Trace(run_id)

    def add(self, kind: str, payload: dict) -> None:
        self._inner.add(kind, payload)

    def write(self) -> str:
        return self._inner.write()

    @property
    def run_id(self) -> str:
        return self._inner.run_id


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
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
    run_id = make_run_id("single", claim_id, seed)
    trace = _Trace(run_id)

    # 1. Fetch claim view (dropping secrets and raw headers)
    budget.add_tool(tool_cost())
    claim_view = get_claim_view(conn, claim_id)
    if not claim_view.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )

    # 2. Missing order_id -> needs_info
    order_id = claim_view.get("order_id")
    if not order_id:
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        trace.add("decision", {"status": "needs_info"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_order_id",
        )

    principal_id = claim_view["principal_id"]

    # 3. Bounded ReAct loop with max_steps=8, worker=True (read-only tools only)
    gathered: dict[str, Any] = {
        "order_view": None,
        "refund_history": None,
    }
    step_count = 0

    def decide(seen: dict[str, Any]) -> dict[str, Any]:
        nonlocal step_count
        step_count += 1

        last_tool = seen.get("last_tool")
        last_result = seen.get("last_result")

        if last_tool == "lookup_order":
            gathered["order_view"] = last_result
            trace.add("react_observe", {"tool": "lookup_order", "result": last_result})
            if not last_result.get("visible"):
                complete(budget, seed=seed, purpose="draft", prompt="escalated")
                return {"final": {"status": "escalated", "reason": last_result.get("reason")}}
            # After inspecting order, check refund history
            complete(budget, seed=seed, purpose="think", prompt=f"step {step_count}: check refund history for {order_id}")
            trace.add("react_action", {"step": step_count, "action": "lookup_refund_history"})
            return {
                "tool": "lookup_refund_history",
                "args": {"order_id": order_id, "principal_id": principal_id},
            }

        if last_tool == "lookup_refund_history":
            gathered["refund_history"] = last_result
            trace.add("react_observe", {"tool": "lookup_refund_history", "result": last_result})
            complete(budget, seed=seed, purpose="draft", prompt=f"step {step_count}: investigation complete")
            return {"final": {"status": "ready"}}

        # Initial step: lookup order
        complete(budget, seed=seed, purpose="think", prompt=f"step {step_count}: lookup order {order_id}")
        trace.add("react_action", {"step": step_count, "action": "lookup_order"})
        return {
            "tool": "lookup_order",
            "args": {"order_id": order_id, "principal_id": principal_id},
        }

    observation = {"claim": claim_view}
    react_outcome = run_react(
        conn,
        budget,
        observation=observation,
        decide=decide,
        max_steps=8,
        worker=True,
    )

    final_payload = react_outcome.get("final", {})
    if react_outcome.get("stopped") == "step_cap":
        trace.add("decision", {"status": "failed", "error_reason": "step_cap"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="step_cap",
        )

    if final_payload.get("status") == "escalated":
        trace.add("decision", {"status": "escalated", "reason": final_payload.get("reason")})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="escalated",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final_payload.get("reason"),
        )

    # 4. Post-loop: calculate quote by code from order
    order_view = gathered.get("order_view")
    if not order_view or not order_view.get("visible") or "order" not in order_view:
        trace.add("decision", {"status": "failed", "error_reason": "missing_order_view"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_order_view",
        )

    order = dict(order_view["order"])
    budget.add_tool(tool_cost())
    quote_payload = compute_compensation(conn, order)
    proposal = int(quote_payload["amount_vnd"])
    trace.add("quote", quote_payload)
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")

    # 5. Quote <= 0: denied directly without writing
    if proposal <= 0:
        trace.add("decision", {"status": "denied", "reason": quote_payload.get("reason")})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="denied",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=quote_payload.get("reason"),
        )

    # 6. Quote > 0: call host durability.issue_refund with full quote and crash_at
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        trace.add("decision", {"status": status, "reason": outcome["reason"]})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=outcome["reason"],
        )

    trace.add("decision", {"status": "resolved"})
    return finish(
        conn,
        shape="single",
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )
