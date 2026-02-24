"""数据质量门控（Quality Gate）契约测试。

验证 evaluate_data_quality_gate 在不同输入条件下返回正确的状态：
- READY：所有检查通过
- DEGRADED：数据略陈旧但在允许范围内
- BLOCKED：跨日不一致或陈旧天数超限
"""
from __future__ import annotations

from src.data.quality_gate import (
    STATUS_BLOCKED,
    STATUS_DEGRADED,
    STATUS_READY,
    evaluate_data_quality_gate,
)


def test_quality_gate_ready_when_all_checks_pass() -> None:
    """所有数据集覆盖率达标且无陈旧数据时，状态应为 READY。"""
    decision = evaluate_data_quality_gate(
        trade_date="20260214",
        coverage_ratio=0.97,
        source_trade_dates={"daily": "20260214", "limit_list": "20260214"},
        quality_by_dataset={"daily": "normal", "limit_list": "normal"},
        stale_days_by_dataset={"daily": 0, "limit_list": 0},
    )
    assert decision.status == STATUS_READY
    assert decision.is_ready is True
    assert decision.issues == []


def test_quality_gate_degraded_when_within_stale_limit() -> None:
    """数据陈旧天数在硬限内时，状态应为 DEGRADED（降级但可用）。"""
    decision = evaluate_data_quality_gate(
        trade_date="20260214",
        coverage_ratio=0.96,
        source_trade_dates={"daily": "20260213", "limit_list": "20260213"},
        quality_by_dataset={"daily": "stale", "limit_list": "stale"},
        stale_days_by_dataset={"daily": 1, "limit_list": 1},
    )
    assert decision.status == STATUS_DEGRADED
    assert decision.is_ready is True
    assert decision.max_stale_days == 1


def test_quality_gate_blocked_when_cross_day_mixed() -> None:
    """不同数据集的交易日不一致（跨日混合）时，状态应为 BLOCKED。"""
    decision = evaluate_data_quality_gate(
        trade_date="20260214",
        coverage_ratio=0.98,
        source_trade_dates={"daily": "20260214", "limit_list": "20260213"},
        quality_by_dataset={"daily": "normal", "limit_list": "stale"},
        stale_days_by_dataset={"daily": 0, "limit_list": 1},
    )
    assert decision.status == STATUS_BLOCKED
    assert "cross_day_inconsistency" in decision.issues


def test_quality_gate_blocked_when_stale_days_exceed_limit() -> None:
    """陈旧天数超过硬限（默认 3 天）时，状态应为 BLOCKED。"""
    decision = evaluate_data_quality_gate(
        trade_date="20260214",
        coverage_ratio=0.96,
        source_trade_dates={"daily": "20260210"},
        quality_by_dataset={"daily": "stale"},
        stale_days_by_dataset={"daily": 4},
    )
    assert decision.status == STATUS_BLOCKED
    assert decision.is_ready is False
    assert any(issue.startswith("stale_days_exceed_limit") for issue in decision.issues)
