from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
import json
from pathlib import Path
import time
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config
from src.data.quality_gate import DataGateDecision
from src.data.repositories.base import (
    DuckDBLockRecoveryError,
    acquire_duckdb_interprocess_lock,
    extract_lock_holder_pid,
    is_duckdb_lock_error,
)


DEFAULT_CONFIG_DESCRIPTIONS = {
    "flat_threshold": "平盘阈值（单位%）",
    "min_coverage_ratio": "最小覆盖率阈值",
    "stale_hard_limit_days": "stale_days 硬门限（天）",
    "enable_intraday_incremental": "是否启用盘中增量（true/false）",
}
QUALITY_DUCKDB_LOCK_MAX_ATTEMPTS = 12
QUALITY_DUCKDB_LOCK_RETRY_BASE_SECONDS = 0.5
QUALITY_DUCKDB_PROCESS_LOCK_TIMEOUT_SECONDS = 120.0
QUALITY_DUCKDB_PROCESS_LOCK_POLL_SECONDS = 0.1


def _utc_now_iso() -> str:
    return pd.Timestamp.utcnow().isoformat()


def _with_duckdb_write_connection(
    database_path: Path,
    *,
    operation: Callable[[duckdb.DuckDBPyConnection], Any],
) -> Any:
    max_attempts = max(1, int(QUALITY_DUCKDB_LOCK_MAX_ATTEMPTS))
    wait_base_seconds = max(0.0, float(QUALITY_DUCKDB_LOCK_RETRY_BASE_SECONDS))
    wait_seconds_total = 0.0
    last_error_message = ""
    lock_holder_pid = ""
    lock_wait_started = time.monotonic()
    try:
        with acquire_duckdb_interprocess_lock(
            database_path,
            timeout_seconds=float(QUALITY_DUCKDB_PROCESS_LOCK_TIMEOUT_SECONDS),
            poll_seconds=float(QUALITY_DUCKDB_PROCESS_LOCK_POLL_SECONDS),
        ):
            wait_seconds_total += max(0.0, time.monotonic() - lock_wait_started)
            for attempt in range(1, max_attempts + 1):
                try:
                    with duckdb.connect(str(database_path)) as connection:
                        return operation(connection)
                except Exception as exc:
                    if not is_duckdb_lock_error(exc):
                        raise
                    last_error_message = str(exc)
                    extracted_pid = extract_lock_holder_pid(last_error_message)
                    if extracted_pid:
                        lock_holder_pid = extracted_pid
                    if attempt >= max_attempts:
                        raise DuckDBLockRecoveryError(
                            database_path=database_path,
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
        extracted_pid = extract_lock_holder_pid(last_error_message)
        if extracted_pid:
            lock_holder_pid = extracted_pid
        raise DuckDBLockRecoveryError(
            database_path=database_path,
            retry_attempts=max_attempts,
            wait_seconds_total=wait_seconds_total,
            last_error_message=last_error_message,
            lock_holder_pid=lock_holder_pid,
        ) from exc


def ensure_quality_tables(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS system_config (
            config_key VARCHAR PRIMARY KEY,
            config_value VARCHAR,
            config_type VARCHAR,
            description VARCHAR,
            is_encrypted BOOLEAN,
            created_at VARCHAR,
            updated_at VARCHAR
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS data_quality_report (
            trade_date VARCHAR,
            check_item VARCHAR,
            expected_value VARCHAR,
            actual_value VARCHAR,
            deviation DOUBLE,
            status VARCHAR,
            gate_status VARCHAR,
            affected_layers VARCHAR,
            action VARCHAR,
            created_at VARCHAR
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS data_readiness_gate (
            trade_date VARCHAR PRIMARY KEY,
            status VARCHAR,
            is_ready BOOLEAN,
            coverage_ratio DOUBLE,
            max_stale_days BIGINT,
            cross_day_consistent BOOLEAN,
            issues VARCHAR,
            warnings VARCHAR,
            created_at VARCHAR
        )
        """
    )


def upsert_system_config_defaults(
    connection: duckdb.DuckDBPyConnection,
    *,
    config: Config,
) -> None:
    now = _utc_now_iso()
    defaults = [
        ("flat_threshold", f"{float(config.flat_threshold):.6f}", "float"),
        ("min_coverage_ratio", f"{float(config.min_coverage_ratio):.6f}", "float"),
        ("stale_hard_limit_days", str(int(config.stale_hard_limit_days)), "int"),
        (
            "enable_intraday_incremental",
            "true" if bool(config.enable_intraday_incremental) else "false",
            "bool",
        ),
    ]
    for key, value, value_type in defaults:
        row = connection.execute(
            "SELECT created_at FROM system_config WHERE config_key = ?",
            [key],
        ).fetchone()
        created_at = str(row[0]) if row and row[0] else now
        connection.execute("DELETE FROM system_config WHERE config_key = ?", [key])
        connection.execute(
            """
            INSERT INTO system_config (
                config_key, config_value, config_type, description, is_encrypted, created_at, updated_at
            ) VALUES (?, ?, ?, ?, false, ?, ?)
            """,
            [
                key,
                value,
                value_type,
                DEFAULT_CONFIG_DESCRIPTIONS.get(key, ""),
                created_at,
                now,
            ],
        )


def load_quality_thresholds(
    connection: duckdb.DuckDBPyConnection,
    *,
    config: Config,
) -> dict[str, float | int]:
    def _read(key: str, fallback: float | int) -> float | int:
        row = connection.execute(
            "SELECT config_value FROM system_config WHERE config_key = ?",
            [key],
        ).fetchone()
        if row is None or row[0] is None:
            return fallback
        raw = str(row[0]).strip()
        if raw == "":
            return fallback
        try:
            if isinstance(fallback, int):
                return int(float(raw))
            return float(raw)
        except ValueError:
            return fallback

    return {
        "flat_threshold": float(_read("flat_threshold", float(config.flat_threshold))),
        "min_coverage_ratio": float(
            _read("min_coverage_ratio", float(config.min_coverage_ratio))
        ),
        "stale_hard_limit_days": int(
            _read("stale_hard_limit_days", int(config.stale_hard_limit_days))
        ),
    }


def persist_data_quality_report(
    connection: duckdb.DuckDBPyConnection,
    *,
    trade_date: str,
    rows: list[dict[str, Any]],
) -> int:
    if not rows:
        return 0
    check_items = [str(row.get("check_item", "")).strip() for row in rows]
    unique_items = sorted({item for item in check_items if item})
    if unique_items:
        placeholders = ",".join(["?"] * len(unique_items))
        connection.execute(
            f"DELETE FROM data_quality_report WHERE trade_date = ? AND check_item IN ({placeholders})",
            [trade_date, *unique_items],
        )

    now = _utc_now_iso()
    payload: list[tuple[Any, ...]] = []
    for row in rows:
        payload.append(
            (
                trade_date,
                str(row.get("check_item", "")),
                str(row.get("expected_value", "")),
                str(row.get("actual_value", "")),
                float(row.get("deviation", 0.0) or 0.0),
                str(row.get("status", "WARN")),
                str(row.get("gate_status", "")),
                str(row.get("affected_layers", "")),
                str(row.get("action", "")),
                now,
            )
        )
    connection.executemany(
        """
        INSERT INTO data_quality_report (
            trade_date, check_item, expected_value, actual_value, deviation,
            status, gate_status, affected_layers, action, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )
    return len(payload)


def persist_data_readiness_gate(
    connection: duckdb.DuckDBPyConnection,
    *,
    decision: DataGateDecision,
) -> None:
    now = _utc_now_iso()
    connection.execute(
        "DELETE FROM data_readiness_gate WHERE trade_date = ?",
        [decision.trade_date],
    )
    connection.execute(
        """
        INSERT INTO data_readiness_gate (
            trade_date, status, is_ready, coverage_ratio, max_stale_days,
            cross_day_consistent, issues, warnings, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            decision.trade_date,
            decision.status,
            bool(decision.is_ready),
            float(decision.coverage_ratio),
            int(decision.max_stale_days),
            bool(decision.cross_day_consistent),
            json.dumps(list(decision.issues), ensure_ascii=True),
            json.dumps(list(decision.warnings), ensure_ascii=True),
            now,
        ],
    )


def init_quality_context(database_path: Path, *, config: Config) -> dict[str, float | int]:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    def _operation(connection: duckdb.DuckDBPyConnection) -> dict[str, float | int]:
        ensure_quality_tables(connection)
        upsert_system_config_defaults(connection, config=config)
        return load_quality_thresholds(connection, config=config)
    return _with_duckdb_write_connection(database_path, operation=_operation)


def persist_quality_outputs(
    database_path: Path,
    *,
    decision: DataGateDecision,
    report_rows: list[dict[str, Any]],
    config: Config,
) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    def _operation(connection: duckdb.DuckDBPyConnection) -> None:
        ensure_quality_tables(connection)
        upsert_system_config_defaults(connection, config=config)
        persist_data_quality_report(
            connection,
            trade_date=decision.trade_date,
            rows=report_rows,
        )
        persist_data_readiness_gate(connection, decision=decision)
    _with_duckdb_write_connection(database_path, operation=_operation)


def decision_to_json(decision: DataGateDecision) -> dict[str, Any]:
    payload = asdict(decision)
    payload["issues"] = list(decision.issues)
    payload["warnings"] = list(decision.warnings)
    return payload
