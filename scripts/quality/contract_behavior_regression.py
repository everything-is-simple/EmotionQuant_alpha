#!/usr/bin/env python3
"""
Behavior-level regression checks for naming/contracts critical boundaries.

These checks are scenario-based (not just text pattern checks) and pin down
the execution semantics required by design docs.
"""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_CONTRACT_VERSION = "nc-v1"
HOLD_RECOMMENDATION = "HOLD"
RECOMMENDATION_RANK = {
    "AVOID": 0,
    "SELL": 1,
    "HOLD": 2,
    "BUY": 3,
    "STRONG_BUY": 4,
}
TREND_TO_DIRECTION = {"up": "bullish", "down": "bearish", "sideways": "neutral"}


@dataclass(frozen=True)
class ExecutionDecision:
    executable: bool
    state: str
    degraded: bool


def cap_recommendation_for_unknown(mss_cycle: str, recommendation: str) -> str:
    """
    Integration contract:
    - when mss_cycle=unknown, recommendation upper bound is HOLD.
    """
    rank = RECOMMENDATION_RANK.get(recommendation)
    if rank is None:
        raise ValueError(f"unknown recommendation={recommendation}")
    if mss_cycle == "unknown" and rank > RECOMMENDATION_RANK[HOLD_RECOMMENDATION]:
        return HOLD_RECOMMENDATION
    return recommendation


def consistency_factor_for_triplet(
    mss_trend: str,
    irs_recommendation: str,
    pas_direction: str,
) -> float:
    """
    Integration contract:
    - when MSS/IRS/PAS are all neutral (sideways/HOLD/neutral), factor=1.0.
    """
    mss_direction = TREND_TO_DIRECTION.get(mss_trend)
    if mss_direction is None:
        raise ValueError(f"unknown trend={mss_trend}")
    if irs_recommendation not in {"STRONG_BUY", "BUY", "HOLD", "SELL", "AVOID"}:
        raise ValueError(f"unknown irs_recommendation={irs_recommendation}")
    if pas_direction not in {"bullish", "bearish", "neutral"}:
        raise ValueError(f"unknown pas_direction={pas_direction}")

    irs_direction = (
        "bullish"
        if irs_recommendation in {"STRONG_BUY", "BUY"}
        else ("bearish" if irs_recommendation in {"SELL", "AVOID"} else "neutral")
    )
    return 1.0 if mss_direction == irs_direction == pas_direction == "neutral" else 0.0


def evaluate_execution_boundary(
    *,
    final_gate: str,
    contract_version: str,
    risk_reward_ratio: float,
) -> ExecutionDecision:
    """
    Trading/Backtest contract:
    - contract_version mismatch blocks immediately.
    - Gate=FAIL blocks.
    - Gate=WARN can continue (degraded path).
    - risk_reward_ratio < 1.0 is filtered; risk_reward_ratio == 1.0 is allowed.
    """
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        return ExecutionDecision(False, "blocked_contract_mismatch", False)
    if final_gate == "FAIL":
        return ExecutionDecision(False, "blocked_gate_fail", False)
    if risk_reward_ratio < 1.0:
        return ExecutionDecision(False, "filtered_rr_lt_1", final_gate == "WARN")
    if final_gate == "WARN":
        return ExecutionDecision(True, "warn_gate_allowed", True)
    if final_gate == "PASS":
        return ExecutionDecision(True, "pass_gate_allowed", False)
    raise ValueError(f"unknown final_gate={final_gate}")


def run_behavior_regression() -> list[str]:
    violations: list[str] = []

    if cap_recommendation_for_unknown("unknown", "STRONG_BUY") != "HOLD":
        violations.append("unknown cycle must cap STRONG_BUY to HOLD")

    if cap_recommendation_for_unknown("emergence", "BUY") != "BUY":
        violations.append("non-unknown cycle should keep BUY unchanged")

    if consistency_factor_for_triplet("sideways", "HOLD", "neutral") != 1.0:
        violations.append("sideways/HOLD/neutral must yield consistency_factor=1.0")

    rr_eq_one = evaluate_execution_boundary(
        final_gate="PASS",
        contract_version=SUPPORTED_CONTRACT_VERSION,
        risk_reward_ratio=1.0,
    )
    if not rr_eq_one.executable:
        violations.append("risk_reward_ratio == 1.0 must be executable")

    warn_case = evaluate_execution_boundary(
        final_gate="WARN",
        contract_version=SUPPORTED_CONTRACT_VERSION,
        risk_reward_ratio=1.1,
    )
    if not (warn_case.executable and warn_case.degraded):
        violations.append("Gate=WARN should execute in degraded mode")

    fail_case = evaluate_execution_boundary(
        final_gate="FAIL",
        contract_version=SUPPORTED_CONTRACT_VERSION,
        risk_reward_ratio=2.0,
    )
    if fail_case.executable or fail_case.state != "blocked_gate_fail":
        violations.append("Gate=FAIL must block execution")

    mismatch_case = evaluate_execution_boundary(
        final_gate="PASS",
        contract_version="nc-v0",
        risk_reward_ratio=2.0,
    )
    if mismatch_case.executable or mismatch_case.state != "blocked_contract_mismatch":
        violations.append("contract_version mismatch must block execution")

    return violations


def check_contract_behavior_regression() -> int:
    violations = run_behavior_regression()
    if not violations:
        print("[contracts-behavior] pass (7 checks)")
        return 0
    print(f"[contracts-behavior] failed ({len(violations)} violations)")
    for item in violations:
        print(f"  - {item}")
    return 1

