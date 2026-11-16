import json

from lab8.shapes.workflow import run_claim


def test_unknown_claim_returns_failed_with_fresh_trace(public_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_claim("C-UNKNOWN", seed=11, store_path=str(public_db))
    assert result.status == "failed"
    assert result.error_reason == "unknown_claim"
    assert result.proposal_amount == 0
    assert result.refund_effects == []
    with open(result.trace_path, encoding="utf-8") as trace_file:
        trace = json.load(trace_file)
    assert trace["run_id"] == result.run_id
    assert isinstance(trace["events"], list)
