from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config


class DuckDBLockRecoveryError(RuntimeError):
    def __init__(
        self,
        *,
        database_path: Path,
        retry_attempts: int,
        wait_seconds_total: float,
        last_error_message: str,
        lock_holder_pid: str = "",
    ) -> None:
        self.database_path = database_path
        self.retry_attempts = int(retry_attempts)
        self.wait_seconds_total = float(wait_seconds_total)
        self.last_error_message = str(last_error_message)
        self.lock_holder_pid = str(lock_holder_pid).strip()
        holder = self.lock_holder_pid or "unknown"
        super().__init__(
            "duckdb_lock_recovery_exhausted: "
            f"db={self.database_path} "
            f"retry_attempts={self.retry_attempts} "
            f"wait_seconds_total={self.wait_seconds_total:.3f} "
            f"lock_holder_pid={holder} "
            f"last_error={self.last_error_message}"
        )


class BaseRepository:
    """Base repository for L1 raw datasets."""

    table_name = ""
    duckdb_lock_max_attempts = 3
    duckdb_lock_retry_base_seconds = 0.2

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

    @staticmethod
    def _is_duckdb_lock_error(exc: Exception) -> bool:
        message = str(exc).strip().lower()
        if not message:
            return False
        lock_signals = (
            "database is locked",
            "conflicting lock is held",
            "could not set lock on file",
            "lock is already held",
        )
        return any(signal in message for signal in lock_signals)

    @staticmethod
    def _extract_lock_holder_pid(message: str) -> str:
        match = re.search(r"(?:process|pid)\s*[:=]?\s*(\d+)", message, flags=re.IGNORECASE)
        if not match:
            return ""
        return str(match.group(1))

    def save_to_database(self, data: Any) -> int:
        self._assert_table_name()
        records = self._normalize_records(data)
        if not records:
            return 0

        frame = pd.DataFrame.from_records(records)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        max_attempts = max(1, int(self.duckdb_lock_max_attempts))
        wait_base_seconds = max(0.0, float(self.duckdb_lock_retry_base_seconds))
        wait_seconds_total = 0.0
        last_error_message = ""
        lock_holder_pid = ""

        for attempt in range(1, max_attempts + 1):
            try:
                with duckdb.connect(str(self.database_path)) as connection:
                    connection.register("incoming_df", frame)
                    connection.execute(
                        f"CREATE TABLE IF NOT EXISTS {self.table_name} "
                        "AS SELECT * FROM incoming_df WHERE 1=0"
                    )
                    self._sync_table_schema(connection)
                    connection.execute(f"INSERT INTO {self.table_name} BY NAME SELECT * FROM incoming_df")
                    connection.unregister("incoming_df")
                return int(len(frame))
            except Exception as exc:
                if not self._is_duckdb_lock_error(exc):
                    raise
                last_error_message = str(exc)
                extracted_pid = self._extract_lock_holder_pid(last_error_message)
                if extracted_pid:
                    lock_holder_pid = extracted_pid
                if attempt >= max_attempts:
                    raise DuckDBLockRecoveryError(
                        database_path=self.database_path,
                        retry_attempts=max_attempts,
                        wait_seconds_total=wait_seconds_total,
                        last_error_message=last_error_message,
                        lock_holder_pid=lock_holder_pid,
                    ) from exc
                wait_seconds = wait_base_seconds * float(attempt)
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                    wait_seconds_total += wait_seconds

        return int(len(frame))

    def _sync_table_schema(self, connection: duckdb.DuckDBPyConnection) -> None:
        existing = connection.execute(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{self.table_name}'"
        ).fetchall()
        existing_columns = {str(item[0]) for item in existing}
        incoming = connection.execute("DESCRIBE incoming_df").fetchall()
        for column_name, column_type, *_ in incoming:
            name = str(column_name)
            if name in existing_columns:
                continue
            escaped_name = name.replace('"', '""')
            connection.execute(
                f'ALTER TABLE {self.table_name} ADD COLUMN "{escaped_name}" {column_type}'
            )
            existing_columns.add(name)

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
