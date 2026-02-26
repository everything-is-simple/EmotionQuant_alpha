"""S6 全链路一致性契约测试。

验证 ConsistencyChecker 三层阈值：
- gate 链精确匹配
- score 链 <1e-6
- return 链 <1e-4
"""

from __future__ import annotations

from src.pipeline.consistency import (
    GATE_CHAIN_TOLERANCE,
    RETURN_CHAIN_TOLERANCE,
    SCORE_CHAIN_TOLERANCE,
    ConsistencyResult,
    FullConsistencyReport,
    check_gate_chain,
    check_return_chain,
    check_score_chain,
    run_full_consistency_check,
)


# ---------- gate chain: exact match ----------


def test_gate_chain_exact_match_passes() -> None:
    baseline = [
        {"stock_code": "000001", "final_gate": "PASS"},
        {"stock_code": "000002", "final_gate": "WARN"},
    ]
    replay = [
        {"stock_code": "000001", "final_gate": "PASS"},
        {"stock_code": "000002", "final_gate": "WARN"},
    ]
    result = check_gate_chain(baseline, replay)
    assert result.passed is True
    assert result.max_diff == 0.0
    assert result.tolerance == GATE_CHAIN_TOLERANCE


def test_gate_chain_mismatch_fails() -> None:
    baseline = [{"stock_code": "000001", "final_gate": "PASS"}]
    replay = [{"stock_code": "000001", "final_gate": "FAIL"}]
    result = check_gate_chain(baseline, replay)
    assert result.passed is False
    assert len(result.field_diffs) >= 1
    assert any(d["field"] == "final_gate" for d in result.field_diffs)


def test_gate_chain_row_count_mismatch_fails() -> None:
    baseline = [{"stock_code": "000001", "final_gate": "PASS"}]
    replay = []
    result = check_gate_chain(baseline, replay)
    assert result.passed is False
    assert any(d["field"] == "_row_count" for d in result.field_diffs)


# ---------- score chain: <1e-6 ----------


def test_score_chain_within_tolerance_passes() -> None:
    baseline = [{"stock_code": "000001", "final_score": 75.0000001}]
    replay = [{"stock_code": "000001", "final_score": 75.0000002}]
    result = check_score_chain(baseline, replay)
    assert result.passed is True
    assert result.max_diff < SCORE_CHAIN_TOLERANCE


def test_score_chain_exceeds_tolerance_fails() -> None:
    baseline = [{"stock_code": "000001", "final_score": 75.0}]
    replay = [{"stock_code": "000001", "final_score": 75.001}]
    result = check_score_chain(baseline, replay)
    assert result.passed is False
    assert result.max_diff > SCORE_CHAIN_TOLERANCE


# ---------- return chain: <1e-4 ----------


def test_return_chain_within_tolerance_passes() -> None:
    baseline = [{"stock_code": "000001", "total_return": 0.1234}]
    replay = [{"stock_code": "000001", "total_return": 0.12345}]
    result = check_return_chain(baseline, replay)
    assert result.passed is True
    assert result.max_diff < RETURN_CHAIN_TOLERANCE


def test_return_chain_exceeds_tolerance_fails() -> None:
    baseline = [{"stock_code": "000001", "total_return": 0.12}]
    replay = [{"stock_code": "000001", "total_return": 0.13}]
    result = check_return_chain(baseline, replay)
    assert result.passed is False
    assert result.max_diff > RETURN_CHAIN_TOLERANCE


# ---------- full consistency report ----------


def test_full_consistency_overall_pass() -> None:
    gates = [{"stock_code": "000001", "final_gate": "PASS"}]
    scores = [{"stock_code": "000001", "final_score": 70.0}]
    returns = [{"stock_code": "000001", "total_return": 0.05}]

    report = run_full_consistency_check(
        "20260226",
        baseline_gates=gates,
        replay_gates=gates,
        baseline_scores=scores,
        replay_scores=scores,
        baseline_returns=returns,
        replay_returns=returns,
    )
    assert isinstance(report, FullConsistencyReport)
    assert report.overall_passed is True
    assert report.gate_result.passed is True
    assert report.score_result.passed is True
    assert report.return_result.passed is True


def test_full_consistency_gate_fail_means_overall_fail() -> None:
    gates_a = [{"stock_code": "000001", "final_gate": "PASS"}]
    gates_b = [{"stock_code": "000001", "final_gate": "FAIL"}]
    scores = [{"stock_code": "000001", "final_score": 70.0}]
    returns = [{"stock_code": "000001", "total_return": 0.05}]

    report = run_full_consistency_check(
        "20260226",
        baseline_gates=gates_a,
        replay_gates=gates_b,
        baseline_scores=scores,
        replay_scores=scores,
        baseline_returns=returns,
        replay_returns=returns,
    )
    assert report.overall_passed is False
    assert report.gate_result.passed is False


def test_consistency_result_records_chain_name() -> None:
    result = check_gate_chain([], [])
    assert isinstance(result, ConsistencyResult)
    assert result.chain_name == "gate"

    result = check_score_chain([], [])
    assert result.chain_name == "score"

    result = check_return_chain([], [])
    assert result.chain_name == "return"


def test_none_values_treated_as_equal() -> None:
    baseline = [{"stock_code": "000001", "field_a": None}]
    replay = [{"stock_code": "000001", "field_a": None}]
    result = check_gate_chain(baseline, replay)
    assert result.passed is True


def test_none_vs_value_treated_as_mismatch() -> None:
    baseline = [{"stock_code": "000001", "field_a": None}]
    replay = [{"stock_code": "000001", "field_a": "PASS"}]
    result = check_gate_chain(baseline, replay)
    assert result.passed is False
