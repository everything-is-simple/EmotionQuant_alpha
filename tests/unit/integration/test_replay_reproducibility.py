"""S6 重跑可复现性测试。

验证 eq run-all CLI 入口解析和一致性检查的幂等特性。
"""

from __future__ import annotations

import math

from src.pipeline.consistency import (
    GATE_CHAIN_TOLERANCE,
    RETURN_CHAIN_TOLERANCE,
    SCORE_CHAIN_TOLERANCE,
    FullConsistencyReport,
    check_gate_chain,
    check_score_chain,
    run_full_consistency_check,
)
from src.pipeline.main import build_parser


# ---------- CLI parser ----------


def test_run_all_subcommand_registered() -> None:
    parser = build_parser()
    args = parser.parse_args(["run-all", "--date", "20260226"])
    assert args.command == "run-all"
    assert args.date == "20260226"
    assert args.skip_consistency is False


def test_run_all_skip_consistency_flag() -> None:
    parser = build_parser()
    args = parser.parse_args(["run-all", "--date", "20260226", "--skip-consistency"])
    assert args.skip_consistency is True


# ---------- idempotent replay ----------


def test_identical_replay_all_chains_pass() -> None:
    """同数据两次检查 = 全通过。"""
    gates = [
        {"stock_code": "000001", "final_gate": "PASS"},
        {"stock_code": "300001", "final_gate": "WARN"},
    ]
    scores = [
        {"stock_code": "000001", "final_score": 72.5},
        {"stock_code": "300001", "final_score": 55.0},
    ]
    returns = [
        {"stock_code": "000001", "total_return": 0.0321},
        {"stock_code": "300001", "total_return": -0.0150},
    ]
    report = run_full_consistency_check(
        "20260226",
        baseline_gates=gates,
        replay_gates=gates,
        baseline_scores=scores,
        replay_scores=scores,
        baseline_returns=returns,
        replay_returns=returns,
    )
    assert report.overall_passed is True
    assert report.gate_result.max_diff == 0.0
    assert report.score_result.max_diff == 0.0
    assert report.return_result.max_diff == 0.0


def test_empty_chains_pass_idempotent() -> None:
    """空数据两次检查 = 全通过。"""
    report = run_full_consistency_check(
        "20260226",
        baseline_gates=[],
        replay_gates=[],
        baseline_scores=[],
        replay_scores=[],
        baseline_returns=[],
        replay_returns=[],
    )
    assert report.overall_passed is True


# ---------- threshold boundary ----------


def test_score_chain_at_exact_boundary_passes() -> None:
    """差异恰好 = 1e-6 时应通过。"""
    baseline = [{"stock_code": "000001", "final_score": 70.0}]
    replay = [{"stock_code": "000001", "final_score": 70.0 + 1e-6}]
    result = check_score_chain(baseline, replay)
    assert result.passed is True


def test_score_chain_just_above_boundary_fails() -> None:
    """差异略超 1e-6 应失败。"""
    baseline = [{"stock_code": "000001", "final_score": 70.0}]
    replay = [{"stock_code": "000001", "final_score": 70.0 + 2e-6}]
    result = check_score_chain(baseline, replay)
    assert result.passed is False


def test_nan_values_treated_as_equal() -> None:
    """NaN == NaN 在一致性检查中视为相等。"""
    baseline = [{"stock_code": "000001", "final_score": float("nan")}]
    replay = [{"stock_code": "000001", "final_score": float("nan")}]
    result = check_score_chain(baseline, replay)
    assert result.passed is True


def test_gate_chain_tolerance_is_zero() -> None:
    """gate 链必须精确匹配，容差 = 0。"""
    assert GATE_CHAIN_TOLERANCE == 0.0


def test_score_chain_tolerance_is_1e6() -> None:
    assert SCORE_CHAIN_TOLERANCE == 1e-6


def test_return_chain_tolerance_is_1e4() -> None:
    assert RETURN_CHAIN_TOLERANCE == 1e-4


# ---------- multi-field diff tracking ----------


def test_multiple_field_diffs_tracked() -> None:
    baseline = [{"stock_code": "000001", "final_gate": "PASS", "extra": "A"}]
    replay = [{"stock_code": "000001", "final_gate": "FAIL", "extra": "B"}]
    result = check_gate_chain(baseline, replay)
    assert result.passed is False
    diff_fields = {d["field"] for d in result.field_diffs}
    assert "final_gate" in diff_fields
    assert "extra" in diff_fields


def test_report_trade_date_preserved() -> None:
    report = run_full_consistency_check(
        "20260301",
        baseline_gates=[],
        replay_gates=[],
        baseline_scores=[],
        replay_scores=[],
        baseline_returns=[],
        replay_returns=[],
    )
    assert report.trade_date == "20260301"
