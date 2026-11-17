"""Test suite for Bonus Topic B7: Grader Audit using Metamorphic Relations."""

from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
import random

import pytest
from lab8.compensation import quote

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "grader_audit" / "fixtures"


def test_business_rule_metamorphic_delay():
    """Verify business rule flip: delay_days=2 vs delay_days=3 under SHIP-LATE-03."""
    fixture = json.loads((FIXTURES_DIR / "metamorphic_claim_delay.json").read_text(encoding="utf-8"))
    order_a = fixture["a"]["order"]
    order_b = fixture["b"]["order"]
    policies = fixture["policies"]
    as_of = fixture["as_of"]

    qa = quote(order_a, policies, as_of=as_of)
    qb = quote(order_b, policies, as_of=as_of)

    # 2 days: ineligible -> 0 VND
    assert qa.amount_vnd == 0
    assert qa.reason == "no_entitlement"

    # 3 days: eligible -> 35,000 VND shipping fee refunded
    assert qb.amount_vnd == 35000
    assert qb.reason == "entitled"
    assert "SHIP-LATE-03" in qb.clause_ids


@pytest.mark.parametrize("grader_name", ["grader_a", "grader_b", "grader_c"])
def test_metamorphic_infra_relation(grader_name: str):
    """Infra error trials must NOT be counted against shape pass rate."""
    mod = importlib.import_module(f"grader_audit.{grader_name}")
    fixture = json.loads((FIXTURES_DIR / "metamorphic_infra.json").read_text(encoding="utf-8"))

    ra = mod.summarize(fixture["a"])["workflow"]
    rb = mod.summarize(fixture["b"])["workflow"]

    if grader_name == "grader_c":
        # Grader C is defective: counts infra_error as failed shape execution
        assert rb["pass_rate"] < ra["pass_rate"], "grader_c must exhibit known defect on infra_error"
        assert rb["graded_trials"] > ra["graded_trials"]
    else:
        # Grader A and B correctly isolate infra errors
        assert ra["pass_rate"] == rb["pass_rate"]
        assert ra["graded_trials"] == rb["graded_trials"]


@pytest.mark.parametrize("grader_name", ["grader_a", "grader_b", "grader_c"])
def test_metamorphic_duplicate_relation(grader_name: str):
    """Duplicating trial list must double totals and preserve per-success rates."""
    mod = importlib.import_module(f"grader_audit.{grader_name}")
    fixture = json.loads((FIXTURES_DIR / "metamorphic_duplicate.json").read_text(encoding="utf-8"))

    ra = mod.summarize(fixture["a"])["workflow"]
    rb = mod.summarize(fixture["b"])["workflow"]

    assert ra["pass_rate"] == rb["pass_rate"]
    assert rb["trials"] == 2 * ra["trials"]
    assert rb["successes"] == 2 * ra["successes"]

    if grader_name == "grader_a":
        # Grader A is defective: double-counts costs on first-seen claim_id, not doubling cleanly
        assert not (abs(rb["total_simulated_cost_vnd"] - 2.0 * ra["total_simulated_cost_vnd"]) < 1e-4)
        assert not (abs(ra["cost_per_success_vnd"] - rb["cost_per_success_vnd"]) < 1e-4)
    else:
        # Grader B and C satisfy duplicate invariance on cost
        assert abs(rb["total_simulated_cost_vnd"] - 2.0 * ra["total_simulated_cost_vnd"]) < 1e-4
        assert abs(ra["cost_per_success_vnd"] - rb["cost_per_success_vnd"]) < 1e-4


@pytest.mark.parametrize("grader_name", ["grader_a", "grader_b", "grader_c"])
def test_new_metamorphic_order_permutation_invariance(grader_name: str):
    """Proposed new metamorphic relation: Shuffling the trial sequence must not alter aggregated results."""
    mod = importlib.import_module(f"grader_audit.{grader_name}")
    fixture = json.loads((FIXTURES_DIR / "metamorphic_infra.json").read_text(encoding="utf-8"))

    trials_orig = fixture["a"]
    trials_shuffled = copy.deepcopy(trials_orig)
    random.Random(1337).shuffle(trials_shuffled)

    ra = mod.summarize(trials_orig)["workflow"]
    rb = mod.summarize(trials_shuffled)["workflow"]

    if grader_name == "grader_a":
        # Grader A's cost depends on the traversal order of trials (which seed of a claim is seen first)
        assert ra["total_simulated_cost_vnd"] != rb["total_simulated_cost_vnd"]
    else:
        assert ra["pass_rate"] == rb["pass_rate"]
        assert abs(ra["total_simulated_cost_vnd"] - rb["total_simulated_cost_vnd"]) < 1e-4
        assert abs(ra["cost_per_success_vnd"] - rb["cost_per_success_vnd"]) < 1e-4


def test_grader_b_is_sound():
    """Verify that grader_b passes all metamorphic invariant checks without defect."""
    mod = importlib.import_module("grader_audit.grader_b")
    f_infra = json.loads((FIXTURES_DIR / "metamorphic_infra.json").read_text(encoding="utf-8"))
    f_dup = json.loads((FIXTURES_DIR / "metamorphic_duplicate.json").read_text(encoding="utf-8"))

    # Infra check
    r_infra_a = mod.summarize(f_infra["a"])["workflow"]
    r_infra_b = mod.summarize(f_infra["b"])["workflow"]
    assert r_infra_a["pass_rate"] == r_infra_b["pass_rate"]

    # Duplicate check
    r_dup_a = mod.summarize(f_dup["a"])["workflow"]
    r_dup_b = mod.summarize(f_dup["b"])["workflow"]
    assert abs(r_dup_b["total_simulated_cost_vnd"] - 2.0 * r_dup_a["total_simulated_cost_vnd"]) < 1e-4
    assert abs(r_dup_a["cost_per_success_vnd"] - r_dup_b["cost_per_success_vnd"]) < 1e-4
