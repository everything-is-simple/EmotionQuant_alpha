from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config


class BaseRepository:
    """Base repository for L1 raw datasets."""

    table_name = ""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config.from_env()
        self.database_path = Path(self.config.duckdb_dir) / "emotionquant.duckdb"
        self.parquet_root = Path(self.config.parquet_path) / "l1"

    def fetch(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("fetch is not implemented")

    def _normalize_records(self, data: Any) -> list[dict[str, Any]]:
        if data is None:
            return []
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        if hasattr(data, "to_dict"):
            records = data.to_dict(orient="records")
            return [row for row in records if isinstance(row, dict)]
        raise TypeError(f"unsupported payload type: {type(data)!r}")

    def _assert_table_name(self) -> None:
        if not self.table_name:
            raise ValueError(f"{self.__class__.__name__}.table_name is empty")

    def save_to_database(self, data: Any) -> int:
        self._assert_table_name()
        records = self._normalize_records(data)
        if not records:
            return 0

        frame = pd.DataFrame.from_records(records)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with duckdb.connect(str(self.database_path)) as connection:
            connection.register("incoming_df", frame)
            connection.execute(
                f"CREATE TABLE IF NOT EXISTS {self.table_name} "
                "AS SELECT * FROM incoming_df WHERE 1=0"
            )
            connection.execute(f"INSERT INTO {self.table_name} SELECT * FROM incoming_df")
            connection.unregister("incoming_df")

        return int(len(frame))

    def save_to_parquet(self, data: Any) -> Path:
        self._assert_table_name()
        records = self._normalize_records(data)
        output_path = self.parquet_root / f"{self.table_name}.parquet"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame.from_records(records)
        frame.to_parquet(output_path, index=False)
        return output_path

    def count_by_trade_date(self, trade_date: str) -> int:
        self._assert_table_name()
        if not self.database_path.exists():
            return 0
        with duckdb.connect(str(self.database_path), read_only=True) as connection:
            result = connection.execute(
                f"SELECT COUNT(*) FROM {self.table_name} WHERE trade_date = ?",
                [trade_date],
            ).fetchone()
        return int(result[0]) if result else 0
