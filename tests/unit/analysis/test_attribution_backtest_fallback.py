from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.analysis.pipeline import run_analysis
from tests.unit.analysis.support import build_analysis_config, database_path
from tests.unit.trade_day_guard import latest_open_trade_days


def _seed_with_backtest_fallback(config, trade_date: str) -> None:
    """Seed: trade_records 为空, backtest_trade_records 有成交, integrated_recommendation 有数据。"""
    db_path = database_path(config)
    with duckdb.connect(str(db_path)) as connection:
        connection.execute("DROP TABLE IF EXISTS integrated_recommendation")
        connection.execute("DROP TABLE IF EXISTS trade_records")
        connection.execute("DROP TABLE IF EXISTS backtest_trade_records")
        connection.execute("DROP TABLE IF EXISTS signal_attribution")
        connection.execute(
            "CREATE TABLE integrated_recommendation ("
            "trade_date VARCHAR, stock_code VARCHAR, mss_score DOUBLE, irs_score DOUBLE, pas_score DOUBLE, "
            "entry DOUBLE, final_score DOUBLE)"
        )
        connection.execute(
            "INSERT INTO integrated_recommendation VALUES "
            "(?, '000001', 62, 58, 61, 10.0, 60), "
            "(?, '000002', 64, 59, 63, 20.0, 62)",
            [trade_date, trade_date],
        )
        # trade_records 存在但无 filled buy（空表）
        connection.execute(
            "CREATE TABLE trade_records ("
            "trade_date VARCHAR, stock_code VARCHAR, direction VARCHAR, status VARCHAR, "
            "price DOUBLE, amount DOUBLE, total_fee DOUBLE)"
        )
        # backtest_trade_records 有成交数据
        connection.execute(
            "CREATE TABLE backtest_trade_records ("
            "backtest_id VARCHAR, trade_date VARCHAR, signal_date VARCHAR, execute_date VARCHAR, "
            "stock_code VARCHAR, direction VARCHAR, filled_price DOUBLE, shares BIGINT, "
            "amount DOUBLE, pnl DOUBLE, pnl_pct DOUBLE, recommendation VARCHAR, "
            "final_score DOUBLE, risk_reward_ratio DOUBLE, integration_mode VARCHAR, "
            "weight_plan_id VARCHAR, status VARCHAR, reject_reason VARCHAR, "
            "t1_restriction_hit BOOLEAN, limit_guard_result VARCHAR, session_guard_result VARCHAR, "
            "contract_version VARCHAR, created_at VARCHAR)"
        )
        connection.execute(
            "INSERT INTO backtest_trade_records VALUES "
            "('BT_TEST', ?, ?, ?, '000001', 'buy', 10.2, 100, 1020, 20.0, 0.02, "
            "'STRONG_BUY', 60, 2.0, 'weighted', 'wp-001', 'filled', '', false, 'PASS', 'PASS', 'nc-v1', '2026-01-01'), "
            "('BT_TEST', ?, ?, ?, '000002', 'buy', 20.5, 100, 2050, 50.0, 0.025, "
            "'BUY', 62, 1.8, 'weighted', 'wp-001', 'filled', '', false, 'PASS', 'PASS', 'nc-v1', '2026-01-01')",
            [trade_date, trade_date, trade_date, trade_date, trade_date, trade_date],
        )


def test_attribution_backtest_fallback(tmp_path: Path) -> None:
    config = build_analysis_config(tmp_path, ".env.s3b.attribution.bt_fallback")
    trade_date = latest_open_trade_days(1)[0]
    _seed_with_backtest_fallback(config, trade_date)

    result = run_analysis(
        config=config,
        trade_date=trade_date,
        run_attribution_summary=True,
    )
    assert result.has_error is False
    assert result.quality_status == "WARN"
    assert result.go_nogo == "GO"
    assert result.attribution_summary_path.exists()

    payload = json.loads(result.attribution_summary_path.read_text(encoding="utf-8"))
    assert payload["trade_date"] == trade_date
    assert payload["attribution_method"].startswith("backtest_fallback_")
    assert int(payload["sample_count"]) > 0
    assert "mss_attribution" in payload
    assert "irs_attribution" in payload
    assert "pas_attribution" in payload
