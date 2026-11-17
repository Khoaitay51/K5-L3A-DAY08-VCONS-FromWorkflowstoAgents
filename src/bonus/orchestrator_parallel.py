"""Bonus B1: Parallel Read-only Investigators and Simulated Latency / Critical Path.

Source: Google Research 2026, Towards a Science of Scaling Agent Systems
(Slide 15, 24, 33, 41)

Implements:
1. ThreadPoolExecutor to run independent read-only investigators in parallel.
   Each thread opens its own SQLite connection to prevent SQLite multithreading corruption.
   Results are joined deterministically.
2. Simulated Latency Model (latency.yaml) calculating Critical Path DAG without time.sleep.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import compute_compensation, get_claim_view, lookup_order, lookup_policy, lookup_refund_history, tool_cost
from lab8.trace import Trace

# Simulated latency in milliseconds from latency model
LATENCY_MODEL = {
    "get_claim_view": 25.0,
    "lookup_order": 40.0,
    "lookup_policy": 35.0,
    "lookup_refund_history": 30.0,
    "compute_compensation": 15.0,
    "model_plan": 120.0,
    "model_draft": 110.0,
    "issue_refund": 50.0,
}


def _run_single_investigator(store_path: str, tool_name: str, args: dict[str, Any]) -> tuple[str, Any]:
    """Execute a single read-only investigator query in its own SQLite connection."""
    conn = connect(store_path)
    try:
        if tool_name == "lookup_order":
            return tool_name, lookup_order(conn, args.get("order_id"), args["principal_id"])
        elif tool_name == "lookup_policy":
            return tool_name, lookup_policy(conn)
        elif tool_name == "lookup_refund_history":
            return tool_name, lookup_refund_history(conn, args.get("order_id"), args["principal_id"])
        raise ValueError(f"Unsupported parallel tool: {tool_name}")
    finally:
        conn.close()


def run_parallel_investigators(
    store_path: str,
    budget: Budget,
    claim: dict[str, Any],
    principal_id: str,
    allowed_tools: list[str],
) -> tuple[dict[str, Any], dict[str, float]]:
    """Run independent read-only tools concurrently using ThreadPoolExecutor."""
    futures = {}
    tools_out = {}
    latencies = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        for name in allowed_tools:
            budget.add_tool(tool_cost())
            args = {"order_id": claim.get("order_id"), "principal_id": principal_id}
            futures[name] = executor.submit(_run_single_investigator, store_path, name, args)

        # Deterministic join in order of allowed_tools
        for name in allowed_tools:
            _, result = futures[name].result()
            tools_out[name] = result
            latencies[name] = LATENCY_MODEL.get(name, 30.0)

    return tools_out, latencies


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    """Run Orchestrator with parallel investigator execution and critical-path latency calculation."""
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, store_path=store_path, crash_at=crash_at)
    finally:
        conn.close()


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id("orchestrator_parallel", claim_id, seed))

    # Step 1: get claim view
    budget.add_tool(tool_cost())
    claim_view = get_claim_view(conn, claim_id)
    if not claim_view.get("found"):
        trace.add("error", {"reason": "unknown_claim", "claim_id": claim_id})
        return finish(
            conn,
            shape="orchestrator_parallel",
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

    # Step 2: Planning model call
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
            shape="orchestrator_parallel",
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_order_id",
        )

    # Step 3: Handoff & Parallel Investigator Execution
    allowed_tools = ["lookup_order", "lookup_policy", "lookup_refund_history"]
    handoff = make_handoff(
        request_id=f"REQ-{claim_id}-s{seed}",
        claim_id=claim_id,
        task="investigate_order_policy_and_refund_history_parallel",
        facts={},
        allowed_tools=allowed_tools,
    )
    trace.add("handoff", safe_dump(handoff))

    tools_out, latencies = run_parallel_investigators(
        store_path,
        budget,
        claim_view,
        principal_id,
        allowed_tools,
    )

    order_view = tools_out.get("lookup_order") or {}
    policy_view = tools_out.get("lookup_policy") or {}
    history_view = tools_out.get("lookup_refund_history") or {}

    trace.add(
        "investigator_parallel",
        {
            "claim_view": safe_dump(claim_view),
            "lookup_order": safe_dump(order_view),
            "policy_count": len(policy_view.get("policies") or []),
            "refund_history": safe_dump(history_view),
            "parallel_latencies": latencies,
        },
    )

    if not order_view.get("visible"):
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        trace.add("decision", {"status": "escalated", "reason": order_view.get("reason")})
        return finish(
            conn,
            shape="orchestrator_parallel",
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

    # Calculate Critical Path vs Sequential Latency
    t_seq_investigators = sum(latencies.values())
    t_par_investigators = max(latencies.values())
    critical_path_ms = (
        LATENCY_MODEL["get_claim_view"]
        + LATENCY_MODEL["model_plan"]
        + t_par_investigators
        + LATENCY_MODEL["compute_compensation"]
        + LATENCY_MODEL["model_draft"]
        + LATENCY_MODEL["issue_refund"]
    )
    sequential_latency_ms = (
        LATENCY_MODEL["get_claim_view"]
        + LATENCY_MODEL["model_plan"]
        + t_seq_investigators
        + LATENCY_MODEL["compute_compensation"]
        + LATENCY_MODEL["model_draft"]
        + LATENCY_MODEL["issue_refund"]
    )

    trace.add(
        "latency_analysis",
        {
            "sequential_latency_ms": sequential_latency_ms,
            "critical_path_ms": critical_path_ms,
            "speedup_ratio": round(sequential_latency_ms / critical_path_ms, 3),
        },
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
            shape="orchestrator_parallel",
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
            shape="orchestrator_parallel",
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
        shape="orchestrator_parallel",
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )
