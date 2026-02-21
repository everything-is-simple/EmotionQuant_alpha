from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.algorithms.validation.pipeline import run_validation_gate
from src.config.config import Config


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2c.validation.lowinfo"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _seed_low_information_inputs(config: Config, trade_date: str) -> None:
    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            """
            CREATE OR REPLACE TABLE mss_panorama (
                trade_date VARCHAR,
                mss_score DOUBLE,
                pct_chg_std DOUBLE,
                stale_days BIGINT,
                created_at TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO mss_panorama (trade_date, mss_score, pct_chg_std, stale_days, created_at)
            VALUES (?, 55.0, 0.02, 0, CURRENT_TIMESTAMP)
            """,
            [trade_date],
        )

        connection.execute(
            """
            CREATE OR REPLACE TABLE irs_industry_daily (
                trade_date VARCHAR,
                industry_code VARCHAR,
                irs_score DOUBLE,
                industry_score DOUBLE,
                stale_days BIGINT,
                created_at TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO irs_industry_daily (trade_date, industry_code, irs_score, industry_score, stale_days, created_at)
            VALUES (?, 'SW9999', 62.0, 62.0, 0, CURRENT_TIMESTAMP)
            """,
            [trade_date],
        )

        connection.execute(
            """
            CREATE OR REPLACE TABLE stock_pas_daily (
                trade_date VARCHAR,
                stock_code VARCHAR,
                pas_score DOUBLE,
                risk_reward_ratio DOUBLE,
                effective_risk_reward_ratio DOUBLE,
                created_at TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO stock_pas_daily (
                trade_date, stock_code, pas_score, risk_reward_ratio, effective_risk_reward_ratio, created_at
            )
            SELECT ?, CAST(row_id AS VARCHAR), 50.0, 1.2, 1.2, CURRENT_TIMESTAMP
            FROM range(1, 101) AS t(row_id)
            """,
            [trade_date],
        )


def test_low_information_pas_factor_falls_back_to_warn(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260213"
    _seed_low_information_inputs(config, trade_date)

    result = run_validation_gate(
        trade_date=trade_date,
        config=config,
        irs_count=1,
        pas_count=100,
        mss_exists=True,
    )

    assert result.final_gate == "WARN"
    assert result.selected_weight_plan != ""
    assert str(result.frame.iloc[0]["reason"]) == "warn_but_allowed"

    pas_row = result.factor_report_frame[result.factor_report_frame["factor_name"] == "pas_internal_stability"]
    assert not pas_row.empty
    assert str(pas_row.iloc[0]["gate"]) == "WARN"

    vote_detail = json.loads(str(pas_row.iloc[0]["vote_detail"]))
    assert vote_detail["low_information_fallback"] is True

