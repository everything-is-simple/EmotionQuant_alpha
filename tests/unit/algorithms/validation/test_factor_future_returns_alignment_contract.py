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
    env_file = tmp_path / ".env.s3e.factor.future"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_inputs(config: Config, trade_dates: list[str]) -> tuple[int, int]:
    irs_count = 0
    pas_count = 0
    for trade_date in trade_dates:
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
    return (irs_count, pas_count)


def test_validation_factor_report_contains_future_returns_alignment_factor(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_dates = [
        "20260210",
        "20260211",
        "20260212",
        "20260213",
        "20260214",
        "20260215",
        "20260216",
        "20260217",
        "20260212",
    ]
    irs_count, pas_count = _prepare_inputs(config, trade_dates)
    trade_date = trade_dates[-1]

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
    target_rows = result.factor_report_frame[
        result.factor_report_frame["factor_name"] == "mss_future_returns_alignment"
    ]
    assert not target_rows.empty
    vote_detail = json.loads(str(target_rows.iloc[0]["vote_detail"]))
    assert vote_detail["return_series_source"] == "future_returns"

