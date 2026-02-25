from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.db.helpers import table_exists as _table_exists

REQUIRED_MSS_FIELDS = {
    "trade_date",
    "mss_score",
    "mss_temperature",
    "mss_cycle",
    "mss_trend",
    "contract_version",
}




def load_mss_panorama_for_integration(
    *,
    database_path: Path,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    if not database_path.exists():
        raise FileNotFoundError(f"duckdb_not_found: {database_path}")

    with duckdb.connect(str(database_path), read_only=True) as connection:
        if not _table_exists(connection, "mss_panorama"):
            raise ValueError("mss_panorama_table_missing")
        frame = connection.execute(
            "SELECT trade_date, mss_score, mss_temperature, mss_cycle, mss_trend, contract_version "
            "FROM mss_panorama "
            "WHERE trade_date >= ? AND trade_date <= ? "
            "ORDER BY trade_date",
            [start_date, end_date],
        ).df()

    if not REQUIRED_MSS_FIELDS <= set(frame.columns):
        missing = REQUIRED_MSS_FIELDS - set(frame.columns)
        raise ValueError(f"mss_panorama_required_fields_missing: {sorted(missing)}")
    return frame
