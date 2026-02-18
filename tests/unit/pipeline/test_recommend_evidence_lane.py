from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.algorithms.mss.pipeline import run_mss_scoring
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.recommend import run_recommendation


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s2c.lane"
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
    result = run_recommendation(
        trade_date=trade_date,
        mode="mss_irs_pas",
        with_validation=True,
        config=config,
    )
    assert result.has_error is False


def test_s2c_bridge_writes_release_and_debug_lanes_separately(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260218"
    _prepare_s2a_inputs(config, trade_date)

    release_result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        with_validation_bridge=True,
        evidence_lane="release",
        config=config,
    )
    assert release_result.has_error is False
    assert "spiral-s2c" in str(release_result.artifacts_dir)
    assert "spiral-s2c-debug" not in str(release_result.artifacts_dir)
    assert release_result.quality_gate_report_path.exists()
    release_mss_sample = release_result.artifacts_dir / "mss_factor_intermediate_sample.parquet"
    release_validation_sample = (
        release_result.artifacts_dir / "validation_gate_decision_sample.parquet"
    )
    assert release_mss_sample.exists()
    assert release_validation_sample.exists()
    assert len(pd.read_parquet(release_mss_sample)) > 0
    assert len(pd.read_parquet(release_validation_sample)) > 0

    debug_result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=False,
        with_validation_bridge=True,
        evidence_lane="debug",
        config=config,
    )
    assert debug_result.has_error is False
    assert "spiral-s2c-debug" in str(debug_result.artifacts_dir)
    assert debug_result.quality_gate_report_path.exists()
    debug_mss_sample = debug_result.artifacts_dir / "mss_factor_intermediate_sample.parquet"
    debug_validation_sample = debug_result.artifacts_dir / "validation_gate_decision_sample.parquet"
    assert debug_mss_sample.exists()
    assert debug_validation_sample.exists()
    assert len(pd.read_parquet(debug_mss_sample)) > 0
    assert len(pd.read_parquet(debug_validation_sample)) > 0

    assert release_result.artifacts_dir != debug_result.artifacts_dir
    assert (release_result.artifacts_dir / "quality_gate_report.md").exists()
    assert (debug_result.artifacts_dir / "quality_gate_report.md").exists()


def test_recommend_rejects_unknown_evidence_lane(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    with pytest.raises(ValueError, match="unsupported evidence_lane"):
        run_recommendation(
            trade_date="20260218",
            mode="integrated",
            with_validation=False,
            with_validation_bridge=True,
            evidence_lane="nightly",
            config=config,
        )
