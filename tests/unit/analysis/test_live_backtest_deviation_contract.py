from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.analysis.pipeline import run_analysis
from tests.unit.analysis.support import (
    build_analysis_config,
    database_path,
    seed_deviation_tables,
)
from tests.unit.trade_day_guard import latest_open_trade_days


def test_live_backtest_deviation_generates_report_and_table(tmp_path: Path) -> None:
    config = build_analysis_config(tmp_path, ".env.s3b.deviation")
    trade_date = latest_open_trade_days(1)[0]
    seed_deviation_tables(config, trade_date)

    result = run_analysis(
        config=config,
        trade_date=trade_date,
        deviation_mode="live-backtest",
    )
    assert result.has_error is False
    assert result.quality_status in {"PASS", "WARN"}
    assert result.go_nogo == "GO"
    assert result.error_manifest_path.name == "error_manifest.json"
    assert result.error_manifest_path.exists()
    assert result.live_backtest_deviation_report_path.exists()
    report_text = result.live_backtest_deviation_report_path.read_text(encoding="utf-8")
    assert "signal_deviation" in report_text
    assert "execution_deviation" in report_text
    assert "dominant_component" in report_text

    with duckdb.connect(str(database_path(config)), read_only=True) as connection:
        row = connection.execute(
            "SELECT trade_date, dominant_component FROM live_backtest_deviation WHERE trade_date = ? LIMIT 1",
            [trade_date],
        ).fetchone()
    assert row is not None
    assert str(row[0]) == trade_date
    assert str(row[1]) in {"signal", "execution", "cost"}


def test_live_backtest_deviation_missing_integrated_table_returns_nogo(tmp_path: Path) -> None:
    config = build_analysis_config(tmp_path, ".env.s3b.deviation.missing.ir")
    trade_date = latest_open_trade_days(1)[0]
    seed_deviation_tables(config, trade_date)
    with duckdb.connect(str(database_path(config))) as connection:
        connection.execute("DROP TABLE integrated_recommendation")

    result = run_analysis(
        config=config,
        trade_date=trade_date,
        deviation_mode="live-backtest",
    )
    assert result.has_error is True
    assert result.quality_status == "FAIL"
    assert result.go_nogo == "NO_GO"
    assert result.error_manifest_path.name == "error_manifest.json"
    assert result.gate_report_path.exists()
    assert result.error_manifest_path.exists()

    gate_text = result.gate_report_path.read_text(encoding="utf-8")
    assert "quality_status: FAIL" in gate_text
    assert "go_nogo: NO_GO" in gate_text

    manifest = json.loads(result.error_manifest_path.read_text(encoding="utf-8"))
    assert int(manifest["error_count"]) >= 1
    assert any(item["message"] == "integrated_recommendation_missing" for item in manifest["errors"])


def test_live_backtest_deviation_empty_both_sides_is_warn(tmp_path: Path) -> None:
    config = build_analysis_config(tmp_path, ".env.s3b.deviation.empty")
    trade_date = latest_open_trade_days(1)[0]
    seed_deviation_tables(config, trade_date)
    with duckdb.connect(str(database_path(config))) as connection:
        connection.execute("DELETE FROM trade_records WHERE trade_date = ?", [trade_date])
        connection.execute("DELETE FROM backtest_trade_records WHERE trade_date = ?", [trade_date])

    result = run_analysis(
        config=config,
        trade_date=trade_date,
        deviation_mode="live-backtest",
    )
    assert result.has_error is False
    assert result.quality_status == "WARN"
    assert result.go_nogo == "GO"
    assert result.error_manifest_path.exists()
    manifest = json.loads(result.error_manifest_path.read_text(encoding="utf-8"))
    assert int(manifest["error_count"]) == 0
    assert "deviation_not_applicable_no_filled_trade" in manifest["warnings"]


def test_live_backtest_deviation_fallbacks_to_signal_date_when_trade_date_is_empty(
    tmp_path: Path,
) -> None:
    config = build_analysis_config(tmp_path, ".env.s3b.deviation.signal-fallback")
    trade_date = latest_open_trade_days(1)[0]
    seed_deviation_tables(config, trade_date)
    with duckdb.connect(str(database_path(config))) as connection:
        connection.execute(
            "UPDATE backtest_trade_records SET trade_date = '20991231' WHERE signal_date = ?",
            [trade_date],
        )

    result = run_analysis(
        config=config,
        trade_date=trade_date,
        deviation_mode="live-backtest",
    )
    assert result.has_error is False
    assert result.quality_status in {"PASS", "WARN"}
    assert result.go_nogo == "GO"
    manifest = json.loads(result.error_manifest_path.read_text(encoding="utf-8"))
    assert int(manifest["error_count"]) == 0
    assert "deviation_backtest_trade_date_empty_fallback_signal_date" in manifest["warnings"]


def test_live_backtest_deviation_backtest_side_empty_is_warn_not_fail(tmp_path: Path) -> None:
    config = build_analysis_config(tmp_path, ".env.s3b.deviation.partial")
    trade_date = latest_open_trade_days(1)[0]
    seed_deviation_tables(config, trade_date)
    with duckdb.connect(str(database_path(config))) as connection:
        connection.execute("DELETE FROM backtest_trade_records WHERE trade_date = ?", [trade_date])

    result = run_analysis(
        config=config,
        trade_date=trade_date,
        deviation_mode="live-backtest",
    )
    assert result.has_error is False
    assert result.quality_status == "WARN"
    assert result.go_nogo == "GO"
    manifest = json.loads(result.error_manifest_path.read_text(encoding="utf-8"))
    assert int(manifest["error_count"]) == 0
    assert "backtest_trade_records_empty_for_trade_date" in manifest["warnings"]
    assert "deviation_based_on_partial_samples" in manifest["warnings"]
