from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pytest

from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.repositories.base import BaseRepository, DuckDBLockRecoveryError
from src.data.repositories.daily import DailyRepository


class _DummyRepository(BaseRepository):
    table_name = "raw_dummy_lock"


def _build_config(tmp_path: Path, env_name: str) -> Config:
    env_file = tmp_path / env_name
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_repository_retries_duckdb_lock_and_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _build_config(tmp_path, ".env.s3ar.lock.retry")
    repository = _DummyRepository(config=config)
    repository.duckdb_lock_max_attempts = 4
    repository.duckdb_lock_retry_base_seconds = 0.0

    original_connect = duckdb.connect
    attempts = {"count": 0}

    def _flaky_connect(path: str, *args: Any, **kwargs: Any) -> duckdb.DuckDBPyConnection:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError(
                'IO Error: Could not set lock on file "emotionquant.duckdb": '
                "Conflicting lock is held in process 4321"
            )
        return original_connect(path, *args, **kwargs)

    monkeypatch.setattr(duckdb, "connect", _flaky_connect)
    inserted = repository.save_to_database([{"trade_date": "20260220", "value": 1.0}])
    assert inserted == 1
    assert attempts["count"] == 3


def test_l1_collection_emits_lock_recovery_audit_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _build_config(tmp_path, ".env.s3ar.lock.audit")

    def _raise_lock_error(self: DailyRepository, data: Any) -> int:
        del data
        raise DuckDBLockRecoveryError(
            database_path=Path(self.config.duckdb_dir) / "emotionquant.duckdb",
            retry_attempts=3,
            wait_seconds_total=0.6,
            last_error_message="database is locked by process 5678",
            lock_holder_pid="5678",
        )

    monkeypatch.setattr(DailyRepository, "save_to_database", _raise_lock_error)
    result = run_l1_collection(
        trade_date="20260220",
        source="tushare",
        config=config,
        fetcher=TuShareFetcher(max_retries=1),
    )

    assert result.has_error is True
    assert result.error_manifest_path.name == "error_manifest.json"
    payload = json.loads(result.error_manifest_path.read_text(encoding="utf-8"))
    lock_items = [
        item
        for item in payload.get("errors", [])
        if item.get("error_type") == "duckdb_lock_recovery_exhausted"
    ]
    assert lock_items
    lock_item = lock_items[0]
    assert lock_item["lock_holder_pid"] == "5678"
    assert lock_item["retry_attempts"] == "3"
    assert lock_item["wait_seconds_total"] == "0.600"
