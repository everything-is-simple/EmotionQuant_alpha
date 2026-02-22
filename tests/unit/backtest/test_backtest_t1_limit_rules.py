from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.algorithms.mss.pipeline import run_mss_scoring
from src.backtest.pipeline import run_backtest
from src.config.config import Config
from src.data.fetch_batch_pipeline import run_fetch_batch
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.recommend import run_recommendation
from tests.unit.trade_day_guard import assert_all_valid_trade_days, latest_open_trade_days


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s3.t1_limit"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_inputs(config: Config, signal_dates: list[str], extra_dates: list[str]) -> None:
    all_dates = sorted(set(signal_dates + extra_dates))
    assert_all_valid_trade_days(all_dates, context="s3_t1_limit_inputs")
    run_fetch_batch(
        start_date=all_dates[0],
        end_date=all_dates[-1],
        batch_size=365,
        workers=3,
        config=config,
    )
    for trade_date in all_dates:
        run_l1_collection(
            trade_date=trade_date,
            source="tushare",
            config=config,
            fetcher=TuShareFetcher(max_retries=1),
        )
        run_l2_snapshot(
            trade_date=trade_date,
            source="tushare",
            config=config,
        )
        if trade_date not in signal_dates:
            continue
        run_mss_scoring(
            trade_date=trade_date,
            config=config,
        )
        s2a = run_recommendation(
            trade_date=trade_date,
            mode="mss_irs_pas",
            with_validation=True,
            with_validation_bridge=False,
            config=config,
        )
        assert s2a.has_error is False
        s2b = run_recommendation(
            trade_date=trade_date,
            mode="integrated",
            with_validation=False,
            with_validation_bridge=True,
            config=config,
        )
        assert s2b.has_error is False


def test_backtest_applies_t1_and_limit_rules(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    rolling_dates = latest_open_trade_days(3)
    signal_dates = rolling_dates[:2]
    extra_dates = [rolling_dates[2]]
    _prepare_inputs(config, signal_dates, extra_dates)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE integrated_recommendation "
            "SET recommendation='BUY', position_size=0.5, final_score=75.0 "
            "WHERE trade_date IN (?, ?) AND stock_code='000001'",
            [signal_dates[0], signal_dates[1]],
        )
        # Make first execute day hit main-board +10% limit-up to force buy rejection.
        connection.execute(
            "UPDATE raw_daily "
            "SET open=close*1.1, high=close*1.1 "
            "WHERE trade_date=? AND stock_code='000001'",
            [signal_dates[1]],
        )

    result = run_backtest(
        start_date=signal_dates[0],
        end_date=extra_dates[0],
        engine="qlib",
        config=config,
    )
    assert result.has_error is False

    frame = pd.read_parquet(result.backtest_trade_records_path)
    filled_buys = frame[(frame["status"] == "filled") & (frame["direction"] == "buy")]
    assert not filled_buys.empty
    assert all(
        str(exec_date) > str(signal_date)
        for exec_date, signal_date in zip(
            filled_buys["execute_date"].tolist(),
            filled_buys["signal_date"].tolist(),
            strict=False,
        )
    )

    rejected_limit_up = frame[
        (frame["status"] == "rejected") & (frame["reject_reason"] == "REJECT_LIMIT_UP")
    ]
    assert not rejected_limit_up.empty


def test_backtest_rejects_buy_when_one_word_board(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    rolling_dates = latest_open_trade_days(3)
    signal_dates = rolling_dates[:2]
    extra_dates = [rolling_dates[2]]
    _prepare_inputs(config, signal_dates, extra_dates)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE integrated_recommendation "
            "SET recommendation='BUY', position_size=0.5, final_score=75.0 "
            "WHERE trade_date IN (?, ?) AND stock_code='000001'",
            [signal_dates[0], signal_dates[1]],
        )
        connection.execute(
            "UPDATE raw_daily "
            "SET open=10.05, high=10.05, low=10.05, close=10.05, vol=800000, amount=8040000 "
            "WHERE trade_date=? AND stock_code='000001'",
            [signal_dates[1]],
        )

    result = run_backtest(
        start_date=signal_dates[0],
        end_date=extra_dates[0],
        engine="qlib",
        config=config,
    )
    assert result.has_error is False

    frame = pd.read_parquet(result.backtest_trade_records_path)
    rejected_one_word = frame[
        (frame["status"] == "rejected") & (frame["reject_reason"] == "REJECT_ONE_WORD_BOARD")
    ]
    assert not rejected_one_word.empty

    gate_report = result.gate_report_path.read_text(encoding="utf-8")
    assert "one_word_board_blocked_count:" in gate_report


def test_backtest_rejects_buy_when_liquidity_dryup(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    rolling_dates = latest_open_trade_days(3)
    signal_dates = rolling_dates[:2]
    extra_dates = [rolling_dates[2]]
    _prepare_inputs(config, signal_dates, extra_dates)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE integrated_recommendation "
            "SET recommendation='BUY', position_size=0.5, final_score=75.0 "
            "WHERE trade_date IN (?, ?) AND stock_code='000001'",
            [signal_dates[0], signal_dates[1]],
        )
        connection.execute(
            "UPDATE raw_daily "
            "SET vol=10, amount=1000, open=10.1, high=10.2, low=10.0, close=10.1 "
            "WHERE trade_date=? AND stock_code='000001'",
            [signal_dates[1]],
        )

    result = run_backtest(
        start_date=signal_dates[0],
        end_date=extra_dates[0],
        engine="qlib",
        config=config,
    )
    assert result.has_error is False
    assert result.quality_status in {"WARN", "PASS"}

    frame = pd.read_parquet(result.backtest_trade_records_path)
    rejected_dryup = frame[
        (frame["status"] == "rejected") & (frame["reject_reason"] == "REJECT_LIQUIDITY_DRYUP")
    ]
    assert not rejected_dryup.empty

    gate_report = result.gate_report_path.read_text(encoding="utf-8")
    assert "liquidity_dryup_blocked_count:" in gate_report


def test_backtest_rejects_buy_when_low_fill_probability(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    rolling_dates = latest_open_trade_days(3)
    signal_dates = rolling_dates[:2]
    extra_dates = [rolling_dates[2]]
    _prepare_inputs(config, signal_dates, extra_dates)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE integrated_recommendation "
            "SET recommendation='BUY', position_size=0.5, final_score=75.0 "
            "WHERE trade_date IN (?, ?) AND stock_code='000001'",
            [signal_dates[0], signal_dates[1]],
        )
        connection.execute(
            "UPDATE raw_daily "
            "SET vol=200000, amount=3000000, open=10.1, high=10.2, low=10.0, close=10.1 "
            "WHERE trade_date=? AND stock_code='000001'",
            [signal_dates[1]],
        )

    result = run_backtest(
        start_date=signal_dates[0],
        end_date=extra_dates[0],
        engine="qlib",
        config=config,
    )
    assert result.has_error is False
    assert result.quality_status in {"WARN", "PASS"}

    frame = pd.read_parquet(result.backtest_trade_records_path)
    rejected_low_fill = frame[
        (frame["status"] == "rejected") & (frame["reject_reason"] == "REJECT_LOW_FILL_PROB")
    ]
    assert not rejected_low_fill.empty

    gate_report = result.gate_report_path.read_text(encoding="utf-8")
    assert "low_fill_prob_blocked_count:" in gate_report
