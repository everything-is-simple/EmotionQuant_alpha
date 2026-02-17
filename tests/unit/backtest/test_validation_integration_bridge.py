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


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s3.bridge"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_inputs_without_bridge(config: Config, trade_dates: list[str]) -> None:
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
            with_validation_bridge=False,
            config=config,
        )
        assert s2b.has_error is False


def test_backtest_blocks_when_validation_bridge_is_missing(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_dates = ["20260218", "20260219"]
    _prepare_inputs_without_bridge(config, trade_dates)

    result = run_backtest(
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
        engine="qlib",
        config=config,
    )
    assert result.has_error is True
    assert result.quality_status == "FAIL"
    assert result.go_nogo == "NO_GO"
    assert result.bridge_check_status == "FAIL"
    gate_text = result.gate_report_path.read_text(encoding="utf-8")
    assert "bridge_check_status: FAIL" in gate_text
    assert "weight_plan_id_baseline_not_allowed_for_s3" in gate_text
