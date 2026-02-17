from __future__ import annotations

from src.backtest.pipeline import _is_limit_down
from src.backtest.pipeline import _is_limit_up
from src.backtest.pipeline import _resolve_limit_ratio


def test_resolve_limit_ratio_by_board_and_st() -> None:
    assert _resolve_limit_ratio(stock_code="000001", stock_name="平安银行") == 0.10
    assert _resolve_limit_ratio(stock_code="300750", stock_name="宁德时代") == 0.20
    assert _resolve_limit_ratio(stock_code="688001", stock_name="华兴源创") == 0.20
    assert _resolve_limit_ratio(stock_code="300001", stock_name="*ST示例") == 0.05


def test_limit_detection_uses_prev_close_and_board_ratio() -> None:
    price_not_limit_up = {"open": 119.0, "high": 119.0, "low": 118.0, "close": 118.5}
    price_limit_up = {"open": 120.0, "high": 120.0, "low": 119.5, "close": 120.0}
    assert (
        _is_limit_up(price=price_not_limit_up, prev_close=100.0, limit_ratio=0.20) is False
    )
    assert _is_limit_up(price=price_limit_up, prev_close=100.0, limit_ratio=0.20) is True

    price_not_limit_down = {"open": 81.5, "high": 82.0, "low": 81.0, "close": 81.2}
    price_limit_down = {"open": 80.0, "high": 80.5, "low": 80.0, "close": 80.0}
    assert (
        _is_limit_down(price=price_not_limit_down, prev_close=100.0, limit_ratio=0.20) is False
    )
    assert _is_limit_down(price=price_limit_down, prev_close=100.0, limit_ratio=0.20) is True


def test_limit_detection_fallback_when_prev_close_missing() -> None:
    price = {"open": 10.0, "high": 10.0, "low": 9.5, "close": 9.8}
    assert _is_limit_up(price=price, prev_close=None, limit_ratio=0.10) is True

    down_price = {"open": 9.5, "high": 9.8, "low": 9.5, "close": 9.6}
    assert _is_limit_down(price=down_price, prev_close=None, limit_ratio=0.10) is True
