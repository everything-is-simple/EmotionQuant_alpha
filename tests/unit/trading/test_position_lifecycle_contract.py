from __future__ import annotations

import pandas as pd

from src.trading.pipeline import run_paper_trade
from tests.unit.trading.support import build_config, prepare_s4_inputs


def test_position_lifecycle_has_t1_freeze_fields(tmp_path) -> None:
    config = build_config(tmp_path, ".env.s4.position")
    trade_date = prepare_s4_inputs(
        config,
        ["20260218", "20260219", "20260220"],
        trade_date_for_s4="20260219",
    )

    result = run_paper_trade(
        trade_date=trade_date,
        mode="paper",
        config=config,
    )
    assert result.has_error is False
    frame = pd.read_parquet(result.positions_path)
    assert not frame.empty
    assert all(str(can_sell) >= str(buy_date) for can_sell, buy_date in zip(
        frame["can_sell_date"].tolist(),
        frame["buy_date"].tolist(),
        strict=False,
    ))
    assert all(bool(item) for item in frame["is_frozen"].tolist())
