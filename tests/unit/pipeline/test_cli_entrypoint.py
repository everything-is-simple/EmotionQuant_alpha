from __future__ import annotations

import json
from pathlib import Path

import pytest

from src import __version__
from src.pipeline.main import build_parser, main


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
