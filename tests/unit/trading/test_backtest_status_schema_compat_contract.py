from __future__ import annotations

import duckdb

from src.trading.pipeline import _read_available_cash, _read_s3_backtest_status


def test_read_backtest_status_returns_legacy_schema_error_instead_of_binder_exception(
    tmp_path,
) -> None:
    db_path = tmp_path / "legacy_backtest_results.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "CREATE TABLE backtest_results ("
            "backtest_id VARCHAR, "
            "start_date VARCHAR, "
            "end_date VARCHAR, "
            "total_trades INTEGER, "
            "created_at VARCHAR)"
        )
        connection.execute(
            "INSERT INTO backtest_results VALUES "
            "('legacy-001','20260210','20260213',3,'2026-02-21T00:00:00+00:00')"
        )

    ready, reason = _read_s3_backtest_status(db_path, "20260213")
    assert ready is False
    assert reason.startswith("backtest_results_schema_legacy_missing_")


def test_read_available_cash_works_with_legacy_trade_records_without_trade_id(tmp_path) -> None:
    db_path = tmp_path / "legacy_trade_records.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "CREATE TABLE trade_records ("
            "trade_date VARCHAR, "
            "direction VARCHAR, "
            "amount DOUBLE, "
            "total_fee DOUBLE, "
            "status VARCHAR)"
        )
        connection.execute(
            "INSERT INTO trade_records VALUES "
            "('20260210','buy',1000.0,1.0,'filled'),"
            "('20260211','sell',1200.0,1.2,'filled')"
        )

    cash = _read_available_cash(db_path, "20260213", 10000.0)
    assert cash == 10197.8
