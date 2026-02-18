from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.algorithms.mss.pipeline import run_mss_scoring
from src.backtest.pipeline import run_backtest
from src.config.config import Config
from src.data.fetch_batch_pipeline import run_fetch_batch
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.recommend import run_recommendation


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s3.core.coverage"
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


def _read_error_messages(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(item.get("message", ""))
        for item in payload.get("errors", [])
        if isinstance(item, dict)
    }


def test_backtest_blocks_when_core_signal_column_is_null(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_dates = ["20260218", "20260219"]
    _prepare_inputs(config, trade_dates)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE integrated_recommendation SET irs_score = NULL "
            "WHERE trade_date = '20260218'"
        )

    result = run_backtest(
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
        engine="qlib",
        config=config,
    )
    assert result.has_error is True
    assert result.quality_status == "FAIL"
    assert result.go_nogo == "NO_GO"
    errors = _read_error_messages(result.error_manifest_path)
    assert "integrated_recommendation_column_null_irs_score" in errors


def test_backtest_blocks_when_core_algorithm_table_missing_in_window(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_dates = ["20260218", "20260219"]
    _prepare_inputs(config, trade_dates)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "DELETE FROM irs_industry_daily WHERE trade_date >= '20260218' AND trade_date <= '20260219'"
        )

    result = run_backtest(
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
        engine="qlib",
        config=config,
    )
    assert result.has_error is True
    assert result.go_nogo == "NO_GO"
    errors = _read_error_messages(result.error_manifest_path)
    assert "irs_industry_daily_missing_for_backtest_window" in errors

    gate_text = result.gate_report_path.read_text(encoding="utf-8")
    assert "irs_industry_daily_rows_in_window: 0" in gate_text
    assert "core_algorithm_coverage_status: FAIL" in gate_text


def test_backtest_writes_core_algorithm_coverage_evidence(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_dates = ["20260218", "20260219"]
    _prepare_inputs(config, trade_dates)

    result = run_backtest(
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
        engine="qlib",
        config=config,
    )
    assert result.has_error is False

    consumption_text = result.consumption_path.read_text(encoding="utf-8")
    assert "core_algorithm_coverage_status: PASS" in consumption_text
    assert "irs_industry_daily_rows_in_window:" in consumption_text

    ab_text = result.ab_metric_summary_path.read_text(encoding="utf-8")
    assert "core_irs_proxy_return:" in ab_text
