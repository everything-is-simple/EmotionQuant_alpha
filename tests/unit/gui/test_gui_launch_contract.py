from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.pipeline.main as cli_main_module
from src.pipeline.main import main


def test_main_gui_command_wires_to_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / ".env.s5.gui.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )

    def _fake_run_gui(**_: object) -> SimpleNamespace:
        artifacts_dir = tmp_path / "artifacts" / "spiral-s5" / "20260213"
        return SimpleNamespace(
            trade_date="20260213",
            export_mode="",
            artifacts_dir=artifacts_dir,
            daily_report_path=None,
            gui_export_manifest_path=None,
            gate_report_path=None,
            consumption_path=None,
            quality_status="PASS",
            go_nogo="GO",
            has_error=False,
        )

    monkeypatch.setattr(cli_main_module, "run_gui", _fake_run_gui)
    exit_code = main(
        [
            "--env-file",
            str(env_file),
            "gui",
            "--date",
            "20260213",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s5_gui"
    assert payload["trade_date"] == "20260213"
    assert payload["export_mode"] == ""
    assert payload["status"] == "ok"


def test_main_gui_daily_report_export_wires_to_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / ".env.s5.gui.export.cli"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )

    def _fake_run_gui(**_: object) -> SimpleNamespace:
        artifacts_dir = tmp_path / "artifacts" / "spiral-s5" / "20260213"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        daily_report = artifacts_dir / "daily_report_sample.md"
        manifest = artifacts_dir / "gui_export_manifest.json"
        gate_report = artifacts_dir / "gate_report.md"
        consumption = artifacts_dir / "consumption.md"
        daily_report.write_text("# report\n", encoding="utf-8")
        manifest.write_text("{}", encoding="utf-8")
        gate_report.write_text("# gate\n", encoding="utf-8")
        consumption.write_text("# consumption\n", encoding="utf-8")
        return SimpleNamespace(
            trade_date="20260213",
            export_mode="daily-report",
            artifacts_dir=artifacts_dir,
            daily_report_path=daily_report,
            gui_export_manifest_path=manifest,
            gate_report_path=gate_report,
            consumption_path=consumption,
            quality_status="PASS",
            go_nogo="GO",
            has_error=False,
        )

    monkeypatch.setattr(cli_main_module, "run_gui", _fake_run_gui)
    exit_code = main(
        [
            "--env-file",
            str(env_file),
            "gui",
            "--date",
            "20260213",
            "--export",
            "daily-report",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["event"] == "s5_gui"
    assert payload["export_mode"] == "daily-report"
    assert Path(payload["daily_report_path"]).exists()
    assert Path(payload["gui_export_manifest_path"]).exists()
    assert Path(payload["gate_report_path"]).exists()
    assert Path(payload["consumption_path"]).exists()
