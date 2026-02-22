from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.stress.pipeline import run_stress
from src.trading.pipeline import run_paper_trade
from tests.unit.trade_day_guard import latest_open_trade_days
from tests.unit.trading.support import build_config, prepare_s4_inputs


def test_stress_limit_down_chain_generates_defense_artifacts(tmp_path: Path) -> None:
    config = build_config(tmp_path, ".env.s4b.limit_down")
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

    result = run_stress(
        trade_date=trade_date,
        scenario="limit_down_chain",
        config=config,
    )
    assert result.has_error is False
    assert result.gate_status in {"PASS", "WARN"}
    assert result.go_nogo == "GO"
    assert result.extreme_defense_report_path.exists()
    assert result.deleveraging_policy_snapshot_path.exists()
    assert result.stress_trade_replay_path.exists()
    assert result.consumption_path.exists()
    assert result.gate_report_path.exists()

    replay_frame = pd.read_csv(result.stress_trade_replay_path)
    assert not replay_frame.empty
    assert (replay_frame["blocked_shares"] > 0).any()
    assert int(replay_frame["executed_sell_shares"].sum()) == 0
    assert "REJECT_LIMIT_DOWN_CHAIN" in set(replay_frame["reject_reason"].astype(str))
