from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import __version__
from src.pipeline.main import build_parser, main
import src.pipeline.main as cli_main_module


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
        artifacts_dir = tmp_path / "artifacts" / "spiral-s3b" / "20260219"
        return SimpleNamespace(
            trade_date="20260219",
            start_date="20260218",
            end_date="20260219",
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
            "20260218",
            "--end",
            "20260219",
            "--ab-benchmark",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s3b_analysis"
    assert payload["status"] == "ok"
    assert payload["quality_status"] == "PASS"


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


def test_main_recommend_runs_s2a_mode(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data_root = tmp_path / "eq_data"
    env_file = tmp_path / ".env.s2a.cli"
    env_file.write_text(
        f"DATA_PATH={data_root}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    trade_date = "20260218"

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
    trade_date = "20260218"

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
    trade_date = "20260218"

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
    trade_dates = ["20260218", "20260219"]

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
    assert payload["total_trades"] > 0


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
        artifacts_dir = tmp_path / "artifacts" / "spiral-s3r" / "20260219"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        patch_note = artifacts_dir / "s3r_patch_note.md"
        delta_report = artifacts_dir / "s3r_delta_report.md"
        patch_note.write_text("# patch\n", encoding="utf-8")
        delta_report.write_text("# delta\n", encoding="utf-8")
        return SimpleNamespace(
            backtest_id="BTR_20260218_20260219_qlib",
            engine="qlib",
            start_date="20260218",
            end_date="20260219",
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
            "20260218",
            "--end",
            "20260219",
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
    trade_dates = ["20260218", "20260219"]

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
