from __future__ import annotations

import duckdb
import pandas as pd

from src.backtest.pipeline import _persist


def test_backtest_results_persist_upgrades_legacy_schema(tmp_path) -> None:
    db_path = tmp_path / "backtest_schema_compat.duckdb"

    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "CREATE TABLE backtest_results ("
            "backtest_id VARCHAR, "
            "start_date VARCHAR, "
            "end_date VARCHAR, "
            "total_trades INTEGER, "
            "win_rate DOUBLE, "
            "total_return DOUBLE, "
            "max_drawdown DOUBLE, "
            "created_at VARCHAR)"
        )
        connection.execute(
            "INSERT INTO backtest_results VALUES "
            "('legacy-001','20260212','20260213',2,0.5,0.01,0.02,'2026-02-19T00:00:00+00:00')"
        )

    incoming = pd.DataFrame.from_records(
        [
            {
                "backtest_id": "BTR_20260210_20260213_qlib",
                "engine": "qlib",
                "start_date": "20260210",
                "end_date": "20260213",
                "quality_status": "WARN",
                "go_nogo": "GO",
                "consumed_signal_rows": 4,
                "total_trades": 3,
                "win_rate": 0.6667,
                "total_return": 0.0123,
                "max_drawdown": 0.0345,
                "max_drawdown_days": 2,
                "daily_return_mean": 0.0012,
                "turnover_cv": 0.25,
                "total_fee": 123.45,
                "cost_bps": 9.87,
                "impact_cost_ratio": 0.21,
                "source_fetch_progress_path": "artifacts/spiral-s3a/20260213/fetch_progress.json",
                "source_fetch_start_date": "20260210",
                "source_fetch_end_date": "20260213",
                "source_fetch_status": "completed",
                "bridge_check_status": "PASS",
                "contract_version": "nc-v1",
                "created_at": "2026-02-21T00:00:00+00:00",
            }
        ]
    )
    _persist(
        database_path=db_path,
        table_name="backtest_results",
        frame=incoming,
        delete_key="backtest_id",
        delete_value="BTR_20260210_20260213_qlib",
    )

    with duckdb.connect(str(db_path), read_only=True) as connection:
        columns = connection.execute("PRAGMA table_info('backtest_results')").df()["name"].tolist()
        row = connection.execute(
            "SELECT quality_status, go_nogo, contract_version "
            "FROM backtest_results WHERE backtest_id = ?",
            ["BTR_20260210_20260213_qlib"],
        ).fetchone()

    assert "quality_status" in columns
    assert "go_nogo" in columns
    assert "contract_version" in columns
    assert "max_drawdown_days" in columns
    assert "daily_return_mean" in columns
    assert "turnover_cv" in columns
    assert "total_fee" in columns
    assert "cost_bps" in columns
    assert "impact_cost_ratio" in columns
    assert row is not None
    assert row[0] == "WARN"
    assert row[1] == "GO"
    assert row[2] == "nc-v1"

