from __future__ import annotations

from pathlib import Path

import duckdb

from src.algorithms.mss.pipeline import run_mss_scoring
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.recommend import run_recommendation


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2b.integration"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_s2b_inputs(config: Config, trade_date: str) -> None:
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
    run_mss_scoring(
        trade_date=trade_date,
        config=config,
    )
    s2a = run_recommendation(
        trade_date=trade_date,
        mode="mss_irs_pas",
        with_validation=True,
        config=config,
    )
    assert s2a.has_error is False


def test_s2b_generates_integrated_recommendation_with_execution_fields(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"
    _prepare_s2b_inputs(config, trade_date)

    result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        config=config,
    )
    assert result.has_error is False
    assert result.integrated_count > 0
    assert result.integrated_count <= 20
    assert result.integration_mode == "top_down"
    assert result.quality_gate_status in {"PASS", "WARN"}
    assert result.integrated_sample_path.exists()
    assert result.quality_gate_report_path.exists()
    assert result.go_nogo_decision_path.exists()

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT contract_version, risk_reward_ratio, t1_restriction_hit, "
            "limit_guard_result, session_guard_result "
            "FROM integrated_recommendation WHERE trade_date=? LIMIT 1",
            [trade_date],
        ).fetchone()
        quality_row = connection.execute(
            "SELECT status FROM quality_gate_report WHERE trade_date=? LIMIT 1",
            [trade_date],
        ).fetchone()

    assert row is not None
    assert row[0] == "nc-v1"
    assert float(row[1]) >= 1.0
    assert row[2] in (False, 0)
    assert str(row[3]) != ""
    assert str(row[4]) != ""
    assert quality_row is not None
    assert quality_row[0] in ("PASS", "WARN")


def test_s2b_supports_bottom_up_mode(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"
    _prepare_s2b_inputs(config, trade_date)

    result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        integration_mode="bottom_up",
        with_validation=False,
        config=config,
    )
    assert result.has_error is False
    assert result.integrated_count > 0
    assert result.integration_mode == "bottom_up"

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        mode_row = connection.execute(
            "SELECT DISTINCT integration_mode FROM integrated_recommendation WHERE trade_date=?",
            [trade_date],
        ).fetchall()
    assert mode_row
    assert all(str(item[0]) == "bottom_up" for item in mode_row)


def test_s2b_enforces_daily_and_industry_recommendation_caps(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"
    _prepare_s2b_inputs(config, trade_date)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        target_row = connection.execute(
            "SELECT index_code FROM raw_index_member ORDER BY index_code LIMIT 1"
        ).fetchone()
        assert target_row is not None
        target_index_code = str(target_row[0])
        connection.execute(
            "UPDATE raw_index_member SET index_code = ? WHERE CAST(trade_date AS VARCHAR) LIKE '202602%'",
            [target_index_code],
        )

    result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        config=config,
    )
    assert result.has_error is False
    assert result.integrated_count <= 20

    with duckdb.connect(str(db_path), read_only=True) as connection:
        max_industry_count = connection.execute(
            "SELECT COALESCE(MAX(cnt), 0) FROM ("
            "SELECT industry_code, COUNT(*) AS cnt "
            "FROM integrated_recommendation WHERE trade_date=? GROUP BY industry_code"
            ")",
            [trade_date],
        ).fetchone()
    assert max_industry_count is not None
    assert int(max_industry_count[0]) <= 5


def test_s2b_repairs_legacy_position_size_integer_schema(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"
    _prepare_s2b_inputs(config, trade_date)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    first = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        config=config,
    )
    assert first.has_error is False

    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "ALTER TABLE integrated_recommendation "
            "ALTER COLUMN position_size TYPE INTEGER USING CAST(position_size AS INTEGER)"
        )

    second = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        config=config,
    )
    assert second.has_error is False

    with duckdb.connect(str(db_path), read_only=True) as connection:
        column_type = connection.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name='integrated_recommendation' AND column_name='position_size'"
        ).fetchone()
        decimals = connection.execute(
            "SELECT COUNT(*) FROM integrated_recommendation "
            "WHERE trade_date=? AND position_size > 0 AND position_size < 1",
            [trade_date],
        ).fetchone()

    assert column_type is not None
    assert str(column_type[0]).upper() in {"DOUBLE", "FLOAT", "REAL"}
    assert decimals is not None
    assert int(decimals[0]) > 0

