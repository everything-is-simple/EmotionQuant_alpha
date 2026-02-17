from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection


class MissingTradeCalClient:
    def call(self, api_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        trade_date = str(params.get("trade_date") or params.get("start_date") or "")
        if api_name == "daily":
            return [{"ts_code": "000001.SZ", "stock_code": "000001", "trade_date": trade_date}]
        if api_name == "trade_cal":
            return []
        if api_name == "limit_list":
            return [{"ts_code": "000001.SZ", "stock_code": "000001", "trade_date": trade_date}]
        raise ValueError(f"unsupported api: {api_name}")


class ClosedDayClient:
    def call(self, api_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        trade_date = str(params.get("trade_date") or params.get("start_date") or "")
        if api_name == "daily":
            return []
        if api_name == "trade_cal":
            return [{"exchange": "SSE", "trade_date": trade_date, "is_open": 0}]
        if api_name == "limit_list":
            return []
        raise ValueError(f"unsupported api: {api_name}")


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s0b"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_l1_collection_persists_required_raw_tables_and_artifacts(tmp_path: Path) -> None:
    config = _build_config(tmp_path)

    result = run_l1_collection(
        trade_date="20260215",
        source="tushare",
        config=config,
        fetcher=TuShareFetcher(max_retries=1),
    )

    assert result.has_error is False
    assert result.raw_counts["raw_daily"] > 0
    assert result.trade_cal_contains_trade_date is True

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        daily_count = connection.execute(
            "SELECT COUNT(*) FROM raw_daily WHERE trade_date='20260215'"
        ).fetchone()[0]
        trade_cal_count = connection.execute(
            "SELECT COUNT(*) FROM raw_trade_cal WHERE trade_date='20260215'"
        ).fetchone()[0]
    assert daily_count > 0
    assert trade_cal_count > 0

    assert (result.artifacts_dir / "raw_counts.json").exists()
    assert (result.artifacts_dir / "fetch_retry_report.md").exists()
    assert (result.artifacts_dir / "error_manifest_sample.json").exists()


def test_l1_collection_writes_error_manifest_when_gate_fails(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    fetcher = TuShareFetcher(client=MissingTradeCalClient(), max_retries=1)

    result = run_l1_collection(
        trade_date="20260215",
        source="tushare",
        config=config,
        fetcher=fetcher,
    )

    assert result.has_error is True
    assert result.error_manifest_path.name == "error_manifest.json"
    assert result.error_manifest_path.exists()

    payload: dict[str, Any] = json.loads(result.error_manifest_path.read_text(encoding="utf-8"))
    messages = [item["message"] for item in payload["errors"]]
    assert "trade_cal_missing_trade_date" in messages


def test_l1_collection_allows_closed_trade_date_without_daily_rows(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    fetcher = TuShareFetcher(client=ClosedDayClient(), max_retries=1)

    result = run_l1_collection(
        trade_date="20260215",
        source="tushare",
        config=config,
        fetcher=fetcher,
    )

    assert result.has_error is False
    payload = json.loads((result.artifacts_dir / "raw_counts.json").read_text(encoding="utf-8"))
    assert payload["gate_checks"]["trade_cal_is_open"] is False
