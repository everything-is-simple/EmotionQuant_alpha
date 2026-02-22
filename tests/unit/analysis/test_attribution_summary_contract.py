from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.analysis.pipeline import run_analysis
from tests.unit.analysis.support import (
    build_analysis_config,
    database_path,
    seed_attribution_tables,
)
from tests.unit.trade_day_guard import latest_open_trade_days


def test_attribution_summary_generates_json_and_table(tmp_path: Path) -> None:
    config = build_analysis_config(tmp_path, ".env.s3b.attribution")
    trade_date = latest_open_trade_days(1)[0]
    seed_attribution_tables(config, trade_date)

    result = run_analysis(
        config=config,
        trade_date=trade_date,
        run_attribution_summary=True,
    )
    assert result.has_error is False
    assert result.quality_status in {"PASS", "WARN"}
    assert result.go_nogo == "GO"
    assert result.attribution_summary_path.exists()

    payload = json.loads(result.attribution_summary_path.read_text(encoding="utf-8"))
    assert payload["trade_date"] == trade_date
    assert "mss_attribution" in payload
    assert "irs_attribution" in payload
    assert "pas_attribution" in payload
    assert "attribution_method" in payload

    with duckdb.connect(str(database_path(config)), read_only=True) as connection:
        row = connection.execute(
            "SELECT trade_date, sample_count FROM signal_attribution WHERE trade_date = ? LIMIT 1",
            [trade_date],
        ).fetchone()
    assert row is not None
    assert str(row[0]) == trade_date
    assert int(row[1]) >= 0


def test_attribution_summary_no_filled_trade_is_warn(tmp_path: Path) -> None:
    config = build_analysis_config(tmp_path, ".env.s3b.attribution.empty")
    trade_date = latest_open_trade_days(1)[0]
    seed_attribution_tables(config, trade_date)
    with duckdb.connect(str(database_path(config))) as connection:
        connection.execute("DELETE FROM trade_records WHERE trade_date = ?", [trade_date])

    result = run_analysis(
        config=config,
        trade_date=trade_date,
        run_attribution_summary=True,
    )
    assert result.has_error is False
    assert result.quality_status == "WARN"
    assert result.go_nogo == "GO"
    payload = json.loads(result.attribution_summary_path.read_text(encoding="utf-8"))
    assert payload["attribution_method"] == "na_no_filled_trade"
    assert int(payload["sample_count"]) == 0
