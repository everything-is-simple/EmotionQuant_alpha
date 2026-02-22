from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from src import __version__
from src.pipeline.main import build_parser, main
import src.pipeline.main as cli_main_module
from tests.unit.trade_day_guard import assert_all_valid_trade_days, latest_open_trade_days


def test_build_parser_uses_eq_as_program_name() -> None:
    parser = build_parser()
    assert parser.prog == "eq"


def test_main_help_exits_with_zero() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


def test_main_run_dry_run_prints_config_snapshot(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data_root = tmp_path / "eq_data"
    env_file = tmp_path / ".env.s0a"
    env_file.write_text(
        f"DATA_PATH={data_root}\n"
        "ENVIRONMENT=test\n"
        "TUSHARE_RATE_LIMIT_PER_MIN=88\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--env-file",
            str(env_file),
            "--print-config",
            "run",
            "--date",
            "20260215",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 3

    config_snapshot = json.loads(lines[0])
    assert config_snapshot["environment"] == "test"
    assert config_snapshot["data_path"] == str(data_root)
    assert config_snapshot["tushare_rate_limit_per_min"] == 88

    event = json.loads(lines[1])
    assert event["event"] == "pipeline_start"
    assert event["trade_date"] == "20260215"
    assert event["dry_run"] is True

    assert "dry-run completed" in lines[2]


def test_main_version_prints_project_version(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["version"])
    assert exit_code == 0
    assert capsys.readouterr().out.strip() == __version__


def test_main_accepts_env_file_none(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DATA_PATH", str(Path.cwd() / "tmp_data"))
    exit_code = main(["--env-file", "none", "run", "--date", "20260215", "--dry-run"])
    assert exit_code == 0
    assert "dry-run completed" in capsys.readouterr().out


def test_main_analysis_command_wires_to_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / ".env.s3b.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )

    def _fake_run_analysis(**_: object) -> SimpleNamespace:
        artifacts_dir = tmp_path / "artifacts" / "spiral-s3b" / "20260213"
        return SimpleNamespace(
            trade_date="20260213",
            start_date="20260212",
            end_date="20260213",
            artifacts_dir=artifacts_dir,
            ab_benchmark_report_path=artifacts_dir / "ab_benchmark_report.md",
            live_backtest_deviation_report_path=artifacts_dir / "live_backtest_deviation_report.md",
            attribution_summary_path=artifacts_dir / "attribution_summary.json",
            consumption_path=artifacts_dir / "consumption.md",
            gate_report_path=artifacts_dir / "gate_report.md",
            error_manifest_path=artifacts_dir / "error_manifest.json",
            quality_status="PASS",
            go_nogo="GO",
            has_error=False,
        )

    monkeypatch.setattr(cli_main_module, "run_analysis", _fake_run_analysis)
    exit_code = main(
        [
            "--env-file",
            str(env_file),
            "analysis",
            "--start",
            "20260212",
            "--end",
            "20260213",
            "--ab-benchmark",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s3b_analysis"
    assert payload["status"] == "ok"
    assert payload["quality_status"] == "PASS"


def test_main_validation_command_wires_to_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / ".env.s3e.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )

    def _fake_resolve_inputs(*_: object, **__: object) -> tuple[int, int, bool]:
        return (31, 31, True)

    def _fake_run_validation_gate(**_: object) -> SimpleNamespace:
        artifacts_dir = tmp_path / "artifacts" / "spiral-s3e" / "20260213"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        factor_report = artifacts_dir / "validation_factor_report_sample.parquet"
        weight_report = artifacts_dir / "validation_weight_report_sample.parquet"
        plan_report = artifacts_dir / "validation_weight_plan_sample.parquet"
        manifest = artifacts_dir / "validation_run_manifest_sample.json"
        oos_report = artifacts_dir / "validation_oos_calibration_report.md"
        factor_report.write_text("factor", encoding="utf-8")
        weight_report.write_text("weight", encoding="utf-8")
        plan_report.write_text("plan", encoding="utf-8")
        manifest.write_text("{}", encoding="utf-8")
        oos_report.write_text("# oos\n", encoding="utf-8")
        return SimpleNamespace(
            trade_date="20260213",
            count=1,
            frame=pd.DataFrame.from_records([{"trade_date": "20260213", "final_gate": "PASS"}]),
            final_gate="PASS",
            selected_weight_plan="vp_balanced_v1",
            has_fail=False,
            factor_report_frame=pd.DataFrame.from_records([{"factor_name": "mss_future_returns_alignment"}]),
            weight_report_frame=pd.DataFrame.from_records([{"plan_id": "vp_balanced_v1"}]),
            weight_plan_frame=pd.DataFrame.from_records([{"plan_id": "vp_balanced_v1"}]),
            run_manifest_payload={"trade_date": "20260213"},
            threshold_mode="regime",
            wfa_mode="dual-window",
            factor_report_sample_path=factor_report,
            weight_report_sample_path=weight_report,
            weight_plan_sample_path=plan_report,
            run_manifest_sample_path=manifest,
            oos_calibration_report_path=oos_report,
        )

    monkeypatch.setattr(cli_main_module, "_resolve_validation_inputs", _fake_resolve_inputs)
    monkeypatch.setattr(cli_main_module, "run_validation_gate", _fake_run_validation_gate)
    exit_code = main(
        [
            "--env-file",
            str(env_file),
            "validation",
            "--trade-date",
            "20260213",
            "--threshold-mode",
            "regime",
            "--wfa",
            "dual-window",
            "--export-run-manifest",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s3e_validation"
    assert payload["status"] == "ok"
    assert payload["threshold_mode"] == "regime"
    assert payload["wfa_mode"] == "dual-window"


def test_main_irs_command_wires_to_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / ".env.s3c.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )

    def _fake_run_irs_daily(**_: object) -> SimpleNamespace:
        artifacts_dir = tmp_path / "artifacts" / "spiral-s3c" / "20260213"
        return SimpleNamespace(
            trade_date="20260213",
            count=31,
            factor_intermediate_sample_path=artifacts_dir / "irs_factor_intermediate_sample.parquet",
            coverage_report_path=artifacts_dir / "irs_allocation_coverage_report.md",
        )

    monkeypatch.setattr(cli_main_module, "run_irs_daily", _fake_run_irs_daily)
    exit_code = main(
        [
            "--env-file",
            str(env_file),
            "irs",
            "--date",
            "20260213",
            "--require-sw31",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s3c_irs"
    assert payload["require_sw31"] is True
    assert payload["irs_industry_count"] == 31
    assert payload["gate_status"] == "PASS"
    assert payload["go_nogo"] == "GO"
    assert Path(payload["gate_report_path"]).exists()
    assert Path(payload["consumption_path"]).exists()
    assert payload["status"] == "ok"


def test_main_pas_command_wires_to_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / ".env.s2b.pas.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )

    def _fake_run_pas_daily(**_: object) -> SimpleNamespace:
        artifacts_dir = tmp_path / "artifacts" / "spiral-s2c" / "20260213"
        return SimpleNamespace(
            trade_date="20260213",
            count=123,
            factor_intermediate_sample_path=artifacts_dir / "pas_factor_intermediate_sample.parquet",
        )

    monkeypatch.setattr(cli_main_module, "run_pas_daily", _fake_run_pas_daily)
    exit_code = main(
        [
            "--env-file",
            str(env_file),
            "pas",
            "--date",
            "20260213",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s2b_pas"
    assert payload["pas_stock_count"] == 123
    assert payload["status"] == "ok"


def test_main_mss_runs_after_l1_and_l2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data_root = tmp_path / "eq_data"
    env_file = tmp_path / ".env.s1a.cli"
    env_file.write_text(
        f"DATA_PATH={data_root}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )

    run_exit_code = main(
        [
            "--env-file",
            str(env_file),
            "run",
            "--date",
            "20260215",
            "--source",
            "tushare",
            "--l1-only",
        ]
    )
    assert run_exit_code == 0

    to_l2_exit_code = main(
        [
            "--env-file",
            str(env_file),
            "run",
            "--date",
            "20260215",
            "--source",
            "tushare",
            "--to-l2",
        ]
    )
    assert to_l2_exit_code == 0

    mss_exit_code = main(["--env-file", str(env_file), "mss", "--date", "20260215"])
    assert mss_exit_code == 0

    lines = capsys.readouterr().out.strip().splitlines()
    payload = json.loads(lines[-1])
    assert payload["event"] == "s1a_mss"
    assert payload["status"] == "ok"
    assert payload["mss_panorama_count"] > 0


def test_main_mss_supports_s3d_threshold_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / ".env.s3d.mss.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )

    def _fake_run_mss_scoring(**_: object) -> SimpleNamespace:
        artifacts_dir = tmp_path / "artifacts" / "spiral-s3d" / "20260212"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        threshold_snapshot = artifacts_dir / "mss_regime_thresholds_snapshot.json"
        adaptive_report = artifacts_dir / "mss_adaptive_regression.md"
        gate_report = artifacts_dir / "gate_report.md"
        consumption = artifacts_dir / "consumption.md"
        sample_path = artifacts_dir / "mss_panorama_sample.parquet"
        factor_trace = artifacts_dir / "mss_factor_trace.md"
        factor_intermediate = artifacts_dir / "mss_factor_intermediate_sample.parquet"
        threshold_snapshot.write_text("{}", encoding="utf-8")
        adaptive_report.write_text("# report\n", encoding="utf-8")
        gate_report.write_text("# gate\n", encoding="utf-8")
        consumption.write_text("# consumption\n", encoding="utf-8")
        sample_path.write_text("sample", encoding="utf-8")
        factor_trace.write_text("# trace\n", encoding="utf-8")
        factor_intermediate.write_text("sample", encoding="utf-8")
        return SimpleNamespace(
            trade_date="20260212",
            artifacts_dir=artifacts_dir,
            mss_panorama_count=1,
            threshold_mode="adaptive",
            has_error=False,
            error_manifest_path=artifacts_dir / "error_manifest_sample.json",
            factor_trace_path=factor_trace,
            sample_path=sample_path,
            factor_intermediate_sample_path=factor_intermediate,
            threshold_snapshot_path=threshold_snapshot,
            adaptive_regression_path=adaptive_report,
            gate_report_path=gate_report,
            consumption_path=consumption,
        )

    monkeypatch.setattr(cli_main_module, "run_mss_scoring", _fake_run_mss_scoring)
    exit_code = main(
        [
            "--env-file",
            str(env_file),
            "mss",
            "--date",
            "20260212",
            "--threshold-mode",
            "adaptive",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s3d_mss"
    assert payload["threshold_mode"] == "adaptive"
    assert "spiral-s3d" in payload["artifacts_dir"]


def test_main_mss_probe_runs_with_window(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data_root = tmp_path / "eq_data"
    env_file = tmp_path / ".env.s1b.cli"
    env_file.write_text(
        f"DATA_PATH={data_root}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    trade_dates = [
        "20260210",
        "20260211",
        "20260212",
        "20260213",
        "20260214",
        "20260215",
        "20260216",
        "20260217",
    ]
    for trade_date in trade_dates:
        assert main(
            [
                "--env-file",
                str(env_file),
                "run",
                "--date",
                trade_date,
                "--source",
                "tushare",
                "--l1-only",
            ]
        ) == 0
        assert main(
            [
                "--env-file",
                str(env_file),
                "run",
                "--date",
                trade_date,
                "--source",
                "tushare",
                "--to-l2",
            ]
        ) == 0
        assert main(
            [
                "--env-file",
                str(env_file),
                "mss",
                "--date",
                trade_date,
            ]
        ) == 0

    probe_exit_code = main(
        [
            "--env-file",
            str(env_file),
            "mss-probe",
            "--start",
            trade_dates[0],
            "--end",
            trade_dates[-1],
        ]
    )
    assert probe_exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s1b_mss_probe"
    assert payload["status"] == "ok"
    assert "top_bottom_spread_5d" in payload


def test_main_mss_probe_supports_future_returns_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / ".env.s3d.probe.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )

    def _fake_run_mss_probe(**_: object) -> SimpleNamespace:
        artifacts_dir = tmp_path / "artifacts" / "spiral-s3d" / "20260210_20260213"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        probe_report = artifacts_dir / "mss_probe_return_series_report.md"
        consumption = artifacts_dir / "consumption.md"
        gate_report = artifacts_dir / "gate_report.md"
        probe_report.write_text("# probe\n", encoding="utf-8")
        consumption.write_text("# consumption\n", encoding="utf-8")
        gate_report.write_text("# gate\n", encoding="utf-8")
        return SimpleNamespace(
            start_date="20260210",
            end_date="20260213",
            artifacts_dir=artifacts_dir,
            return_series_source="future_returns",
            has_error=False,
            error_manifest_path=artifacts_dir / "error_manifest_sample.json",
            probe_report_path=probe_report,
            consumption_case_path=consumption,
            gate_report_path=gate_report,
            top_bottom_spread_5d=0.01,
            conclusion="PASS_POSITIVE_SPREAD",
        )

    monkeypatch.setattr(cli_main_module, "run_mss_probe", _fake_run_mss_probe)
    exit_code = main(
        [
            "--env-file",
            str(env_file),
            "mss-probe",
            "--start",
            "20260210",
            "--end",
            "20260213",
            "--return-series-source",
            "future_returns",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s3d_mss_probe"
    assert payload["return_series_source"] == "future_returns"
    assert "spiral-s3d" in payload["artifacts_dir"]


def test_main_recommend_runs_s2a_mode(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data_root = tmp_path / "eq_data"
    env_file = tmp_path / ".env.s2a.cli"
    env_file.write_text(
        f"DATA_PATH={data_root}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    trade_date = "20260212"

    assert main(
        [
            "--env-file",
            str(env_file),
            "run",
            "--date",
            trade_date,
            "--source",
            "tushare",
            "--l1-only",
        ]
    ) == 0
    assert main(
        [
            "--env-file",
            str(env_file),
            "run",
            "--date",
            trade_date,
            "--source",
            "tushare",
            "--to-l2",
        ]
    ) == 0
    assert main(
        [
            "--env-file",
            str(env_file),
            "mss",
            "--date",
            trade_date,
        ]
    ) == 0

    recommend_exit = main(
        [
            "--env-file",
            str(env_file),
            "recommend",
            "--date",
            trade_date,
            "--mode",
            "mss_irs_pas",
            "--with-validation",
        ]
    )
    assert recommend_exit == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s2a_recommend"
    assert payload["mode"] == "mss_irs_pas"
    assert payload["status"] == "ok"


def test_main_validation_runs_s3e_mode(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data_root = tmp_path / "eq_data"
    env_file = tmp_path / ".env.s3e.real.cli"
    env_file.write_text(
        f"DATA_PATH={data_root}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    trade_date = "20260212"

    assert main(
        [
            "--env-file",
            str(env_file),
            "run",
            "--date",
            trade_date,
            "--source",
            "tushare",
            "--l1-only",
        ]
    ) == 0
    assert main(
        [
            "--env-file",
            str(env_file),
            "run",
            "--date",
            trade_date,
            "--source",
            "tushare",
            "--to-l2",
        ]
    ) == 0
    assert main(
        [
            "--env-file",
            str(env_file),
            "mss",
            "--date",
            trade_date,
            "--threshold-mode",
            "adaptive",
        ]
    ) == 0
    assert main(
        [
            "--env-file",
            str(env_file),
            "recommend",
            "--date",
            trade_date,
            "--mode",
            "mss_irs_pas",
            "--with-validation",
        ]
    ) == 0

    validation_exit = main(
        [
            "--env-file",
            str(env_file),
            "validation",
            "--trade-date",
            trade_date,
            "--threshold-mode",
            "regime",
            "--wfa",
            "dual-window",
            "--export-run-manifest",
        ]
    )
    assert validation_exit == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s3e_validation"
    assert payload["status"] == "ok"
    assert payload["threshold_mode"] == "regime"
    assert payload["wfa_mode"] == "dual-window"
    assert Path(payload["run_manifest_sample_path"]).exists()
    assert Path(payload["oos_calibration_report_path"]).exists()


def test_main_recommend_runs_s2b_integrated_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data_root = tmp_path / "eq_data"
    env_file = tmp_path / ".env.s2b.cli"
    env_file.write_text(
        f"DATA_PATH={data_root}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    trade_date = "20260212"

    assert main(
        [
            "--env-file",
            str(env_file),
            "run",
            "--date",
            trade_date,
            "--source",
            "tushare",
            "--l1-only",
        ]
    ) == 0
    assert main(
        [
            "--env-file",
            str(env_file),
            "run",
            "--date",
            trade_date,
            "--source",
            "tushare",
            "--to-l2",
        ]
    ) == 0
    assert main(
        [
            "--env-file",
            str(env_file),
            "mss",
            "--date",
            trade_date,
        ]
    ) == 0
    assert main(
        [
            "--env-file",
            str(env_file),
            "recommend",
            "--date",
            trade_date,
            "--mode",
            "mss_irs_pas",
            "--with-validation",
        ]
    ) == 0

    recommend_exit = main(
        [
            "--env-file",
            str(env_file),
            "recommend",
            "--date",
            trade_date,
            "--mode",
            "integrated",
        ]
    )
    assert recommend_exit == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s2b_recommend"
    assert payload["mode"] == "integrated"
    assert payload["integration_mode"] == "top_down"
    assert payload["status"] == "ok"
    assert payload["quality_gate_status"] in {"PASS", "WARN"}
    assert payload["integrated_count"] > 0

    recommend_exit_bu = main(
        [
            "--env-file",
            str(env_file),
            "recommend",
            "--date",
            trade_date,
            "--mode",
            "integrated",
            "--integration-mode",
            "bottom_up",
        ]
    )
    assert recommend_exit_bu == 0
    payload_bu = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload_bu["event"] == "s2b_recommend"
    assert payload_bu["integration_mode"] == "bottom_up"


def test_main_recommend_forwards_validation_mode_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / ".env.s2b.validation.flags.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def _fake_run_recommendation(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        artifacts_dir = tmp_path / "artifacts" / "spiral-s2c" / "20260213"
        return SimpleNamespace(
            trade_date="20260213",
            mode="integrated",
            integration_mode="dual_verify",
            evidence_lane="release",
            artifacts_dir=artifacts_dir,
            irs_count=31,
            pas_count=5474,
            validation_count=1,
            final_gate="WARN",
            integrated_count=10,
            quality_gate_status="WARN",
            go_nogo="GO",
            has_error=False,
            error_manifest_path=artifacts_dir / "error_manifest_sample.json",
            irs_sample_path=artifacts_dir / "irs_industry_daily_sample.parquet",
            pas_sample_path=artifacts_dir / "stock_pas_daily_sample.parquet",
            validation_sample_path=artifacts_dir / "validation_gate_decision_sample.parquet",
            integrated_sample_path=artifacts_dir / "integrated_recommendation_sample.parquet",
            quality_gate_report_path=artifacts_dir / "quality_gate_report.md",
            go_nogo_decision_path=artifacts_dir / "s2_go_nogo_decision.md",
            s2r_patch_note_path=None,
            s2r_delta_report_path=None,
        )

    monkeypatch.setattr(cli_main_module, "run_recommendation", _fake_run_recommendation)
    exit_code = main(
        [
            "--env-file",
            str(env_file),
            "recommend",
            "--date",
            "20260213",
            "--mode",
            "integrated",
            "--with-validation",
            "--with-validation-bridge",
            "--integration-mode",
            "dual_verify",
            "--evidence-lane",
            "release",
            "--validation-threshold-mode",
            "regime",
            "--validation-wfa",
            "dual-window",
            "--validation-export-run-manifest",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s2b_recommend"
    assert captured["validation_threshold_mode"] == "regime"
    assert captured["validation_wfa_mode"] == "dual-window"
    assert captured["validation_export_run_manifest"] is True


def test_main_recommend_runs_s2r_repair_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data_root = tmp_path / "eq_data"
    env_file = tmp_path / ".env.s2r.cli"
    env_file.write_text(
        f"DATA_PATH={data_root}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    trade_date = "20260212"

    assert main(
        [
            "--env-file",
            str(env_file),
            "run",
            "--date",
            trade_date,
            "--source",
            "tushare",
            "--l1-only",
        ]
    ) == 0
    assert main(
        [
            "--env-file",
            str(env_file),
            "run",
            "--date",
            trade_date,
            "--source",
            "tushare",
            "--to-l2",
        ]
    ) == 0
    assert main(
        [
            "--env-file",
            str(env_file),
            "mss",
            "--date",
            trade_date,
        ]
    ) == 0
    assert main(
        [
            "--env-file",
            str(env_file),
            "recommend",
            "--date",
            trade_date,
            "--mode",
            "mss_irs_pas",
            "--with-validation",
        ]
    ) == 0

    repair_exit = main(
        [
            "--env-file",
            str(env_file),
            "recommend",
            "--date",
            trade_date,
            "--mode",
            "integrated",
            "--repair",
            "s2r",
        ]
    )
    assert repair_exit in {0, 1}
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s2r_recommend"
    assert payload["repair"] == "s2r"
    assert payload["integration_mode"] == "top_down"
    assert "spiral-s2r" in payload["artifacts_dir"]
    assert Path(payload["s2r_patch_note_path"]).exists()
    assert Path(payload["s2r_delta_report_path"]).exists()


def test_main_fetch_batch_status_and_retry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / ".env.s3a.cli"
    env_file.write_text(
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )

    fetch_exit = main(
        [
            "--env-file",
            str(env_file),
            "fetch-batch",
            "--start",
            "20260101",
            "--end",
            "20260105",
            "--batch-size",
            "2",
            "--workers",
            "3",
        ]
    )
    assert fetch_exit == 0
    fetch_payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert fetch_payload["event"] == "s3a_fetch_batch"
    assert fetch_payload["status"] == "completed"
    assert fetch_payload["failed_batches"] == 0

    status_exit = main(["--env-file", str(env_file), "fetch-status"])
    assert status_exit == 0
    status_payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert status_payload["event"] == "s3a_fetch_status"
    assert status_payload["status"] == "completed"
    assert status_payload["completed_batches"] == status_payload["total_batches"]

    retry_exit = main(["--env-file", str(env_file), "fetch-retry"])
    assert retry_exit == 0
    retry_payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert retry_payload["event"] == "s3a_fetch_retry"
    assert retry_payload["retried_batches"] == 0
    assert retry_payload["status"] == "completed"


def test_main_backtest_runs_with_s3a_consumption(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / ".env.s3.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    trade_dates = latest_open_trade_days(2)
    assert_all_valid_trade_days(trade_dates, context="cli_backtest_e2e")

    assert main(
        [
            "--env-file",
            str(env_file),
            "fetch-batch",
            "--start",
            trade_dates[0],
            "--end",
            trade_dates[-1],
            "--batch-size",
            "365",
            "--workers",
            "3",
        ]
    ) == 0
    for trade_date in trade_dates:
        assert main(
            [
                "--env-file",
                str(env_file),
                "run",
                "--date",
                trade_date,
                "--source",
                "tushare",
                "--l1-only",
            ]
        ) == 0
        assert main(
            [
                "--env-file",
                str(env_file),
                "run",
                "--date",
                trade_date,
                "--source",
                "tushare",
                "--to-l2",
            ]
        ) == 0
        assert main(
            [
                "--env-file",
                str(env_file),
                "mss",
                "--date",
                trade_date,
            ]
        ) == 0
        assert main(
            [
                "--env-file",
                str(env_file),
                "recommend",
                "--date",
                trade_date,
                "--mode",
                "mss_irs_pas",
                "--with-validation",
            ]
        ) == 0
        assert main(
            [
                "--env-file",
                str(env_file),
                "recommend",
                "--date",
                trade_date,
                "--mode",
                "integrated",
                "--with-validation-bridge",
            ]
        ) == 0

    backtest_exit = main(
        [
            "--env-file",
            str(env_file),
            "backtest",
            "--engine",
            "qlib",
            "--start",
            trade_dates[0],
            "--end",
            trade_dates[-1],
        ]
    )
    assert backtest_exit == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s3_backtest"
    assert payload["quality_status"] in {"PASS", "WARN"}
    assert payload["go_nogo"] == "GO"
    assert payload["bridge_check_status"] == "PASS"
    assert payload["total_trades"] >= 0
    gate_report_path = Path(payload["gate_report_path"])
    assert gate_report_path.exists()
    if payload["total_trades"] == 0:
        gate_text = gate_report_path.read_text(encoding="utf-8")
        assert "no_long_entry_signal_in_window" in gate_text


def test_main_backtest_runs_s3r_repair_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / ".env.s3r.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )

    def _fake_run_backtest(**_: object) -> SimpleNamespace:
        artifacts_dir = tmp_path / "artifacts" / "spiral-s3r" / "20260213"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        patch_note = artifacts_dir / "s3r_patch_note.md"
        delta_report = artifacts_dir / "s3r_delta_report.md"
        patch_note.write_text("# patch\n", encoding="utf-8")
        delta_report.write_text("# delta\n", encoding="utf-8")
        return SimpleNamespace(
            backtest_id="BTR_20260212_20260213_qlib",
            engine="qlib",
            start_date="20260212",
            end_date="20260213",
            repair="s3r",
            consumed_signal_rows=10,
            total_trades=3,
            quality_status="WARN",
            go_nogo="GO",
            bridge_check_status="PASS",
            artifacts_dir=artifacts_dir,
            backtest_results_path=artifacts_dir / "backtest_results.parquet",
            backtest_trade_records_path=artifacts_dir / "backtest_trade_records.parquet",
            ab_metric_summary_path=artifacts_dir / "ab_metric_summary.md",
            gate_report_path=artifacts_dir / "gate_report.md",
            consumption_path=artifacts_dir / "consumption.md",
            error_manifest_path=artifacts_dir / "error_manifest_sample.json",
            s3r_patch_note_path=patch_note,
            s3r_delta_report_path=delta_report,
            has_error=False,
        )

    monkeypatch.setattr(cli_main_module, "run_backtest", _fake_run_backtest)
    exit_code = main(
        [
            "--env-file",
            str(env_file),
            "backtest",
            "--engine",
            "qlib",
            "--start",
            "20260212",
            "--end",
            "20260213",
            "--repair",
            "s3r",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s3r_backtest"
    assert payload["repair"] == "s3r"
    assert "spiral-s3r" in payload["artifacts_dir"]
    assert Path(payload["s3r_patch_note_path"]).exists()
    assert Path(payload["s3r_delta_report_path"]).exists()


def test_main_backtest_warn_go_with_zero_trades_is_valid_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / ".env.s3.warn0.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )

    def _fake_run_backtest(**_: object) -> SimpleNamespace:
        artifacts_dir = tmp_path / "artifacts" / "spiral-s3" / "20260213"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        gate_report = artifacts_dir / "gate_report.md"
        gate_report.write_text(
            "# gate\n- warnings: no_long_entry_signal_in_window\n",
            encoding="utf-8",
        )
        return SimpleNamespace(
            backtest_id="BT_20260212_20260213_qlib",
            engine="qlib",
            start_date="20260212",
            end_date="20260213",
            repair="",
            consumed_signal_rows=12,
            total_trades=0,
            quality_status="WARN",
            go_nogo="GO",
            bridge_check_status="PASS",
            artifacts_dir=artifacts_dir,
            backtest_results_path=artifacts_dir / "backtest_results.parquet",
            backtest_trade_records_path=artifacts_dir / "backtest_trade_records.parquet",
            ab_metric_summary_path=artifacts_dir / "ab_metric_summary.md",
            gate_report_path=gate_report,
            consumption_path=artifacts_dir / "consumption.md",
            error_manifest_path=artifacts_dir / "error_manifest_sample.json",
            s3r_patch_note_path=None,
            s3r_delta_report_path=None,
            has_error=False,
        )

    monkeypatch.setattr(cli_main_module, "run_backtest", _fake_run_backtest)
    exit_code = main(
        [
            "--env-file",
            str(env_file),
            "backtest",
            "--engine",
            "qlib",
            "--start",
            "20260212",
            "--end",
            "20260213",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s3_backtest"
    assert payload["quality_status"] == "WARN"
    assert payload["go_nogo"] == "GO"
    assert payload["total_trades"] == 0
    assert payload["bridge_check_status"] == "PASS"
    assert payload["repair"] == ""
    assert "s3r_patch_note_path" not in payload
    assert "s3r_delta_report_path" not in payload


def test_main_trade_runs_paper_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / ".env.s4.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    trade_dates = latest_open_trade_days(2)
    assert_all_valid_trade_days(trade_dates, context="cli_trade_e2e")

    assert main(
        [
            "--env-file",
            str(env_file),
            "fetch-batch",
            "--start",
            trade_dates[0],
            "--end",
            trade_dates[-1],
            "--batch-size",
            "365",
            "--workers",
            "3",
        ]
    ) == 0

    for trade_date in trade_dates:
        assert main(
            [
                "--env-file",
                str(env_file),
                "run",
                "--date",
                trade_date,
                "--source",
                "tushare",
                "--l1-only",
            ]
        ) == 0
        assert main(
            [
                "--env-file",
                str(env_file),
                "run",
                "--date",
                trade_date,
                "--source",
                "tushare",
                "--to-l2",
            ]
        ) == 0
        assert main(
            [
                "--env-file",
                str(env_file),
                "mss",
                "--date",
                trade_date,
            ]
        ) == 0
        assert main(
            [
                "--env-file",
                str(env_file),
                "recommend",
                "--date",
                trade_date,
                "--mode",
                "mss_irs_pas",
                "--with-validation",
            ]
        ) == 0
        assert main(
            [
                "--env-file",
                str(env_file),
                "recommend",
                "--date",
                trade_date,
                "--mode",
                "integrated",
                "--with-validation-bridge",
            ]
        ) == 0

    assert main(
        [
            "--env-file",
            str(env_file),
            "backtest",
            "--engine",
            "qlib",
            "--start",
            trade_dates[0],
            "--end",
            trade_dates[-1],
        ]
    ) == 0

    trade_exit = main(
        [
            "--env-file",
            str(env_file),
            "trade",
            "--mode",
            "paper",
            "--date",
            trade_dates[-1],
        ]
    )
    assert trade_exit == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s4_trade"
    assert payload["mode"] == "paper"
    assert payload["quality_status"] in {"PASS", "WARN"}
    assert payload["go_nogo"] == "GO"
    assert payload["filled_orders"] > 0

