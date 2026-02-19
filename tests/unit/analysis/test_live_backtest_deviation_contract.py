from __future__ import annotations

from pathlib import Path

import duckdb

from src.analysis.pipeline import run_analysis
from tests.unit.analysis.support import (
    build_analysis_config,
    database_path,
    seed_deviation_tables,
)


def test_live_backtest_deviation_generates_report_and_table(tmp_path: Path) -> None:
    config = build_analysis_config(tmp_path, ".env.s3b.deviation")
    trade_date = "20260219"
    seed_deviation_tables(config, trade_date)

    result = run_analysis(
        config=config,
        trade_date=trade_date,
        deviation_mode="live-backtest",
    )
    assert result.has_error is False
    assert result.quality_status in {"PASS", "WARN"}
    assert result.go_nogo == "GO"
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
