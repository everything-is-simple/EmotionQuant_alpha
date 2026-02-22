from __future__ import annotations

from pathlib import Path

from src.algorithms.irs.pipeline import run_irs_daily
from src.algorithms.mss.pipeline import run_mss_scoring
from src.algorithms.pas.pipeline import run_pas_daily
from src.algorithms.validation.pipeline import run_validation_gate
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s3e.wfa"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_validation_weight_report_supports_dual_window_mode(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"
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
    run_mss_scoring(trade_date=trade_date, config=config)
    irs_count = run_irs_daily(trade_date=trade_date, config=config).count
    pas_count = run_pas_daily(trade_date=trade_date, config=config).count

    result = run_validation_gate(
        trade_date=trade_date,
        config=config,
        irs_count=irs_count,
        pas_count=pas_count,
        mss_exists=True,
        artifacts_dir=tmp_path / "artifacts" / "spiral-s3e" / trade_date,
        threshold_mode="regime",
        wfa_mode="dual-window",
        export_run_manifest=True,
    )
    assert result.wfa_mode == "dual-window"
    window_groups = set(result.weight_report_frame["window_group"].astype(str).tolist())
    assert {"short_window", "long_window"} <= window_groups

