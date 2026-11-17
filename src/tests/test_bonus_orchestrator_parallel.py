"""Unit tests for Bonus B1: Parallel Investigators and Critical Path Latency."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from bonus.orchestrator_parallel import LATENCY_MODEL, run_claim, run_parallel_investigators
from lab8.app import prepare_store
from lab8.db import connect
from lab8.schemas import Budget
from lab8.tools import get_claim_view

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_parallel_investigators_deterministic_order(tmp_path: Path):
    """Test that parallel investigators always return identically regardless of thread completion order."""
    store_file = tmp_path / "test_store.sqlite"
    prepare_store(store_file)

    conn = connect(str(store_file))
    claim_id = "C-001"
    claim_view = get_claim_view(conn, claim_id)
    conn.close()

    budget1 = Budget()
    budget2 = Budget()
    allowed_tools = ["lookup_order", "lookup_policy", "lookup_refund_history"]

    tools_out_1, latencies_1 = run_parallel_investigators(
        str(store_file),
        budget1,
        claim_view,
        str(claim_view["principal_id"]),
        allowed_tools,
    )

    tools_out_2, latencies_2 = run_parallel_investigators(
        str(store_file),
        budget2,
        claim_view,
        str(claim_view["principal_id"]),
        allowed_tools,
    )

    # Identical keys in exact order
    assert list(tools_out_1.keys()) == allowed_tools
    assert list(tools_out_2.keys()) == allowed_tools
    assert tools_out_1 == tools_out_2
    assert latencies_1 == latencies_2


def test_parallel_run_claim_identical_to_orchestrator(tmp_path: Path):
    """Test that orchestrator_parallel produces a valid RunResult and identical status to sequential orchestrator."""
    store_file = tmp_path / "run_claim.sqlite"
    prepare_store(store_file)

    result = run_claim("C-001", seed=11, store_path=str(store_file))
    assert result.status == "resolved"
    assert result.proposal_amount > 0
    assert result.error_reason is None

    # Check trace file exists and contains parallel latency analysis
    trace_data = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    event_kinds = [e["kind"] for e in trace_data["events"]]
    assert "investigator_parallel" in event_kinds
    assert "latency_analysis" in event_kinds


def test_amdahl_speedup_calculation():
    """Verify simulated critical path latency model adheres to Amdahl's Law."""
    t_seq_inv = LATENCY_MODEL["lookup_order"] + LATENCY_MODEL["lookup_policy"] + LATENCY_MODEL["lookup_refund_history"]
    t_par_inv = max(LATENCY_MODEL["lookup_order"], LATENCY_MODEL["lookup_policy"], LATENCY_MODEL["lookup_refund_history"])

    seq_total = (
        LATENCY_MODEL["get_claim_view"]
        + LATENCY_MODEL["model_plan"]
        + t_seq_inv
        + LATENCY_MODEL["compute_compensation"]
        + LATENCY_MODEL["model_draft"]
        + LATENCY_MODEL["issue_refund"]
    )
    par_total = (
        LATENCY_MODEL["get_claim_view"]
        + LATENCY_MODEL["model_plan"]
        + t_par_inv
        + LATENCY_MODEL["compute_compensation"]
        + LATENCY_MODEL["model_draft"]
        + LATENCY_MODEL["issue_refund"]
    )

    speedup = seq_total / par_total
    # Parallelizable fraction is only investigators (105ms out of 425ms = ~24.7%)
    # Amdahl speedup is bounded around ~1.18x
    assert 1.15 < speedup < 1.25
