from __future__ import annotations

import pytest

from src.algorithms.mss.engine import MssInputSnapshot, calculate_mss_score


def test_mss_temperature_matches_six_factor_weight_formula() -> None:
    snapshot = MssInputSnapshot(
        trade_date="20260218",
        total_stocks=1200,
        rise_count=730,
        limit_up_count=48,
        limit_down_count=8,
        touched_limit_up=62,
        strong_up_count=160,
        strong_down_count=55,
        new_100d_high_count=95,
        new_100d_low_count=30,
        continuous_limit_up_2d=13,
        continuous_limit_up_3d_plus=5,
        continuous_new_high_2d_plus=19,
        high_open_low_close_count=21,
        low_open_high_close_count=29,
        pct_chg_std=0.024,
        amount_volatility=280000.0,
        data_quality="normal",
        stale_days=0,
        source_trade_date="20260218",
    )

    score = calculate_mss_score(snapshot, temperature_history=[44.0, 48.0, 51.0, 53.0])

    expected_temperature = round(
        score.mss_market_coefficient * 0.17
        + score.mss_profit_effect * 0.34
        + (100.0 - score.mss_loss_effect) * 0.34
        + score.mss_continuity_factor * 0.05
        + score.mss_extreme_factor * 0.05
        + score.mss_volatility_factor * 0.05,
        4,
    )
    assert score.mss_temperature == pytest.approx(expected_temperature, abs=1e-4)
    assert 0.0 <= score.mss_market_coefficient <= 100.0
    assert 0.0 <= score.mss_profit_effect <= 100.0
    assert 0.0 <= score.mss_loss_effect <= 100.0
    assert 0.0 <= score.mss_continuity_factor <= 100.0
    assert 0.0 <= score.mss_extreme_factor <= 100.0
    assert 0.0 <= score.mss_volatility_factor <= 100.0
    assert -1.0 <= score.mss_extreme_direction_bias <= 1.0
    assert score.trend_quality in {"normal", "cold_start", "degraded"}
    assert score.mss_rank >= 1
    assert 0.0 <= score.mss_percentile <= 100.0


def test_mss_missing_baseline_fallbacks_to_neutral_50() -> None:
    snapshot = MssInputSnapshot(
        trade_date="20260218",
        total_stocks=0,
        rise_count=0,
        limit_up_count=0,
        limit_down_count=0,
        touched_limit_up=0,
        strong_up_count=0,
        strong_down_count=0,
        new_100d_high_count=0,
        new_100d_low_count=0,
        continuous_limit_up_2d=0,
        continuous_limit_up_3d_plus=0,
        continuous_new_high_2d_plus=0,
        high_open_low_close_count=0,
        low_open_high_close_count=0,
        pct_chg_std=0.0,
        amount_volatility=0.0,
        data_quality="stale",
        stale_days=3,
        source_trade_date="20260215",
    )

    score = calculate_mss_score(snapshot, temperature_history=[])
    assert score.mss_market_coefficient == pytest.approx(50.0, abs=1e-6)
    assert score.mss_profit_effect == pytest.approx(50.0, abs=1e-6)
    assert score.mss_loss_effect == pytest.approx(50.0, abs=1e-6)
    assert score.mss_continuity_factor == pytest.approx(50.0, abs=1e-6)
    assert score.mss_extreme_factor == pytest.approx(50.0, abs=1e-6)
    assert score.mss_volatility_factor == pytest.approx(50.0, abs=1e-6)
    assert score.mss_temperature == pytest.approx(50.0, abs=1e-6)
    assert score.mss_rank == 1
    assert score.mss_percentile == pytest.approx(100.0, abs=1e-6)
