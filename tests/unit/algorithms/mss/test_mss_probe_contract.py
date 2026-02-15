from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.algorithms.mss.pipeline import run_mss_scoring
from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.main import main


def _build_config(tmp_path: Path) -> tuple[Config, Path]:
    env_file = tmp_path / ".env.s1b"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file)), env_file


def _prepare_mss_history(config: Config, trade_dates: list[str]) -> None:
    for trade_date in trade_dates:
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
        result = run_mss_scoring(
            trade_date=trade_date,
            config=config,
        )
        assert result.has_error is False


def test_s1b_mss_probe_command_generates_probe_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config, env_file = _build_config(tmp_path)
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
    _prepare_mss_history(config, trade_dates)

    exit_code = main(
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
    assert exit_code == 0

    lines = capsys.readouterr().out.strip().splitlines()
    payload = json.loads(lines[-1])
    assert payload["event"] == "s1b_mss_probe"
    assert payload["status"] == "ok"
    assert "top_bottom_spread_5d" in payload

    report_path = Path(payload["probe_report_path"])
    case_path = Path(payload["consumption_case_path"])
    assert report_path.exists()
    assert case_path.exists()

    report = report_path.read_text(encoding="utf-8")
    assert "top_bottom_spread_5d" in report
    assert "conclusion" in report
