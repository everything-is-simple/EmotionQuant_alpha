from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

from src.algorithms.mss.pipeline import run_mss_scoring
from src.backtest.pipeline import run_backtest
from src.config.config import Config
from src.data.fetch_batch_pipeline import run_fetch_batch
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.recommend import run_recommendation


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s3.repro"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_inputs(config: Config, trade_dates: list[str]) -> None:
    assert trade_dates
    run_fetch_batch(
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
        batch_size=365,
        workers=3,
        config=config,
    )
    for trade_date in trade_dates:
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


def test_backtest_is_reproducible_for_same_inputs(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_dates = ["20260218", "20260219"]
    _prepare_inputs(config, trade_dates)

    first = run_backtest(
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
        engine="qlib",
        config=config,
    )
    assert first.has_error is False
    first_results = pd.read_parquet(first.backtest_results_path).drop(columns=["created_at"])
    first_trades = (
        pd.read_parquet(first.backtest_trade_records_path)
        .drop(columns=["created_at"])
        .sort_values(by=["trade_date", "stock_code"])
        .reset_index(drop=True)
    )

    second = run_backtest(
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
        engine="qlib",
        config=config,
    )
    assert second.has_error is False
    second_results = pd.read_parquet(second.backtest_results_path).drop(columns=["created_at"])
    second_trades = (
        pd.read_parquet(second.backtest_trade_records_path)
        .drop(columns=["created_at"])
        .sort_values(by=["trade_date", "stock_code"])
        .reset_index(drop=True)
    )

    assert first.backtest_id == second.backtest_id
    assert first.total_trades == second.total_trades
    assert first.quality_status == second.quality_status
    assert_frame_equal(first_results, second_results, check_dtype=False)
    assert_frame_equal(first_trades, second_trades, check_dtype=False)
