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
