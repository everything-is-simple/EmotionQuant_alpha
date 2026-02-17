from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.trading.pipeline import run_paper_trade
from tests.unit.trading.support import build_config, prepare_s4_inputs


def test_risk_guard_rejects_limit_up_buy(tmp_path) -> None:
    config = build_config(tmp_path, ".env.s4.risk")
    trade_date = prepare_s4_inputs(config, ["20260218", "20260219"])

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE raw_daily SET open=high WHERE trade_date=? AND stock_code='000001'",
            [trade_date],
        )

    result = run_paper_trade(
        trade_date=trade_date,
        mode="paper",
        config=config,
    )
    assert result.has_error is True
    assert result.quality_status == "FAIL"
    assert result.go_nogo == "NO_GO"
    assert result.risk_event_count > 0

    risk_frame = pd.read_parquet(result.risk_events_path)
    assert not risk_frame.empty
    assert any(str(item) == "REJECT_LIMIT_UP" for item in risk_frame["event_type"].tolist())
