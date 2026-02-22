from __future__ import annotations

from pathlib import Path

import duckdb

from src.algorithms.pas.pipeline import run_pas_daily
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2c.pas.full"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_pas_full_semantics_outputs_contract_fields_and_artifact(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"

    run_l1_collection(
        trade_date=trade_date,
        source="tushare",
        config=config,
        fetcher=TuShareFetcher(max_retries=1),
    )

    result = run_pas_daily(trade_date=trade_date, config=config)
    assert result.count > 0
    assert result.factor_intermediate_sample_path.exists()

    required_columns = {
        "opportunity_score",
        "pas_score",
        "opportunity_grade",
        "direction",
        "pas_direction",
        "risk_reward_ratio",
        "effective_risk_reward_ratio",
        "quality_flag",
        "sample_days",
        "neutrality",
        "window_mode",
        "adaptive_window",
        "bull_gene_score",
        "structure_score",
        "behavior_score",
        "contract_version",
    }
    assert required_columns <= set(result.frame.columns)

    assert set(result.frame["opportunity_grade"].unique().tolist()) <= {"S", "A", "B", "C", "D"}
    assert set(result.frame["direction"].unique().tolist()) <= {"bullish", "bearish", "neutral"}
    assert set(result.frame["quality_flag"].unique().tolist()) <= {"normal", "cold_start", "stale"}
    assert set(result.frame["adaptive_window"].astype(int).unique().tolist()) <= {20, 60, 120}
    assert ((result.frame["pas_score"] >= 0.0) & (result.frame["pas_score"] <= 100.0)).all()
    assert ((result.frame["neutrality"] >= 0.0) & (result.frame["neutrality"] <= 1.0)).all()
    assert (result.frame["sample_days"] >= 0).all()

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        factor_count = connection.execute(
            "SELECT COUNT(*) FROM pas_factor_intermediate WHERE trade_date=?",
            [trade_date],
        ).fetchone()[0]
    assert int(factor_count) > 0

