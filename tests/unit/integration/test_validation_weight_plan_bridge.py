from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from src.algorithms.mss.pipeline import run_mss_scoring
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.recommend import run_recommendation


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2c.bridge"
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


def test_s2c_bridge_consumes_selected_weight_plan(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260218"
    _prepare_s2a_inputs(config, trade_date)

    result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        with_validation_bridge=True,
        config=config,
    )
    assert result.has_error is False
    assert result.integrated_count > 0
    assert result.quality_gate_status in {"PASS", "WARN"}

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        gate_row = connection.execute(
            "SELECT selected_weight_plan FROM validation_gate_decision WHERE trade_date=?",
            [trade_date],
        ).fetchone()
        plan_row = connection.execute(
            "SELECT plan_id, w_mss, w_irs, w_pas FROM validation_weight_plan WHERE trade_date=?",
            [trade_date],
        ).fetchone()
        integrated_row = connection.execute(
            "SELECT weight_plan_id, w_mss, w_irs, w_pas FROM integrated_recommendation "
            "WHERE trade_date=? LIMIT 1",
            [trade_date],
        ).fetchone()

    assert gate_row is not None
    assert plan_row is not None
    assert integrated_row is not None
    assert str(gate_row[0]) == str(plan_row[0])
    assert str(integrated_row[0]) == str(plan_row[0])
    assert float(integrated_row[1]) == pytest.approx(float(plan_row[1]), abs=1e-6)
    assert float(integrated_row[2]) == pytest.approx(float(plan_row[2]), abs=1e-6)
    assert float(integrated_row[3]) == pytest.approx(float(plan_row[3]), abs=1e-6)


def test_s2c_bridge_blocks_when_selected_plan_missing(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260218"
    _prepare_s2a_inputs(config, trade_date)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE validation_gate_decision SET selected_weight_plan='' WHERE trade_date=?",
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
    assert result.integrated_count == 0
    assert result.quality_gate_status == "FAIL"
    assert result.go_nogo == "NO_GO"
    report_text = result.quality_gate_report_path.read_text(encoding="utf-8")
    assert "selected_weight_plan_missing" in report_text
