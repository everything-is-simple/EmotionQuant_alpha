from __future__ import annotations

from pathlib import Path

import duckdb

from src.trading.pipeline import run_paper_trade
from tests.unit.trade_day_guard import latest_open_trade_days
from tests.unit.trading.support import build_config, prepare_s4_inputs


def test_order_pipeline_generates_trade_records(tmp_path: Path) -> None:
    config = build_config(tmp_path, ".env.s4.order")
    trade_date = prepare_s4_inputs(config, latest_open_trade_days(2))

    result = run_paper_trade(
        trade_date=trade_date,
        mode="paper",
        config=config,
    )
    assert result.has_error is False
    assert result.quality_status in {"PASS", "WARN"}
    assert result.go_nogo == "GO"
    assert result.total_orders > 0
    assert result.filled_orders > 0
    assert result.trade_records_path.exists()
    assert result.positions_path.exists()
    assert result.risk_events_path.exists()
    assert result.paper_trade_replay_path.exists()

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT risk_reward_ratio, t1_restriction_hit, limit_guard_result, session_guard_result "
            "FROM trade_records WHERE trade_date=? AND status='filled' LIMIT 1",
            [trade_date],
        ).fetchone()
        trade_count = connection.execute(
            "SELECT COUNT(*) FROM trade_records WHERE trade_date=?",
            [trade_date],
        ).fetchone()

    assert row is not None
    assert float(row[0]) >= 1.0
    assert row[1] in (False, 0)
    assert str(row[2]) != ""
    assert str(row[3]) != ""
    assert trade_count is not None
    assert int(trade_count[0]) > 0
