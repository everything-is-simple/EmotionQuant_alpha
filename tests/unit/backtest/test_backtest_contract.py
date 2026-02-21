from __future__ import annotations

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
    env_file = tmp_path / ".env.s3.backtest"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_s3_inputs(config: Config, trade_dates: list[str]) -> None:
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


def test_backtest_consumes_s3a_artifacts_and_generates_outputs(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_dates = ["20260218", "20260219"]
    _prepare_s3_inputs(config, trade_dates)

    result = run_backtest(
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
        engine="qlib",
        config=config,
    )
    assert result.has_error is False
    assert result.total_trades >= 0
    assert result.consumed_signal_rows > 0
    assert result.quality_status in {"PASS", "WARN"}
    assert result.go_nogo == "GO"
    assert result.bridge_check_status == "PASS"
    assert result.backtest_results_path.exists()
    assert result.backtest_trade_records_path.exists()
    assert result.ab_metric_summary_path.exists()
    assert result.gate_report_path.exists()
    assert result.consumption_path.exists()

    consumption_text = result.consumption_path.read_text(encoding="utf-8")
    assert "fetch_progress_path" in consumption_text
    assert "consumption_conclusion: ready_for_s4" in consumption_text
    if result.total_trades == 0:
        gate_text = result.gate_report_path.read_text(encoding="utf-8")
        assert "no_long_entry_signal_in_window" in gate_text

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        result_row = connection.execute(
            "SELECT quality_status, go_nogo, consumed_signal_rows, total_trades "
            "FROM backtest_results WHERE backtest_id=? LIMIT 1",
            [result.backtest_id],
        ).fetchone()
        trade_count = connection.execute(
            "SELECT COUNT(*) FROM backtest_trade_records WHERE backtest_id=?",
            [result.backtest_id],
        ).fetchone()

    assert result_row is not None
    assert result_row[0] in ("PASS", "WARN")
    assert result_row[1] == "GO"
    assert int(result_row[2]) > 0
    assert int(result_row[3]) >= 0
    assert trade_count is not None
    assert int(trade_count[0]) >= 0


def test_backtest_no_long_entry_signal_window_is_warn_not_fail(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_dates = ["20260218", "20260219"]
    _prepare_s3_inputs(config, trade_dates)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE integrated_recommendation "
            "SET recommendation='SELL', position_size=0.0, final_score=40.0 "
            "WHERE trade_date >= ? AND trade_date <= ?",
            [trade_dates[0], trade_dates[-1]],
        )

    result = run_backtest(
        start_date=trade_dates[0],
        end_date=trade_dates[-1],
        engine="qlib",
        config=config,
    )
    assert result.has_error is False
    assert result.total_trades == 0
    assert result.consumed_signal_rows > 0
    assert result.quality_status == "WARN"
    assert result.go_nogo == "GO"

    gate_text = result.gate_report_path.read_text(encoding="utf-8")
    assert "no_long_entry_signal_in_window" in gate_text
