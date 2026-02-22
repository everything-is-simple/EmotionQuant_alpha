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
    env_file = tmp_path / ".env.s2b.quality"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _prepare_s2b_inputs(config: Config, trade_date: str) -> None:
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
        config=config,
    )
    assert s2a.has_error is False


def test_s2b_gate_fail_produces_no_go_and_blocks_recommendation(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"
    _prepare_s2b_inputs(config, trade_date)

    run_validation_gate(
        trade_date=trade_date,
        config=config,
        irs_count=0,
        pas_count=0,
        mss_exists=False,
    )

    result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        config=config,
    )
    assert result.has_error is True
    assert result.integrated_count == 0
    assert result.quality_gate_status == "FAIL"
    assert result.go_nogo == "NO_GO"

    quality_text = result.quality_gate_report_path.read_text(encoding="utf-8")
    go_nogo_text = result.go_nogo_decision_path.read_text(encoding="utf-8")
    assert "- status: FAIL" in quality_text
    assert "- decision: NO_GO" in go_nogo_text

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path), read_only=True) as connection:
        quality_row = connection.execute(
            "SELECT status, go_nogo FROM quality_gate_report WHERE trade_date=? LIMIT 1",
            [trade_date],
        ).fetchone()

    assert quality_row == ("FAIL", "NO_GO")


def test_s2r_repair_emits_patch_and_delta_artifacts(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"
    _prepare_s2b_inputs(config, trade_date)

    result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        repair="s2r",
        config=config,
    )
    assert "spiral-s2r" in str(result.artifacts_dir)
    assert result.s2r_patch_note_path is not None
    assert result.s2r_delta_report_path is not None
    assert result.s2r_patch_note_path.exists()
    assert result.s2r_delta_report_path.exists()
    assert result.quality_gate_report_path.exists()


def test_s2b_warns_and_fallbacks_when_candidate_exec_not_pass(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260212"
    _prepare_s2b_inputs(config, trade_date)

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "UPDATE validation_gate_decision "
            "SET final_gate='PASS', selected_weight_plan='vp_candidate_v1', "
            "candidate_exec_pass=false, tradability_pass_ratio=0.50, impact_cost_bps=60.0 "
            "WHERE trade_date=?",
            [trade_date],
        )

    result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        config=config,
    )
    assert result.has_error is False
    assert result.quality_gate_status == "WARN"
    assert result.go_nogo == "GO"
    quality_text = result.quality_gate_report_path.read_text(encoding="utf-8")
    assert "warn_candidate_exec" in quality_text

