from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import src.pipeline.recommend as recommend_module
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
    trade_date = "20260212"
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
            trade_date="20260212",
            mode="integrated",
            with_validation=False,
            with_validation_bridge=True,
            evidence_lane="nightly",
            config=config,
        )


def test_integrated_bridge_validation_defaults_to_s3e_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260213"
    captured: dict[str, object] = {}

    def _fake_run_s2a(**kwargs: object) -> recommend_module.RecommendRunResult:
        captured.update(kwargs)
        artifacts_dir = tmp_path / "artifacts" / "spiral-s2c" / trade_date
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        empty = pd.DataFrame.from_records([])
        sample = artifacts_dir / "sample.parquet"
        empty.to_parquet(sample, index=False)
        gate = artifacts_dir / "quality_gate_report.md"
        gate.write_text("# gate\n", encoding="utf-8")
        nogo = artifacts_dir / "s2_go_nogo_decision.md"
        nogo.write_text("# nogo\n", encoding="utf-8")
        err = artifacts_dir / "error_manifest_sample.json"
        err.write_text("{}", encoding="utf-8")
        return recommend_module.RecommendRunResult(
            trade_date=trade_date,
            mode="mss_irs_pas",
            integration_mode="top_down",
            evidence_lane="release",
            artifacts_dir=artifacts_dir,
            irs_count=31,
            pas_count=5474,
            validation_count=1,
            final_gate="WARN",
            integrated_count=0,
            quality_gate_status="WARN",
            go_nogo="GO",
            has_error=False,
            error_manifest_path=err,
            irs_sample_path=sample,
            pas_sample_path=sample,
            validation_sample_path=sample,
            integrated_sample_path=sample,
            quality_gate_report_path=gate,
            go_nogo_decision_path=nogo,
        )

    def _fake_run_integrated_daily(**kwargs: object):  # type: ignore[no-untyped-def]
        _ = kwargs
        frame = pd.DataFrame.from_records(
            [{"trade_date": trade_date, "stock_code": "000001", "contract_version": "nc-v1"}]
        )
        quality = pd.DataFrame.from_records(
            [{"trade_date": trade_date, "status": "WARN", "go_nogo": "GO"}]
        )
        return type(
            "IntegratedResult",
            (),
            {
                "integration_mode": "top_down",
                "count": 1,
                "validation_gate": "WARN",
                "quality_status": "WARN",
                "go_nogo": "GO",
                "frame": frame,
                "quality_frame": quality,
                "rr_filtered_count": 0,
                "quality_message": "ok",
            },
        )()

    monkeypatch.setattr(recommend_module, "_run_s2a", _fake_run_s2a)
    monkeypatch.setattr(recommend_module, "run_integrated_daily", _fake_run_integrated_daily)
    monkeypatch.setattr(
        recommend_module,
        "_materialize_s2c_bridge_samples",
        lambda **_: (1, []),
    )

    result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=True,
        with_validation_bridge=True,
        config=config,
    )
    assert result.has_error is False
    assert captured["validation_threshold_mode"] == "regime"
    assert captured["validation_wfa_mode"] == "dual-window"
    assert captured["validation_export_run_manifest"] is True


def test_materialize_s2c_bridge_samples_accepts_parquet_only_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trade_date = "20260213"
    parquet_root = tmp_path / "l3"
    artifacts_dir = tmp_path / "artifacts"
    parquet_root.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame.from_records([{"trade_date": trade_date, "stock_code": "000001"}]).to_parquet(
        parquet_root / "mss_factor_intermediate.parquet",
        index=False,
    )
    pd.DataFrame.from_records([{"trade_date": trade_date, "final_gate": "WARN"}]).to_parquet(
        parquet_root / "validation_gate_decision.parquet",
        index=False,
    )

    def _fake_load_trade_date_table(**_: object) -> tuple[pd.DataFrame, bool]:
        return (pd.DataFrame.from_records([]), False)

    monkeypatch.setattr(recommend_module, "_load_trade_date_table", _fake_load_trade_date_table)

    validation_count, violations = recommend_module._materialize_s2c_bridge_samples(
        database_path=tmp_path / "missing.duckdb",
        parquet_root=parquet_root,
        trade_date=trade_date,
        artifacts_dir=artifacts_dir,
    )

    assert validation_count == 1
    assert violations == []
    assert (artifacts_dir / "mss_factor_intermediate_sample.parquet").exists()
    assert (artifacts_dir / "validation_gate_decision_sample.parquet").exists()


def test_integrated_bridge_parquet_only_source_does_not_mark_run_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _build_config(tmp_path)
    trade_date = "20260213"
    parquet_root = Path(config.parquet_path) / "l3"
    parquet_root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame.from_records([{"trade_date": trade_date, "stock_code": "000001"}]).to_parquet(
        parquet_root / "mss_factor_intermediate.parquet",
        index=False,
    )
    pd.DataFrame.from_records([{"trade_date": trade_date, "final_gate": "WARN"}]).to_parquet(
        parquet_root / "validation_gate_decision.parquet",
        index=False,
    )

    def _fake_load_trade_date_table(**_: object) -> tuple[pd.DataFrame, bool]:
        return (pd.DataFrame.from_records([]), False)

    def _fake_run_s2a(**kwargs: object) -> recommend_module.RecommendRunResult:
        _ = kwargs
        artifacts_dir = tmp_path / "artifacts" / "spiral-s2c" / trade_date
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        empty = pd.DataFrame.from_records([])
        sample = artifacts_dir / "sample.parquet"
        empty.to_parquet(sample, index=False)
        gate = artifacts_dir / "quality_gate_report.md"
        gate.write_text("# gate\n", encoding="utf-8")
        nogo = artifacts_dir / "s2_go_nogo_decision.md"
        nogo.write_text("# nogo\n", encoding="utf-8")
        err = artifacts_dir / "error_manifest_sample.json"
        err.write_text("{}", encoding="utf-8")
        return recommend_module.RecommendRunResult(
            trade_date=trade_date,
            mode="mss_irs_pas",
            integration_mode="top_down",
            evidence_lane="release",
            artifacts_dir=artifacts_dir,
            irs_count=31,
            pas_count=5474,
            validation_count=1,
            final_gate="WARN",
            integrated_count=0,
            quality_gate_status="WARN",
            go_nogo="GO",
            has_error=False,
            error_manifest_path=err,
            irs_sample_path=sample,
            pas_sample_path=sample,
            validation_sample_path=sample,
            integrated_sample_path=sample,
            quality_gate_report_path=gate,
            go_nogo_decision_path=nogo,
        )

    def _fake_run_integrated_daily(**kwargs: object):  # type: ignore[no-untyped-def]
        _ = kwargs
        frame = pd.DataFrame.from_records(
            [{"trade_date": trade_date, "stock_code": "000001", "contract_version": "nc-v1"}]
        )
        quality = pd.DataFrame.from_records(
            [{"trade_date": trade_date, "status": "WARN", "go_nogo": "GO"}]
        )
        return type(
            "IntegratedResult",
            (),
            {
                "integration_mode": "top_down",
                "count": 1,
                "validation_gate": "WARN",
                "quality_status": "WARN",
                "go_nogo": "GO",
                "frame": frame,
                "quality_frame": quality,
                "rr_filtered_count": 0,
                "quality_message": "ok",
            },
        )()

    monkeypatch.setattr(recommend_module, "_load_trade_date_table", _fake_load_trade_date_table)
    monkeypatch.setattr(recommend_module, "_run_s2a", _fake_run_s2a)
    monkeypatch.setattr(recommend_module, "run_integrated_daily", _fake_run_integrated_daily)

    result = run_recommendation(
        trade_date=trade_date,
        mode="integrated",
        with_validation=True,
        with_validation_bridge=True,
        config=config,
    )

    assert result.has_error is False

