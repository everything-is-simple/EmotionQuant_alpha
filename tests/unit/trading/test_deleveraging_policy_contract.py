from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.stress.pipeline import run_stress
from src.trading.pipeline import run_paper_trade
from tests.unit.trade_day_guard import latest_open_trade_days
from tests.unit.trading.support import build_config, prepare_s4_inputs


def test_deleveraging_policy_uses_s3b_deviation_as_traceable_source(tmp_path: Path) -> None:
    config = build_config(tmp_path, ".env.s4b.policy")
    trade_dates = latest_open_trade_days(3)
    trade_date = prepare_s4_inputs(
        config,
        trade_dates,
        trade_date_for_s4=trade_dates[1],
    )
    warmup = run_paper_trade(
        trade_date=trade_date,
        mode="paper",
        config=config,
    )
    assert warmup.has_error is False

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS live_backtest_deviation ("
            "trade_date VARCHAR, signal_deviation DOUBLE, execution_deviation DOUBLE, "
            "cost_deviation DOUBLE, total_deviation DOUBLE, dominant_component VARCHAR, created_at VARCHAR)"
        )
        connection.execute("DELETE FROM live_backtest_deviation WHERE trade_date = ?", [trade_date])
        connection.execute(
            "INSERT INTO live_backtest_deviation VALUES (?, ?, ?, ?, ?, ?, ?)",
            [trade_date, 0.01, 0.02, 0.08, 0.08, "cost", "2026-02-22T00:00:00+00:00"],
        )

    result = run_stress(
        trade_date=trade_date,
        scenario="limit_down_chain",
        config=config,
    )
    payload = json.loads(result.deleveraging_policy_snapshot_path.read_text(encoding="utf-8"))
    assert payload["policy_source"]["source"] == "live_backtest_deviation"
    assert payload["policy_source"]["dominant_component"] == "cost"
    assert float(payload["target_deleveraging_ratio"]) == 0.6

    repair_result = run_stress(
        trade_date=trade_date,
        scenario="limit_down_chain",
        config=config,
        repair="s4br",
    )
    repair_payload = json.loads(
        repair_result.deleveraging_policy_snapshot_path.read_text(encoding="utf-8")
    )
    assert repair_payload["repair"] == "s4br"
    assert float(repair_payload["target_deleveraging_ratio"]) == 0.7
    assert repair_result.s4br_patch_note_path is not None
    assert repair_result.s4br_delta_report_path is not None
    assert repair_result.s4br_patch_note_path.exists()
    assert repair_result.s4br_delta_report_path.exists()
