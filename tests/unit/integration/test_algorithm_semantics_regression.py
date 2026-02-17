from __future__ import annotations

from pathlib import Path

import duckdb

from src.algorithms.mss.pipeline import run_mss_scoring
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.recommend import run_recommendation


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2c.semantics"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_s2a_inputs(config: Config, trade_date: str) -> None:
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


def test_bridge_mode_blocks_on_fail_gate(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260218"
    _prepare_s2a_inputs(config, trade_date)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE validation_gate_decision "
            "SET final_gate='FAIL', validation_prescription='manual_fail', selected_weight_plan='vp_balanced_v1' "
            "WHERE trade_date=?",
            [trade_date],
        )

    result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        with_validation_bridge=True,
        config=config,
    )
    assert result.has_error is True
    assert result.quality_gate_status == "FAIL"
    assert result.go_nogo == "NO_GO"
    assert result.integrated_count == 0
    report_text = result.quality_gate_report_path.read_text(encoding="utf-8")
    assert "validation_gate_fail" in report_text


def test_unknown_cycle_caps_positive_signal_to_hold_in_bridge_mode(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260218"
    _prepare_s2a_inputs(config, trade_date)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE mss_panorama SET mss_cycle='unknown', mss_score=95.0, mss_trend='up' WHERE trade_date=?",
            [trade_date],
        )
        connection.execute(
            "UPDATE irs_industry_daily SET irs_score=95.0, recommendation='STRONG_BUY' WHERE trade_date=?",
            [trade_date],
        )
        connection.execute(
            "UPDATE stock_pas_daily SET pas_score=95.0, pas_direction='bullish', risk_reward_ratio=2.0 WHERE trade_date=?",
            [trade_date],
        )
        connection.execute(
            "UPDATE validation_gate_decision SET final_gate='PASS', selected_weight_plan='vp_balanced_v1' WHERE trade_date=?",
            [trade_date],
        )

    result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        with_validation_bridge=True,
        config=config,
    )
    assert result.has_error is False
    assert result.integrated_count > 0

    with duckdb.connect(str(db_path), read_only=True) as connection:
        recommendations = connection.execute(
            "SELECT DISTINCT recommendation FROM integrated_recommendation WHERE trade_date=?",
            [trade_date],
        ).fetchall()
    assert recommendations
    assert all(str(row[0]) == "HOLD" for row in recommendations)
