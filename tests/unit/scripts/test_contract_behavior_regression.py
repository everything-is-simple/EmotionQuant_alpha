from __future__ import annotations

from scripts.quality.contract_behavior_regression import (
    SUPPORTED_CONTRACT_VERSION,
    cap_recommendation_for_unknown,
    check_contract_behavior_regression,
    consistency_factor_for_triplet,
    evaluate_execution_boundary,
)


def test_unknown_cycle_caps_positive_recommendation_to_hold() -> None:
    assert cap_recommendation_for_unknown("unknown", "STRONG_BUY") == "HOLD"
    assert cap_recommendation_for_unknown("unknown", "BUY") == "HOLD"


def test_sideways_hold_neutral_triplet_returns_neutral_consistency() -> None:
    assert consistency_factor_for_triplet("sideways", "HOLD", "neutral") == 1.0


def test_rr_equal_one_is_executable() -> None:
    decision = evaluate_execution_boundary(
        final_gate="PASS",
        contract_version=SUPPORTED_CONTRACT_VERSION,
        risk_reward_ratio=1.0,
    )
    assert decision.executable is True
    assert decision.state == "pass_gate_allowed"


def test_warn_is_degraded_but_not_blocked() -> None:
    decision = evaluate_execution_boundary(
        final_gate="WARN",
        contract_version=SUPPORTED_CONTRACT_VERSION,
        risk_reward_ratio=1.2,
    )
    assert decision.executable is True
    assert decision.degraded is True
    assert decision.state == "warn_gate_allowed"


def test_fail_gate_blocks_execution() -> None:
    decision = evaluate_execution_boundary(
        final_gate="FAIL",
        contract_version=SUPPORTED_CONTRACT_VERSION,
        risk_reward_ratio=2.0,
    )
    assert decision.executable is False
    assert decision.state == "blocked_gate_fail"


def test_contract_version_mismatch_blocks_execution() -> None:
    decision = evaluate_execution_boundary(
        final_gate="PASS",
        contract_version="nc-v0",
        risk_reward_ratio=2.0,
    )
    assert decision.executable is False
    assert decision.state == "blocked_contract_mismatch"


def test_behavior_regression_suite_passes() -> None:
    assert check_contract_behavior_regression() == 0

