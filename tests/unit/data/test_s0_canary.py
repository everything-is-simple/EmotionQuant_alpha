from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config.config import Config
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s0c.canary"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_s0c_canary_reports_error_levels_when_l1_missing(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    result = run_l2_snapshot(
        trade_date="20260215",
        source="tushare",
        config=config,
    )

    assert result.has_error is True
    assert result.error_manifest_path.name == "error_manifest.json"
    assert result.error_manifest_path.exists()
    assert result.canary_report_path.exists()

    payload: dict[str, Any] = json.loads(result.error_manifest_path.read_text(encoding="utf-8"))
    assert payload["error_count"] > 0
    assert all("error_level" in item for item in payload["errors"])
    messages = [item["message"] for item in payload["errors"]]
    assert "duckdb_not_found" in messages

    report_text = result.canary_report_path.read_text(encoding="utf-8")
    assert "- status: FAIL" in report_text

