from __future__ import annotations

from src.data.quality_gate import (
    STATUS_BLOCKED,
    STATUS_DEGRADED,
    STATUS_READY,
    evaluate_data_quality_gate,
)


def test_quality_gate_ready_when_all_checks_pass() -> None:
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
