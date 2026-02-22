from __future__ import annotations

from pathlib import Path

import duckdb

from src.algorithms.irs.pipeline import run_irs_daily
from src.algorithms.mss.pipeline import run_mss_scoring
from src.algorithms.pas.pipeline import run_pas_daily
from src.algorithms.validation.pipeline import run_validation_gate
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2c.validation.factor"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_inputs(config: Config, trade_date: str) -> tuple[int, int]:
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
    irs_result = run_irs_daily(trade_date=trade_date, config=config)
    pas_result = run_pas_daily(trade_date=trade_date, config=config)
    return (irs_result.count, pas_result.count)


def test_validation_factor_metrics_contract(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"
    irs_count, pas_count = _prepare_inputs(config, trade_date)

    result = run_validation_gate(
        trade_date=trade_date,
        config=config,
        irs_count=irs_count,
        pas_count=pas_count,
        mss_exists=True,
    )

    assert result.factor_report_sample_path.exists()
    assert not result.factor_report_frame.empty

    required_columns = {
        "factor_name",
        "ic",
        "rank_ic",
        "icir",
        "decay_5d",
        "sample_size",
        "gate",
        "contract_version",
    }
    assert required_columns <= set(result.factor_report_frame.columns)
    assert set(result.factor_report_frame["gate"].unique().tolist()) <= {"PASS", "WARN", "FAIL"}
    assert ((result.factor_report_frame["ic"] >= -1.0) & (result.factor_report_frame["ic"] <= 1.0)).all()
    assert ((result.factor_report_frame["rank_ic"] >= -1.0) & (result.factor_report_frame["rank_ic"] <= 1.0)).all()
    assert ((result.factor_report_frame["decay_5d"] >= 0.0) & (result.factor_report_frame["decay_5d"] <= 1.0)).all()

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM validation_factor_report WHERE trade_date=?",
            [trade_date],
        ).fetchone()[0]
    assert int(count) > 0

