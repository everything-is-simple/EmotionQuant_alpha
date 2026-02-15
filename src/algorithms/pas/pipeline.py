from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from src.config.config import Config


@dataclass(frozen=True)
class PasRunResult:
    trade_date: str
    count: int
    frame: pd.DataFrame


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _to_direction(return_ratio: float) -> str:
    if return_ratio > 0.01:
        return "bullish"
    if return_ratio < -0.01:
        return "bearish"
    return "neutral"


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


def run_pas_daily(
    *,
    trade_date: str,
    config: Config,
) -> PasRunResult:
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not database_path.exists():
        raise FileNotFoundError("duckdb_not_found")

    with duckdb.connect(str(database_path), read_only=True) as connection:
        if not _table_exists(connection, "raw_daily"):
            raise ValueError("raw_daily_table_missing")
        source = connection.execute(
            "SELECT trade_date, ts_code, stock_code, open, close FROM raw_daily WHERE trade_date = ?",
            [trade_date],
        ).df()

    if source.empty:
        raise ValueError("raw_daily_empty_for_trade_date")

    frame = source.copy()
    frame["open"] = pd.to_numeric(frame["open"], errors="coerce").fillna(0.0)
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce").fillna(0.0)
    frame["return_ratio"] = (frame["close"] - frame["open"]) / frame["open"].replace(0.0, pd.NA)
    frame["return_ratio"] = frame["return_ratio"].fillna(0.0)
    frame["pas_score"] = (50.0 + frame["return_ratio"] * 300.0).clip(0.0, 100.0)
    frame["pas_direction"] = frame["return_ratio"].map(_to_direction)
    # S2a only validates existence; still keep canonical name for later execution boundary.
    frame["risk_reward_ratio"] = (1.0 + frame["return_ratio"].abs() * 5.0).clip(lower=1.0)
    frame["contract_version"] = "nc-v1"
    frame["created_at"] = pd.Timestamp.utcnow().isoformat()
    frame = frame[
        [
            "trade_date",
            "ts_code",
            "stock_code",
            "pas_score",
            "pas_direction",
            "risk_reward_ratio",
            "contract_version",
            "created_at",
        ]
    ]

    count = _persist(
        database_path=database_path,
        table_name="stock_pas_daily",
        frame=frame,
        trade_date=trade_date,
    )
    return PasRunResult(
        trade_date=trade_date,
        count=count,
        frame=frame,
    )
