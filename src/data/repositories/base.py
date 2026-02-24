from __future__ import annotations

from contextlib import contextmanager
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config

try:
    import msvcrt
except ImportError:  # pragma: no cover - non-Windows fallback
    msvcrt = None


def is_duckdb_lock_error(exc: Exception) -> bool:
    message = str(exc).strip().lower()
    if not message:
        return False
    lock_signals = (
        "database is locked",
        "conflicting lock is held",
        "could not set lock on file",
        "lock is already held",
        "另一个程序正在使用此文件",
    )
    return any(signal in message for signal in lock_signals)


def extract_lock_holder_pid(message: str) -> str:
    match = re.search(r"(?:process|pid)\s*[:=]?\s*(\d+)", message, flags=re.IGNORECASE)
    if not match:
        return ""
    return str(match.group(1))


@contextmanager
def acquire_duckdb_interprocess_lock(
    database_path: Path,
    *,
    timeout_seconds: float,
    poll_seconds: float,
):
    """Coordinate writes across Python processes on Windows via lock-file byte lock."""
    if os.name != "nt" or msvcrt is None:
        yield
        return
    lock_path = database_path.with_suffix(f"{database_path.suffix}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    timeout = max(0.0, float(timeout_seconds))
    poll = max(0.01, float(poll_seconds))
    deadline = time.monotonic() + timeout
    while True:
        handle = lock_path.open("a+b")
        try:
            handle.seek(0)
            handle.write(b"\0")
            handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            break
        except OSError:
            handle.close()
            if time.monotonic() >= deadline:
                raise TimeoutError(f"duckdb_interprocess_lock_timeout: {lock_path}")
            time.sleep(poll)
    try:
        yield
    finally:
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            handle.close()


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
    duckdb_lock_max_attempts = 12
    duckdb_lock_retry_base_seconds = 0.5
    duckdb_process_lock_timeout_seconds = 120.0
    duckdb_process_lock_poll_seconds = 0.1
    _write_io_lock = threading.RLock()

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
        return is_duckdb_lock_error(exc)

    @staticmethod
    def _extract_lock_holder_pid(message: str) -> str:
        return extract_lock_holder_pid(message)

    def _table_has_column(
        self, connection: duckdb.DuckDBPyConnection, *, table_name: str, column_name: str
    ) -> bool:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = ? AND column_name = ?",
            [table_name, column_name],
        ).fetchone()
        return bool(row and int(row[0]) > 0)

    def _replace_trade_date_partition(self, connection: duckdb.DuckDBPyConnection) -> None:
        if not self._table_has_column(connection, table_name=self.table_name, column_name="trade_date"):
            return
        incoming_columns = {str(item[0]) for item in connection.execute("DESCRIBE incoming_df").fetchall()}
        if "trade_date" not in incoming_columns:
            return
        connection.execute(
            f"DELETE FROM {self.table_name} "
            "WHERE CAST(trade_date AS VARCHAR) IN ("
            "SELECT DISTINCT CAST(trade_date AS VARCHAR) FROM incoming_df WHERE trade_date IS NOT NULL)"
        )

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

        with self._write_io_lock:
            lock_wait_started = time.monotonic()
            try:
                with acquire_duckdb_interprocess_lock(
                    self.database_path,
                    timeout_seconds=float(self.duckdb_process_lock_timeout_seconds),
                    poll_seconds=float(self.duckdb_process_lock_poll_seconds),
                ):
                    wait_seconds_total += max(0.0, time.monotonic() - lock_wait_started)
                    for attempt in range(1, max_attempts + 1):
                        try:
                            with duckdb.connect(str(self.database_path)) as connection:
                                connection.register("incoming_df", frame)
                                connection.execute(
                                    f"CREATE TABLE IF NOT EXISTS {self.table_name} "
                                    "AS SELECT * FROM incoming_df WHERE 1=0"
                                )
                                self._sync_table_schema(connection)
                                self._replace_trade_date_partition(connection)
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
            except TimeoutError as exc:
                wait_seconds_total += max(0.0, time.monotonic() - lock_wait_started)
                last_error_message = str(exc)
                extracted_pid = self._extract_lock_holder_pid(last_error_message)
                if extracted_pid:
                    lock_holder_pid = extracted_pid
                raise DuckDBLockRecoveryError(
                    database_path=self.database_path,
                    retry_attempts=max_attempts,
                    wait_seconds_total=wait_seconds_total,
                    last_error_message=last_error_message,
                    lock_holder_pid=lock_holder_pid,
                ) from exc

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
        with self._write_io_lock:
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
