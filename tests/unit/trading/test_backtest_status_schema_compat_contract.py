from __future__ import annotations

import duckdb
import pandas as pd

from src.trading.pipeline import _persist, _read_available_cash, _read_s3_backtest_status


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


def test_persist_auto_adds_missing_columns_for_legacy_trade_records_schema(tmp_path) -> None:
    db_path = tmp_path / "legacy_trade_records_insert.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "CREATE TABLE trade_records ("
            "trade_date VARCHAR, "
            "direction VARCHAR, "
            "amount DOUBLE, "
            "total_fee DOUBLE, "
            "status VARCHAR, "
            "created_at VARCHAR, "
            "stock_code VARCHAR)"
        )

    frame = pd.DataFrame.from_records(
        [
            {
                "trade_id": "TRD_20260213_0001",
                "trade_date": "20260213",
                "stock_code": "000001",
                "industry_code": "801010",
                "direction": "buy",
                "order_type": "auction",
                "price": 10.0,
                "shares": 100,
                "amount": 1000.0,
                "commission": 1.0,
                "stamp_tax": 0.0,
                "transfer_fee": 0.02,
                "total_fee": 1.02,
                "status": "filled",
                "reject_reason": "",
                "t1_restriction_hit": False,
                "limit_guard_result": "PASS",
                "session_guard_result": "PASS",
                "risk_reward_ratio": 1.2,
                "contract_version": "nc-v1",
                "created_at": "2026-02-23T00:00:00+00:00",
            }
        ]
    )

    _persist(
        database_path=db_path,
        table_name="trade_records",
        frame=frame,
        delete_trade_date="20260213",
    )

    with duckdb.connect(str(db_path), read_only=True) as connection:
        column_count = connection.execute(
            "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='trade_records'"
        ).fetchone()
        row = connection.execute(
            "SELECT trade_id, reject_reason, risk_reward_ratio "
            "FROM trade_records WHERE trade_date='20260213' LIMIT 1"
        ).fetchone()

    assert column_count is not None
    assert int(column_count[0]) >= 21
    assert row is not None
    assert row[0] == "TRD_20260213_0001"
    assert float(row[2]) == 1.2
