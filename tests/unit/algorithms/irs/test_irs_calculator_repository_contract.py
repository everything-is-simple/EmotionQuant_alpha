from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.algorithms.irs.calculator import DefaultIrsCalculator
from src.algorithms.irs.repository import DuckDbIrsRepository


def _mock_snapshot_frame(trade_date: str) -> pd.DataFrame:
    return pd.DataFrame.from_records(
        [
            {
                "trade_date": "20260212",
                "industry_code": "801001.SI",
                "industry_name": "行业A",
                "industry_pct_chg": 0.80,
                "industry_amount": 1200.0,
                "industry_turnover": 2.4,
                "industry_pe_ttm": 16.0,
                "industry_pb": 1.8,
                "rise_count": 30,
                "fall_count": 8,
                "new_100d_high_count": 10,
                "new_100d_low_count": 2,
                "limit_up_count": 4,
                "top5_limit_up": 2,
                "top5_pct_chg": "[1.5,1.2,1.1,0.8,0.5]",
                "stock_count": 38,
                "stale_days": 0,
            },
            {
                "trade_date": trade_date,
                "industry_code": "801001.SI",
                "industry_name": "行业A",
                "industry_pct_chg": 1.20,
                "industry_amount": 1800.0,
                "industry_turnover": 2.8,
                "industry_pe_ttm": 15.5,
                "industry_pb": 1.7,
                "rise_count": 33,
                "fall_count": 6,
                "new_100d_high_count": 11,
                "new_100d_low_count": 1,
                "limit_up_count": 5,
                "top5_limit_up": 3,
                "top5_pct_chg": "[2.2,1.9,1.6,1.1,0.7]",
                "stock_count": 39,
                "stale_days": 0,
            },
        ]
    )


def test_default_irs_calculator_can_score_without_pipeline() -> None:
    trade_date = "20260213"
    history = _mock_snapshot_frame(trade_date=trade_date)
    source = history[history["trade_date"] == trade_date].reset_index(drop=True)
    benchmark_history = pd.DataFrame.from_records(
        [
            {"trade_date": "20260212", "pct_chg": 0.4},
            {"trade_date": trade_date, "pct_chg": 0.5},
        ]
    )

    frame = DefaultIrsCalculator().score(
        source=source,
        history=history,
        trade_date=trade_date,
        benchmark_history=benchmark_history,
    )

    assert not frame.empty
    assert {"industry_score", "irs_score", "allocation_advice", "rotation_status"} <= set(frame.columns)
    assert frame.iloc[0]["industry_code"] == "801001.SI"


def test_duckdb_irs_repository_roundtrip(tmp_path: Path) -> None:
    trade_date = "20260213"
    database_path = tmp_path / "emotionquant.duckdb"
    snapshot = _mock_snapshot_frame(trade_date=trade_date)
    with duckdb.connect(str(database_path)) as connection:
        connection.register("snapshot_df", snapshot)
        connection.execute("CREATE TABLE industry_snapshot AS SELECT * FROM snapshot_df")
        connection.unregister("snapshot_df")

    repository = DuckDbIrsRepository(database_path=database_path)
    loaded = repository.load_industry_snapshot(trade_date=trade_date)
    assert len(loaded) == 1
    assert loaded.iloc[0]["industry_code"] == "801001.SI"

    scored = pd.DataFrame.from_records(
        [
            {
                "trade_date": trade_date,
                "industry_code": "801001.SI",
                "industry_score": 72.3,
                "irs_score": 72.3,
            }
        ]
    )
    count = repository.save_daily(scored, trade_date=trade_date)
    assert count == 1

    with duckdb.connect(str(database_path), read_only=True) as connection:
        rows = connection.execute(
            "SELECT COUNT(*) FROM irs_industry_daily WHERE trade_date = ?",
            [trade_date],
        ).fetchone()
    assert rows and int(rows[0]) == 1
