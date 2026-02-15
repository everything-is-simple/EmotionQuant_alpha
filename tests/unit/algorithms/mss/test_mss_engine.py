from __future__ import annotations

from src.algorithms.mss.engine import (
    MssInputSnapshot,
    calculate_mss_score,
    detect_cycle,
    detect_trend,
)


def test_detect_trend_uses_three_point_monotonic_rule() -> None:
    assert detect_trend([40.0, 45.0, 50.0]) == "up"
    assert detect_trend([50.0, 45.0, 40.0]) == "down"
    assert detect_trend([50.0, 50.0, 52.0]) == "sideways"
    assert detect_trend([50.0, 52.0]) == "sideways"


def test_detect_cycle_matches_naming_contract() -> None:
    assert detect_cycle(80.0, "up") == "climax"
    assert detect_cycle(25.0, "up") == "emergence"
    assert detect_cycle(35.0, "up") == "fermentation"
    assert detect_cycle(55.0, "up") == "acceleration"
    assert detect_cycle(65.0, "up") == "divergence"
    assert detect_cycle(65.0, "down") == "diffusion"
    assert detect_cycle(55.0, "sideways") == "recession"
    assert detect_cycle(55.0, "invalid") == "unknown"


def test_calculate_mss_score_returns_required_fields_and_ranges() -> None:
    snapshot = MssInputSnapshot(
        trade_date="20260215",
        total_stocks=1000,
        rise_count=620,
        limit_up_count=42,
        limit_down_count=6,
        touched_limit_up=58,
        strong_up_count=110,
        strong_down_count=30,
        new_100d_high_count=80,
        new_100d_low_count=25,
        continuous_limit_up_2d=10,
        continuous_limit_up_3d_plus=4,
        continuous_new_high_2d_plus=16,
        high_open_low_close_count=18,
        low_open_high_close_count=27,
        pct_chg_std=0.021,
        amount_volatility=230000.0,
        data_quality="normal",
        stale_days=0,
        source_trade_date="20260215",
    )

    result = calculate_mss_score(snapshot, temperature_history=[43.0, 47.0, 50.0, 53.0])

    assert 0.0 <= result.mss_score <= 100.0
    assert 0.0 <= result.mss_temperature <= 100.0
    assert 0.0 <= result.neutrality <= 1.0
    assert result.mss_cycle in {
        "emergence",
        "fermentation",
        "acceleration",
        "divergence",
        "climax",
        "diffusion",
        "recession",
        "unknown",
    }

    payload = result.to_storage_record()
    assert {"mss_score", "mss_temperature", "mss_cycle"} <= set(payload.keys())
    assert payload["trade_date"] == "20260215"
    assert payload["contract_version"] == "nc-v1"
