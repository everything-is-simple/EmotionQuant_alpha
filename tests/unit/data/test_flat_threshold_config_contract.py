from __future__ import annotations

from pathlib import Path

import duckdb

from src.config.config import Config
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.flat.threshold"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n"
        "FLAT_THRESHOLD=0.5\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _seed_l1_inputs(db_path: Path, trade_date: str) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            """
            CREATE OR REPLACE TABLE raw_daily (
                ts_code VARCHAR,
                stock_code VARCHAR,
                trade_date VARCHAR,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                vol BIGINT,
                amount DOUBLE
            )
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE TABLE raw_limit_list (
                ts_code VARCHAR,
                stock_code VARCHAR,
                trade_date VARCHAR,
                limit_type VARCHAR
            )
            """
        )
        connection.executemany(
            "INSERT INTO raw_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("000001.SZ", "000001", trade_date, 10.0, 10.1, 9.9, 10.04, 100000, 1004000.0),
                ("000002.SZ", "000002", trade_date, 10.0, 10.2, 9.8, 10.06, 100000, 1006000.0),
                ("000003.SZ", "000003", trade_date, 10.0, 10.1, 9.9, 9.98, 100000, 998000.0),
            ],
        )


def test_flat_count_uses_flat_threshold_from_system_config(tmp_path: Path) -> None:
    trade_date = "20260215"
    config = _build_config(tmp_path)
    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    _seed_l1_inputs(db_path, trade_date)

    result = run_l2_snapshot(
        trade_date=trade_date,
        source="tushare",
        config=config,
        strict_sw31=False,
    )
    assert result.has_error is False

    with duckdb.connect(str(db_path), read_only=True) as connection:
        market_flat_count = connection.execute(
            "SELECT flat_count FROM market_snapshot WHERE trade_date = ?",
            [trade_date],
        ).fetchone()
        industry_flat_count = connection.execute(
            "SELECT flat_count FROM industry_snapshot WHERE trade_date = ? AND industry_code = 'ALL'",
            [trade_date],
        ).fetchone()
        flat_threshold = connection.execute(
            "SELECT config_value FROM system_config WHERE config_key = 'flat_threshold'",
        ).fetchone()

    assert market_flat_count is not None
    assert int(market_flat_count[0]) == 2
    assert industry_flat_count is not None
    assert int(industry_flat_count[0]) == 2
    assert flat_threshold is not None
    assert abs(float(flat_threshold[0]) - 0.5) < 1e-9
