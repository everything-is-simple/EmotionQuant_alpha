from __future__ import annotations

from src.backtest.pipeline import _estimate_impact_cost, _resolve_fee_tier


def test_fee_tier_respects_notional_bands() -> None:
    small_tier = _resolve_fee_tier(80_000.0)
    medium_tier = _resolve_fee_tier(250_000.0)
    large_tier = _resolve_fee_tier(800_000.0)

    assert small_tier[0] == "S"
    assert medium_tier[0] == "M"
    assert large_tier[0] == "L"
    assert small_tier[1] > medium_tier[1] > large_tier[1]


def test_impact_cost_higher_under_lower_liquidity_tier() -> None:
    amount = 200_000.0
    order_shares = 10_000
    slippage_rate = 0.001

    l1_cost, l1_tier, _ = _estimate_impact_cost(
        price={"vol": 2_000_000.0, "open": 10.0, "close": 10.0},
        order_shares=order_shares,
        amount=amount,
        slippage_rate=slippage_rate,
    )
    l3_cost, l3_tier, _ = _estimate_impact_cost(
        price={"vol": 80_000.0, "open": 10.0, "close": 10.0},
        order_shares=order_shares,
        amount=amount,
        slippage_rate=slippage_rate,
    )

    assert l1_tier == "L1"
    assert l3_tier == "L3"
    assert l3_cost > l1_cost


def test_impact_cost_increases_with_queue_pressure() -> None:
    amount = 200_000.0
    slippage_rate = 0.001
    price = {"vol": 500_000.0, "open": 10.0, "close": 10.0}

    low_pressure_cost, _, low_queue_ratio = _estimate_impact_cost(
        price=price,
        order_shares=500,
        amount=amount,
        slippage_rate=slippage_rate,
    )
    high_pressure_cost, _, high_queue_ratio = _estimate_impact_cost(
        price=price,
        order_shares=50_000,
        amount=amount,
        slippage_rate=slippage_rate,
    )

    assert high_queue_ratio > low_queue_ratio
    assert high_pressure_cost > low_pressure_cost
