from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config


@dataclass(frozen=True)
class IrsRunResult:
    trade_date: str
    count: int
    frame: pd.DataFrame


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _to_recommendation(score: float) -> str:
    if score >= 75.0:
        return "STRONG_BUY"
    if score >= 70.0:
        return "BUY"
    if score >= 50.0:
        return "HOLD"
    if score >= 30.0:
        return "SELL"
    return "AVOID"


def _to_rotation_status(score: float) -> str:
    if score >= 60.0:
        return "IN"
    if score <= 40.0:
        return "OUT"
    return "HOLD"


def _persist(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
    trade_date: str,
) -> int:
    with duckdb.connect(str(database_path)) as connection:
        connection.register("incoming_df", frame)
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM incoming_df WHERE 1=0"
        )
        connection.execute(f"DELETE FROM {table_name} WHERE trade_date = ?", [trade_date])
        connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_df")
        connection.unregister("incoming_df")
    return int(len(frame))


def run_irs_daily(
    *,
    trade_date: str,
    config: Config,
) -> IrsRunResult:
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not database_path.exists():
        raise FileNotFoundError("duckdb_not_found")

    with duckdb.connect(str(database_path), read_only=True) as connection:
        if not _table_exists(connection, "industry_snapshot"):
            raise ValueError("industry_snapshot_table_missing")
        source = connection.execute(
            "SELECT trade_date, industry_code, industry_name, industry_pct_chg, data_quality, "
            "stale_days, source_trade_date FROM industry_snapshot WHERE trade_date = ?",
            [trade_date],
        ).df()

    if source.empty:
        raise ValueError("industry_snapshot_empty_for_trade_date")

    frame = source.copy()
    # Minimal mapping: convert pct change to 0-100 bounded score.
    frame["irs_score"] = (50.0 + frame["industry_pct_chg"].astype(float) * 2.0).clip(0.0, 100.0)
    frame["rotation_status"] = frame["irs_score"].map(_to_rotation_status)
    frame["recommendation"] = frame["irs_score"].map(_to_recommendation)
    frame["contract_version"] = "nc-v1"
    frame["created_at"] = pd.Timestamp.utcnow().isoformat()
    frame = frame[
        [
            "trade_date",
            "industry_code",
            "industry_name",
            "irs_score",
            "rotation_status",
            "recommendation",
            "data_quality",
            "stale_days",
            "source_trade_date",
            "contract_version",
            "created_at",
        ]
    ]

    count = _persist(
        database_path=database_path,
        table_name="irs_industry_daily",
        frame=frame,
        trade_date=trade_date,
    )
    return IrsRunResult(
        trade_date=trade_date,
        count=count,
        frame=frame,
    )
