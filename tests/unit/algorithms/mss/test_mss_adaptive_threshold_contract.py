from __future__ import annotations

import json
from pathlib import Path

from src.algorithms.mss.engine import (
    MssInputSnapshot,
    calculate_mss_score,
    resolve_cycle_thresholds,
)
from src.algorithms.mss.pipeline import run_mss_scoring
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s3d.mss"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_mss_threshold_mode_contract_supports_fixed_and_adaptive() -> None:
    history = [float(10 + idx % 80) for idx in range(180)]
    fixed = resolve_cycle_thresholds(history, threshold_mode="fixed")
    adaptive = resolve_cycle_thresholds(history, threshold_mode="adaptive")
    assert fixed == {"t30": 30.0, "t45": 45.0, "t60": 60.0, "t75": 75.0}
    assert adaptive != fixed

    snapshot = MssInputSnapshot(
        trade_date="20260221",
        total_stocks=500,
        rise_count=300,
        limit_up_count=20,
        limit_down_count=5,
        touched_limit_up=28,
        strong_up_count=60,
        strong_down_count=20,
        new_100d_high_count=25,
        new_100d_low_count=8,
        continuous_limit_up_2d=6,
        continuous_limit_up_3d_plus=2,
        continuous_new_high_2d_plus=8,
        high_open_low_close_count=10,
        low_open_high_close_count=12,
        pct_chg_std=0.021,
        amount_volatility=220000.0,
        data_quality="normal",
        stale_days=0,
        source_trade_date="20260221",
    )
    fixed_score = calculate_mss_score(snapshot, temperature_history=history, threshold_mode="fixed")
    adaptive_score = calculate_mss_score(snapshot, temperature_history=history, threshold_mode="adaptive")
    assert fixed_score.mss_cycle in {
        "emergence",
        "fermentation",
        "acceleration",
        "divergence",
        "climax",
        "diffusion",
        "recession",
        "unknown",
    }
    assert adaptive_score.mss_cycle in {
        "emergence",
        "fermentation",
        "acceleration",
        "divergence",
        "climax",
        "diffusion",
        "recession",
        "unknown",
    }


def test_s3d_mss_writes_threshold_snapshot_and_regression_artifacts(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260218"
    run_l1_collection(
        trade_date=trade_date,
        source="tushare",
        config=config,
        fetcher=TuShareFetcher(max_retries=1),
    )
    run_l2_snapshot(
        trade_date=trade_date,
        source="tushare",
        config=config,
    )
    artifacts_dir = tmp_path / "artifacts" / "spiral-s3d" / trade_date
    result = run_mss_scoring(
        trade_date=trade_date,
        config=config,
        threshold_mode="adaptive",
        artifacts_dir=artifacts_dir,
    )
    assert result.has_error is False
    assert result.threshold_mode == "adaptive"
    assert result.threshold_snapshot_path.exists()
    assert result.adaptive_regression_path.exists()
    assert result.gate_report_path.exists()
    assert result.consumption_path.exists()

    payload = json.loads(result.threshold_snapshot_path.read_text(encoding="utf-8"))
    assert payload["trade_date"] == trade_date
    assert payload["threshold_mode"] == "adaptive"
    assert {"t30", "t45", "t60", "t75"} <= set(payload["thresholds"].keys())
