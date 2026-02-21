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
    signal_dates = ["20260218", "20260219"]
    extra_dates = ["20260220"]
    _prepare_inputs(config, signal_dates, extra_dates)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE integrated_recommendation "
            "SET recommendation='BUY', position_size=0.5, final_score=75.0 "
            "WHERE trade_date IN ('20260218', '20260219') AND stock_code='000001'"
        )
        # Make first execute day hit main-board +10% limit-up to force buy rejection.
        connection.execute(
            "UPDATE raw_daily "
            "SET open=close*1.1, high=close*1.1 "
            "WHERE trade_date='20260219' AND stock_code='000001'"
        )

    result = run_backtest(
        start_date="20260218",
        end_date="20260220",
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


def test_backtest_rejects_buy_when_liquidity_dryup(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    signal_dates = ["20260218", "20260219"]
    extra_dates = ["20260220"]
    _prepare_inputs(config, signal_dates, extra_dates)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE integrated_recommendation "
            "SET recommendation='BUY', position_size=0.5, final_score=75.0 "
            "WHERE trade_date IN ('20260218', '20260219') AND stock_code='000001'"
        )
        connection.execute(
            "UPDATE raw_daily "
            "SET vol=10, amount=1000, open=10.1, high=10.2, low=10.0, close=10.1 "
            "WHERE trade_date='20260219' AND stock_code='000001'"
        )

    result = run_backtest(
        start_date="20260218",
        end_date="20260220",
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
