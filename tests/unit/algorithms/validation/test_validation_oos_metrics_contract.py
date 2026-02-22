from __future__ import annotations

import json
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
    env_file = tmp_path / ".env.s3e.oos"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_validation_oos_report_and_manifest_contract(tmp_path: Path) -> None:
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

    artifacts_dir = tmp_path / "artifacts" / "spiral-s3e" / trade_date
    result = run_validation_gate(
        trade_date=trade_date,
        config=config,
        irs_count=irs_count,
        pas_count=pas_count,
        mss_exists=True,
        artifacts_dir=artifacts_dir,
        threshold_mode="regime",
        wfa_mode="dual-window",
        export_run_manifest=True,
    )
    assert result.oos_calibration_report_path.exists()
    report_text = result.oos_calibration_report_path.read_text(encoding="utf-8")
    assert "Validation OOS Calibration Report" in report_text
    assert "threshold_mode: regime" in report_text
    assert "wfa_mode: dual-window" in report_text

    manifest = json.loads(result.run_manifest_sample_path.read_text(encoding="utf-8"))
    assert manifest["threshold_mode"] == "regime"
    assert manifest["wfa_mode"] == "dual-window"

