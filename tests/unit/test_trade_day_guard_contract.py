from __future__ import annotations

from tests.unit.trade_day_guard import (
    assert_all_valid_trade_days,
    latest_open_trade_days,
    load_canary_open_trade_days,
)


def test_trade_day_canary_excludes_known_cny_closure_days() -> None:
    days = set(load_canary_open_trade_days())
    assert "20260213" in days
    assert "20260218" not in days
    assert "20260219" not in days


def test_trade_day_guard_rejects_invalid_date() -> None:
    try:
        assert_all_valid_trade_days(["20260218"], context="contract")
    except AssertionError as exc:
        assert "invalid_trade_date_in_contract" in str(exc)
        return
    raise AssertionError("expected invalid_trade_date assertion")


def test_latest_open_trade_days_returns_ascending_window() -> None:
    window = latest_open_trade_days(2)
    assert len(window) == 2
    assert window[0] < window[1]
