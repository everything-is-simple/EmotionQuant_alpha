from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.algorithms.validation.pipeline import run_validation_gate
from src.config.config import Config


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s3e.validation.neutral.softgate"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _seed_inputs(
    config: Config,
    trade_date: str,
    *,
    mss_score: float = 55.0,
    pct_chg_std: float = 0.02,
) -> tuple[int, int]:
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
            VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
            """,
            [trade_date, float(mss_score), float(pct_chg_std)],
        )

        connection.execute(
            """
            CREATE OR REPLACE TABLE raw_daily (
                trade_date VARCHAR,
                close DOUBLE
            )
            """
        )
        for idx in range(40):
            synthetic_date = f"202601{idx + 1:02d}"
            if synthetic_date == trade_date:
                continue
            connection.execute(
                "INSERT INTO raw_daily (trade_date, close) VALUES (?, 10.0)",
                [synthetic_date],
            )
            connection.execute(
                "INSERT INTO mss_panorama (trade_date, mss_score, pct_chg_std, stale_days, created_at) "
                "VALUES (?, ?, 0.02, 0, CURRENT_TIMESTAMP)",
                [synthetic_date, 55.0 if idx % 2 == 0 else 45.0],
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
        for idx in range(31):
            score = 100.0 if idx % 2 == 0 else 0.0
            connection.execute(
                """
                INSERT INTO irs_industry_daily (
                    trade_date, industry_code, irs_score, industry_score, stale_days, created_at
                ) VALUES (?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
                """,
                [trade_date, f"SW{idx+1:04d}", score, score],
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
        for idx in range(310):
            score = 0.0 if idx % 2 == 0 else 100.0
            connection.execute(
                """
                INSERT INTO stock_pas_daily (
                    trade_date, stock_code, pas_score, risk_reward_ratio, effective_risk_reward_ratio, created_at
                ) VALUES (?, ?, ?, 1.20, 1.20, CURRENT_TIMESTAMP)
                """,
                [trade_date, f"{idx + 1:06d}", score],
            )

    return (31, 310)


def test_neutral_regime_dual_window_softens_factor_fail_to_warn(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260213"
    irs_count, pas_count = _seed_inputs(config, trade_date)

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

    assert result.final_gate == "WARN"
    assert result.selected_weight_plan != ""
    frame_row = result.frame.iloc[0]
    assert str(frame_row["reason"]) == "neutral_regime_factor_softened"
    assert str(frame_row["factor_gate"]) == "WARN"

    vote_detail = json.loads(str(frame_row["vote_detail"]))
    assert vote_detail["factor_gate_raw"] == "FAIL"
    assert vote_detail["neutral_regime_softening_applied"] is True

    manifest = json.loads(result.run_manifest_sample_path.read_text(encoding="utf-8"))
    assert manifest["vote_detail"]["factor_gate"] == "WARN"
    assert manifest["vote_detail"]["factor_gate_raw"] == "FAIL"
    assert manifest["vote_detail"]["neutral_regime_softening_applied"] is True


def test_cold_or_volatile_dual_window_softens_factor_fail_to_warn(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260126"
    irs_count, pas_count = _seed_inputs(
        config,
        trade_date,
        mss_score=40.0,
        pct_chg_std=0.05,
    )

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

    assert result.final_gate == "WARN"
    frame_row = result.frame.iloc[0]
    assert str(frame_row["reason"]) == "cold_or_volatile_factor_softened"
    assert str(frame_row["factor_gate"]) == "WARN"
    assert float(frame_row["position_cap_ratio"]) == 0.60

    vote_detail = json.loads(str(frame_row["vote_detail"]))
    assert vote_detail["factor_gate_raw"] == "FAIL"
    assert vote_detail["cold_or_volatile_softening_applied"] is True
    assert vote_detail["neutral_regime_softening_applied"] is False
