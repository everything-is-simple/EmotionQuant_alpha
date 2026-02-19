from __future__ import annotations

from pathlib import Path

import duckdb

from src.config.config import Config


def build_analysis_config(tmp_path: Path, env_name: str) -> Config:
    env_file = tmp_path / env_name
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    config = Config.from_env(env_file=str(env_file))
    Path(config.duckdb_dir).mkdir(parents=True, exist_ok=True)
    return config


def database_path(config: Config) -> Path:
    return Path(config.duckdb_dir) / "emotionquant.duckdb"


def seed_ab_benchmark_tables(config: Config, start_date: str, end_date: str) -> None:
    db_path = database_path(config)
    with duckdb.connect(str(db_path)) as connection:
        connection.execute("DROP TABLE IF EXISTS backtest_results")
        connection.execute("DROP TABLE IF EXISTS integrated_recommendation")
        connection.execute(
            "CREATE TABLE backtest_results ("
            "backtest_id VARCHAR, start_date VARCHAR, end_date VARCHAR, "
            "total_return DOUBLE, max_drawdown DOUBLE, win_rate DOUBLE, total_trades BIGINT, created_at VARCHAR)"
        )
        connection.execute(
            "INSERT INTO backtest_results VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?)",
            ["bt-001", start_date, end_date, 0.12, -0.05, 0.6, 8, "2026-02-19T00:00:00+00:00"],
        )
        connection.execute(
            "CREATE TABLE integrated_recommendation ("
            "trade_date VARCHAR, stock_code VARCHAR, mss_score DOUBLE, irs_score DOUBLE, pas_score DOUBLE, "
            "entry DOUBLE, final_score DOUBLE)"
        )
        connection.execute(
            "INSERT INTO integrated_recommendation VALUES "
            "('20260218', '000001', 62, 58, 61, 10.0, 60), "
            "('20260219', '000002', 64, 59, 63, 11.0, 62)"
        )


def seed_deviation_tables(config: Config, trade_date: str) -> None:
    db_path = database_path(config)
    with duckdb.connect(str(db_path)) as connection:
        connection.execute("DROP TABLE IF EXISTS integrated_recommendation")
        connection.execute("DROP TABLE IF EXISTS trade_records")
        connection.execute("DROP TABLE IF EXISTS backtest_trade_records")
        connection.execute("DROP TABLE IF EXISTS live_backtest_deviation")
        connection.execute(
            "CREATE TABLE integrated_recommendation ("
            "trade_date VARCHAR, stock_code VARCHAR, mss_score DOUBLE, irs_score DOUBLE, pas_score DOUBLE, "
            "entry DOUBLE, final_score DOUBLE)"
        )
        connection.execute(
            "INSERT INTO integrated_recommendation VALUES "
            "(?, '000001', 62, 58, 61, 10.0, 60), "
            "(?, '000002', 64, 59, 63, 20.0, 62)",
            [trade_date, trade_date],
        )
        connection.execute(
            "CREATE TABLE trade_records ("
            "trade_date VARCHAR, stock_code VARCHAR, direction VARCHAR, status VARCHAR, "
            "price DOUBLE, amount DOUBLE, total_fee DOUBLE)"
        )
        connection.execute(
            "INSERT INTO trade_records VALUES "
            "(?, '000001', 'buy', 'filled', 10.2, 1020, 2.0), "
            "(?, '000002', 'buy', 'filled', 20.1, 2010, 3.0)",
            [trade_date, trade_date],
        )
        connection.execute(
            "CREATE TABLE backtest_trade_records ("
            "trade_date VARCHAR, signal_date VARCHAR, stock_code VARCHAR, direction VARCHAR, status VARCHAR, "
            "filled_price DOUBLE, amount DOUBLE, final_score DOUBLE)"
        )
        connection.execute(
            "INSERT INTO backtest_trade_records VALUES "
            "(?, ?, '000001', 'buy', 'filled', 10.1, 1010, 59), "
            "(?, ?, '000002', 'buy', 'filled', 20.2, 2020, 61)",
            [trade_date, trade_date, trade_date, trade_date],
        )


def seed_attribution_tables(config: Config, trade_date: str) -> None:
    db_path = database_path(config)
    with duckdb.connect(str(db_path)) as connection:
        connection.execute("DROP TABLE IF EXISTS integrated_recommendation")
        connection.execute("DROP TABLE IF EXISTS trade_records")
        connection.execute("DROP TABLE IF EXISTS signal_attribution")
        connection.execute(
            "CREATE TABLE integrated_recommendation ("
            "trade_date VARCHAR, stock_code VARCHAR, mss_score DOUBLE, irs_score DOUBLE, pas_score DOUBLE, "
            "entry DOUBLE, final_score DOUBLE)"
        )
        connection.execute(
            "INSERT INTO integrated_recommendation VALUES "
            "(?, '000001', 62, 58, 61, 10.0, 60), "
            "(?, '000002', 64, 59, 63, 20.0, 62), "
            "(?, '000003', 66, 60, 65, 30.0, 64)",
            [trade_date, trade_date, trade_date],
        )
        connection.execute(
            "CREATE TABLE trade_records ("
            "trade_date VARCHAR, stock_code VARCHAR, direction VARCHAR, status VARCHAR, "
            "price DOUBLE, amount DOUBLE, total_fee DOUBLE)"
        )
        connection.execute(
            "INSERT INTO trade_records VALUES "
            "(?, '000001', 'buy', 'filled', 10.2, 1020, 2.0), "
            "(?, '000002', 'buy', 'filled', 20.1, 2010, 3.0), "
            "(?, '000003', 'buy', 'filled', 29.7, 2970, 4.0)",
            [trade_date, trade_date, trade_date],
        )
