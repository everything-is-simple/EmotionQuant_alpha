"""S6 一致性检查器（ConsistencyChecker）。

全链路重跑后，对比两次运行产物的一致性。
三层阈值：gate 链精确匹配 / score 链 <1e-6 / return 链 <1e-4。

与 docs/design/enhancements/eq-improvement-plan-core-frozen.md ENH-08 对齐。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# DESIGN_TRACE:
# - docs/design/enhancements/eq-improvement-plan-core-frozen.md (ENH-08 稳定化闭环)
# - Governance/SpiralRoadmap/execution-cards/S6-EXECUTION-CARD.md (§3 模块级补齐任务)
DESIGN_TRACE = {
    "enhancement_plan": "docs/design/enhancements/eq-improvement-plan-core-frozen.md",
    "s6_execution_card": "Governance/SpiralRoadmap/execution-cards/S6-EXECUTION-CARD.md",
}

# 三层阈值
GATE_CHAIN_TOLERANCE = 0.0       # 精确匹配（bitwise equal）
SCORE_CHAIN_TOLERANCE = 1e-6     # 数值容差
RETURN_CHAIN_TOLERANCE = 1e-4    # 收益率容差


@dataclass
class ConsistencyResult:
    """一致性检查结果。"""

    chain_name: str           # gate / score / return
    tolerance: float
    max_diff: float
    field_diffs: list[dict[str, Any]] = field(default_factory=list)
    passed: bool = True


@dataclass
class FullConsistencyReport:
    """全链路一致性报告。"""

    trade_date: str
    gate_result: ConsistencyResult
    score_result: ConsistencyResult
    return_result: ConsistencyResult
    overall_passed: bool = True


def _compare_values(a: Any, b: Any, tolerance: float) -> tuple[bool, float]:
    """比较两个值，返回 (is_equal, diff)。"""
    if a is None and b is None:
        return True, 0.0
    if a is None or b is None:
        return False, float("inf")
    # 字符串精确比较
    if isinstance(a, str) or isinstance(b, str):
        return str(a) == str(b), 0.0 if str(a) == str(b) else float("inf")
    # 数值比较
    try:
        fa, fb = float(a), float(b)
        if math.isnan(fa) and math.isnan(fb):
            return True, 0.0
        diff = abs(fa - fb)
        return diff <= tolerance, diff
    except (TypeError, ValueError):
        return str(a) == str(b), 0.0 if str(a) == str(b) else float("inf")


def check_gate_chain(
    baseline: list[dict[str, Any]], replay: list[dict[str, Any]]
) -> ConsistencyResult:
    """gate 链一致性检查：精确匹配。"""
    return _check_chain("gate", baseline, replay, GATE_CHAIN_TOLERANCE)


def check_score_chain(
    baseline: list[dict[str, Any]], replay: list[dict[str, Any]]
) -> ConsistencyResult:
    """score 链一致性检查：差异 <1e-6。"""
    return _check_chain("score", baseline, replay, SCORE_CHAIN_TOLERANCE)


def check_return_chain(
    baseline: list[dict[str, Any]], replay: list[dict[str, Any]]
) -> ConsistencyResult:
    """return 链一致性检查：差异 <1e-4。"""
    return _check_chain("return", baseline, replay, RETURN_CHAIN_TOLERANCE)


def _check_chain(
    chain_name: str,
    baseline: list[dict[str, Any]],
    replay: list[dict[str, Any]],
    tolerance: float,
) -> ConsistencyResult:
    """通用链一致性检查。"""
    result = ConsistencyResult(
        chain_name=chain_name,
        tolerance=tolerance,
        max_diff=0.0,
    )

    if len(baseline) != len(replay):
        result.passed = False
        result.max_diff = float("inf")
        result.field_diffs.append({
            "field": "_row_count",
            "baseline": len(baseline),
            "replay": len(replay),
            "diff": abs(len(baseline) - len(replay)),
        })
        return result

    for idx, (b_row, r_row) in enumerate(zip(baseline, replay)):
        all_keys = set(b_row.keys()) | set(r_row.keys())
        for key in sorted(all_keys):
            b_val = b_row.get(key)
            r_val = r_row.get(key)
            is_eq, diff = _compare_values(b_val, r_val, tolerance)
            if not is_eq:
                result.passed = False
                result.field_diffs.append({
                    "row": idx,
                    "field": key,
                    "baseline": b_val,
                    "replay": r_val,
                    "diff": diff,
                })
            if diff != float("inf"):
                result.max_diff = max(result.max_diff, diff)

    return result


def run_full_consistency_check(
    trade_date: str,
    *,
    baseline_gates: list[dict[str, Any]],
    replay_gates: list[dict[str, Any]],
    baseline_scores: list[dict[str, Any]],
    replay_scores: list[dict[str, Any]],
    baseline_returns: list[dict[str, Any]],
    replay_returns: list[dict[str, Any]],
) -> FullConsistencyReport:
    """执行全链路一致性检查。"""
    gate_result = check_gate_chain(baseline_gates, replay_gates)
    score_result = check_score_chain(baseline_scores, replay_scores)
    return_result = check_return_chain(baseline_returns, replay_returns)

    overall = gate_result.passed and score_result.passed and return_result.passed

    return FullConsistencyReport(
        trade_date=trade_date,
        gate_result=gate_result,
        score_result=score_result,
        return_result=return_result,
        overall_passed=overall,
    )
