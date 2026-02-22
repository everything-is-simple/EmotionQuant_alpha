from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.trading.pipeline import run_paper_trade
from tests.unit.trade_day_guard import latest_open_trade_days
from tests.unit.trading.support import build_config, prepare_s4_inputs


def test_position_lifecycle_has_t1_freeze_fields(tmp_path) -> None:
    config = build_config(tmp_path, ".env.s4.position")
    dates = latest_open_trade_days(3)
    trade_date = prepare_s4_inputs(
        config,
        dates,
        trade_date_for_s4=dates[1],
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


def test_position_lifecycle_retries_limit_down_sell_next_day(tmp_path) -> None:
    config = build_config(tmp_path, ".env.s4.position.retry")
    dates = latest_open_trade_days(4)
    day0, day1, day2, day3 = dates
    prepare_s4_inputs(
        config,
        dates,
        trade_date_for_s4=day1,
    )

    first_day = run_paper_trade(
        trade_date=day1,
        mode="paper",
        config=config,
    )
    assert first_day.has_error is False
    first_positions = pd.read_parquet(first_day.positions_path)
    assert not first_positions.empty
    stock_code = str(first_positions.iloc[0]["stock_code"])

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE raw_daily SET open=1.0, high=1.01, low=1.0, close=1.0 "
            "WHERE trade_date=? AND stock_code=?",
            [day2, stock_code],
        )

    blocked_day = run_paper_trade(
        trade_date=day2,
        mode="paper",
        config=config,
    )
    assert blocked_day.has_error is False
    blocked_trades = pd.read_parquet(blocked_day.trade_records_path)
    assert any(
        str(direction) == "sell" and str(reason) == "REJECT_LIMIT_DOWN"
        for direction, reason in zip(
            blocked_trades["direction"].tolist(),
            blocked_trades["reject_reason"].tolist(),
            strict=False,
        )
    )
    blocked_risk = pd.read_parquet(blocked_day.risk_events_path)
    assert any(str(event) == "SELL_RETRY_NEXT_DAY" for event in blocked_risk["event_type"].tolist())

    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE raw_daily SET open=10.0, high=10.2, low=9.8, close=10.1 "
            "WHERE trade_date=? AND stock_code=?",
            [day3, stock_code],
        )

    retry_day = run_paper_trade(
        trade_date=day3,
        mode="paper",
        config=config,
    )
    assert retry_day.has_error is False
    retry_trades = pd.read_parquet(retry_day.trade_records_path)
    assert any(
        str(code) == stock_code and str(direction) == "sell" and str(status) == "filled"
        for code, direction, status in zip(
            retry_trades["stock_code"].tolist(),
            retry_trades["direction"].tolist(),
            retry_trades["status"].tolist(),
            strict=False,
        )
    )
