from __future__ import annotations

from pathlib import Path

import duckdb

from src.algorithms.irs.pipeline import run_irs_daily
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2c.irs.full"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_irs_full_semantics_outputs_contract_fields_and_artifact(tmp_path: Path) -> None:
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

    result = run_irs_daily(trade_date=trade_date, config=config)
    assert result.count > 0
    assert result.factor_intermediate_sample_path.exists()

    required_columns = {
        "industry_score",
        "irs_score",
        "rotation_status",
        "rotation_slope",
        "allocation_advice",
        "allocation_mode",
        "quality_flag",
        "sample_days",
        "neutrality",
        "relative_strength",
        "continuity_factor",
        "capital_flow",
        "valuation",
        "leader_score",
        "gene_score",
        "contract_version",
    }
    assert required_columns <= set(result.frame.columns)

    assert set(result.frame["rotation_status"].unique().tolist()) <= {"IN", "OUT", "HOLD"}
    assert set(result.frame["allocation_mode"].unique().tolist()) <= {"dynamic", "fixed"}
    assert set(result.frame["quality_flag"].unique().tolist()) <= {"normal", "cold_start", "stale"}
    assert ((result.frame["industry_score"] >= 0.0) & (result.frame["industry_score"] <= 100.0)).all()
    assert ((result.frame["neutrality"] >= 0.0) & (result.frame["neutrality"] <= 1.0)).all()
    assert (result.frame["sample_days"] >= 0).all()

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        factor_count = connection.execute(
            "SELECT COUNT(*) FROM irs_factor_intermediate WHERE trade_date=?",
            [trade_date],
        ).fetchone()[0]
    assert int(factor_count) > 0

