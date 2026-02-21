from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from src.algorithms.irs.pipeline import run_irs_daily
from src.algorithms.mss.pipeline import run_mss_scoring
from src.algorithms.pas.pipeline import run_pas_daily
from src.algorithms.validation.pipeline import run_validation_gate
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2c.validation"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_inputs(config: Config, trade_date: str) -> tuple[int, int]:
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
    irs_result = run_irs_daily(trade_date=trade_date, config=config)
    pas_result = run_pas_daily(trade_date=trade_date, config=config)
    return (irs_result.count, pas_result.count)


def test_validation_gate_persists_selected_weight_plan_and_plan_row(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260218"
    irs_count, pas_count = _prepare_inputs(config, trade_date)

    gate = run_validation_gate(
        trade_date=trade_date,
        config=config,
        irs_count=irs_count,
        pas_count=pas_count,
        mss_exists=True,
    )
    assert gate.final_gate in {"PASS", "WARN"}
    assert gate.selected_weight_plan != ""

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        gate_row = connection.execute(
            "SELECT final_gate, selected_weight_plan, contract_version "
            "FROM validation_gate_decision WHERE trade_date=?",
            [trade_date],
        ).fetchone()
        plan_row = connection.execute(
            "SELECT plan_id, w_mss, w_irs, w_pas, contract_version "
            "FROM validation_weight_plan WHERE trade_date=?",
            [trade_date],
        ).fetchone()

    assert gate_row is not None
    assert gate_row[0] in {"PASS", "WARN"}
    assert gate_row[2] == "nc-v1"
    assert gate_row[1] != ""

    assert plan_row is not None
    assert plan_row[0] == gate_row[1]
    assert plan_row[4] == "nc-v1"
    weight_sum = float(plan_row[1]) + float(plan_row[2]) + float(plan_row[3])
    assert float(plan_row[1]) > 0.0
    assert float(plan_row[2]) > 0.0
    assert float(plan_row[3]) > 0.0
    assert weight_sum == pytest.approx(1.0, abs=0.05)


def test_validation_fail_keeps_prescription_and_no_selected_plan(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260218"
    _prepare_inputs(config, trade_date)

    gate = run_validation_gate(
        trade_date=trade_date,
        config=config,
        irs_count=0,
        pas_count=0,
        mss_exists=False,
    )
    assert gate.final_gate == "FAIL"
    assert gate.selected_weight_plan == ""
    prescription = str(gate.frame.iloc[0]["validation_prescription"])
    assert prescription != ""
