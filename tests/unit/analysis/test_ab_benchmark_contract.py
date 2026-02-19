from __future__ import annotations

from pathlib import Path

import duckdb

from src.analysis.pipeline import run_analysis
from tests.unit.analysis.support import (
    build_analysis_config,
    database_path,
    seed_ab_benchmark_tables,
)


def test_ab_benchmark_generates_report_and_metrics_table(tmp_path: Path) -> None:
    config = build_analysis_config(tmp_path, ".env.s3b.ab")
    trade_dates = ["20260218", "20260219"]
    seed_ab_benchmark_tables(config, trade_dates[0], trade_dates[-1])

    result = run_analysis(
        config=config,
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
        run_ab_benchmark=True,
    )
    assert result.has_error is False
    assert result.quality_status in {"PASS", "WARN"}
    assert result.go_nogo == "GO"
    assert result.ab_benchmark_report_path.exists()
    report_text = result.ab_benchmark_report_path.read_text(encoding="utf-8")
    assert "A_sentiment_main_total_return" in report_text
    assert "conclusion:" in report_text

    with duckdb.connect(str(database_path(config)), read_only=True) as connection:
        row = connection.execute(
            "SELECT metric_date, total_return FROM performance_metrics WHERE metric_date = ? LIMIT 1",
            [trade_dates[-1]],
        ).fetchone()
    assert row is not None
    assert str(row[0]) == trade_dates[-1]
