from __future__ import annotations

from pathlib import Path

from src.algorithms.mss.pipeline import run_mss_scoring
from src.backtest.pipeline import run_backtest
from src.config.config import Config
from src.data.fetch_batch_pipeline import run_fetch_batch
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.recommend import run_recommendation
from tests.unit.trade_day_guard import assert_all_valid_trade_days


def build_config(tmp_path: Path, env_name: str) -> Config:
    env_file = tmp_path / env_name
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def prepare_s4_inputs(
    config: Config, trade_dates: list[str], trade_date_for_s4: str | None = None
) -> str:
    assert len(trade_dates) >= 2
    assert_all_valid_trade_days(trade_dates, context="s4_inputs")
    if trade_date_for_s4 is not None:
        assert_all_valid_trade_days([trade_date_for_s4], context="s4_trade_date")
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

    backtest_end = trade_date_for_s4 or trade_dates[-1]
    s3 = run_backtest(
        start_date=trade_dates[0],
        end_date=backtest_end,
        engine="qlib",
        config=config,
    )
    assert s3.has_error is False
    if trade_date_for_s4 is not None:
        return trade_date_for_s4
    return trade_dates[-1]
