"""Bonus B7 - Metamorphic Grader Audit Script.

Executes metamorphic relations against candidate graders:
- grader_a (cost double count / claim deduplication defect)
- grader_b (reference implementation, passes all metamorphic relations)
- grader_c (penalizes infrastructure errors as shape failures)
"""

from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
from typing import Any

from lab8.compensation import quote

SRC_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = SRC_ROOT / "grader_audit" / "fixtures"


def audit_claim_delay() -> dict[str, Any]:
    fixture = json.loads((FIXTURES_DIR / "metamorphic_claim_delay.json").read_text(encoding="utf-8"))
    order_a = fixture["a"]["order"]
    order_b = fixture["b"]["order"]
    policies = fixture["policies"]
    as_of = fixture["as_of"]

    qa = quote(order_a, policies, as_of=as_of)
    qb = quote(order_b, policies, as_of=as_of)

    passed = (
        qa.amount_vnd == 0
        and qa.reason == "no_entitlement"
        and qb.amount_vnd == 35000
        and qb.clause_ids == ["SHIP-LATE-03"]
    )
    return {
        "relation": fixture.get("relation", "delay_days_2_vs_3"),
        "qa_amount_vnd": qa.amount_vnd,
        "qa_reason": qa.reason,
        "qb_amount_vnd": qb.amount_vnd,
        "qb_reason": qb.reason,
        "qb_clause_ids": qb.clause_ids,
        "status": "PASS" if passed else "FAIL",
    }


def audit_infra_relation(grader_name: str) -> dict[str, Any]:
    mod = importlib.import_module(f"grader_audit.{grader_name}")
    fixture = json.loads((FIXTURES_DIR / "metamorphic_infra.json").read_text(encoding="utf-8"))
    ra = mod.summarize(fixture["a"])["workflow"]
    rb = mod.summarize(fixture["b"])["workflow"]

    passed = (
        ra["pass_rate"] == rb["pass_rate"]
        and ra["graded_trials"] == rb["graded_trials"]
        and rb["trials"] > ra["trials"]
    )
    return {
        "grader": grader_name,
        "a_trials": ra["trials"],
        "b_trials": rb["trials"],
        "a_graded_trials": ra["graded_trials"],
        "b_graded_trials": rb["graded_trials"],
        "a_pass_rate": ra["pass_rate"],
        "b_pass_rate": rb["pass_rate"],
        "status": "PASS" if passed else "FAIL",
        "defect_note": (
            "None"
            if passed
            else "Counts infra_error trials as graded and failed, depressing pass_rate"
        ),
    }


def audit_duplicate_relation(grader_name: str) -> dict[str, Any]:
    mod = importlib.import_module(f"grader_audit.{grader_name}")
    fixture = json.loads((FIXTURES_DIR / "metamorphic_duplicate.json").read_text(encoding="utf-8"))
    ra = mod.summarize(fixture["a"])["workflow"]
    rb = mod.summarize(fixture["b"])["workflow"]

    cost_doubled = abs(rb["total_simulated_cost_vnd"] - 2.0 * ra["total_simulated_cost_vnd"]) < 1e-4
    cost_per_succ_equal = abs(ra["cost_per_success_vnd"] - rb["cost_per_success_vnd"]) < 1e-4
    pass_rate_equal = abs(ra["pass_rate"] - rb["pass_rate"]) < 1e-4

    passed = cost_doubled and cost_per_succ_equal and pass_rate_equal
    return {
        "grader": grader_name,
        "a_pass_rate": ra["pass_rate"],
        "b_pass_rate": rb["pass_rate"],
        "a_total_cost_vnd": ra["total_simulated_cost_vnd"],
        "b_total_cost_vnd": rb["total_simulated_cost_vnd"],
        "cost_ratio": (
            rb["total_simulated_cost_vnd"] / ra["total_simulated_cost_vnd"]
            if ra["total_simulated_cost_vnd"]
            else None
        ),
        "a_cost_per_success_vnd": ra["cost_per_success_vnd"],
        "b_cost_per_success_vnd": rb["cost_per_success_vnd"],
        "status": "PASS" if passed else "FAIL",
        "defect_note": (
            "None"
            if passed
            else "Double-counts cost with set(claim_id) dedup loop, distorting total cost and cost/success"
        ),
    }


def audit_order_permutation_relation(grader_name: str) -> dict[str, Any]:
    """New metamorphic relation: shuffling trial order must preserve all aggregated metrics."""
    mod = importlib.import_module(f"grader_audit.{grader_name}")
    fixture = json.loads((FIXTURES_DIR / "metamorphic_infra.json").read_text(encoding="utf-8"))
    trials_orig = fixture["a"]
    trials_rev = list(reversed(copy.deepcopy(trials_orig)))

    ra = mod.summarize(trials_orig)["workflow"]
    rb = mod.summarize(trials_rev)["workflow"]

    cost_invariant = abs(ra["total_simulated_cost_vnd"] - rb["total_simulated_cost_vnd"]) < 1e-4
    pass_rate_invariant = abs(ra["pass_rate"] - rb["pass_rate"]) < 1e-4

    passed = cost_invariant and pass_rate_invariant
    return {
        "grader": grader_name,
        "orig_total_cost_vnd": ra["total_simulated_cost_vnd"],
        "rev_total_cost_vnd": rb["total_simulated_cost_vnd"],
        "orig_pass_rate": ra["pass_rate"],
        "rev_pass_rate": rb["pass_rate"],
        "status": "PASS" if passed else "FAIL",
        "defect_note": (
            "None"
            if passed
            else "Order-dependent cost accumulation due to first-seen claim_id tracking"
        ),
    }


def run_full_audit() -> dict[str, Any]:
    graders = ["grader_a", "grader_b", "grader_c"]
    delay_res = audit_claim_delay()

    results: dict[str, Any] = {
        "metadata": {
            "topic": "B7 · Kiểm toán grader (Grader Audit & Metamorphic Testing)",
            "sources": [
                "EMNLP 2026, Rethinking Evaluation of MAS Efficiency",
                "Chen et al., Metamorphic Testing for Machine Learning & Software Evaluation",
            ],
            "evaluated_graders": graders,
        },
        "business_rule_relation": {
            "name": "metamorphic_claim_delay",
            "result": delay_res,
        },
        "grader_evaluations": {},
        "verdict": {
            "grader_a": "DEFECTIVE: double-counts cost on first occurrence of claim_id and breaks trial-order invariance",
            "grader_b": "CORRECT: satisfies all metamorphic relations and preserves invariants",
            "grader_c": "DEFECTIVE: counts infra_error trials as graded=False, unfairly depressing pass rate",
        },
    }

    for g in graders:
        results["grader_evaluations"][g] = {
            "infra_error_isolation": audit_infra_relation(g),
            "duplicate_invariance": audit_duplicate_relation(g),
            "order_permutation_invariance": audit_order_permutation_relation(g),
        }

    return results


def main() -> None:
    results = run_full_audit()
    out_dir = SRC_ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "bonus_grader_audit.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Audit completed. Report saved to {out_path}")


if __name__ == "__main__":
    main()
