from __future__ import annotations

from pathlib import Path

import duckdb

from src.algorithms.mss.pipeline import run_mss_scoring
from src.algorithms.validation.pipeline import run_validation_gate
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.recommend import run_recommendation


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2a.validation"
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


def test_s2a_recommend_generates_validation_gate_with_nc_v1(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"
    _prepare_s2a_inputs(config, trade_date)

    result = run_recommendation(
        trade_date=trade_date,
        mode="mss_irs_pas",
        with_validation=True,
        config=config,
    )
    assert result.has_error is False
    assert result.validation_count > 0

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT final_gate, contract_version FROM validation_gate_decision WHERE trade_date=?",
            [trade_date],
        ).fetchone()

    assert row is not None
    assert row[1] == "nc-v1"
    assert result.validation_sample_path.exists()


def test_validation_fail_contains_prescription(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    _prepare_s2a_inputs(config, "20260212")
    gate = run_validation_gate(
        trade_date="20260212",
        config=config,
        irs_count=0,
        pas_count=0,
        mss_exists=False,
    )
    assert gate.final_gate == "FAIL"
    prescription = str(gate.frame.iloc[0]["validation_prescription"])
    assert prescription != ""

