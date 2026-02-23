from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.config.config import Config
from src.gui.app import run_gui
import src.gui.app as gui_app


def _build_test_config(tmp_path: Path, *, streamlit_port: int = 8501) -> Config:
    env_file = tmp_path / ".env.s5.streamlit.launch"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n"
        f"STREAMLIT_PORT={streamlit_port}\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def test_run_gui_no_export_without_launch_keeps_non_blocking_contract(tmp_path: Path) -> None:
    config = _build_test_config(tmp_path, streamlit_port=8505)
    result = run_gui(
        config=config,
        trade_date="20260213",
        export_mode="",
        launch_dashboard=False,
    )

    assert result.has_error is False
    assert result.quality_status == "PASS"
    assert result.go_nogo == "GO"
    assert result.dashboard_url is None


def test_run_gui_no_export_launches_streamlit_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _build_test_config(tmp_path, streamlit_port=8511)
    captured: dict[str, object] = {}

    def _fake_subprocess_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["kwargs"] = kwargs
        command = list(args[0]) if args else []
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(gui_app.subprocess, "run", _fake_subprocess_run)
    result = run_gui(
        config=config,
        trade_date="20260213",
        export_mode="",
        launch_dashboard=True,
    )

    assert result.has_error is False
    assert result.quality_status == "PASS"
    assert result.dashboard_url == "http://127.0.0.1:8511"
    assert "args" in captured
    assert "kwargs" in captured

    command = list(captured["args"][0])  # type: ignore[index]
    command_text = " ".join(str(token) for token in command)
    assert "-m streamlit run" in command_text
    assert "src\\gui\\dashboard.py" in command_text or "src/gui/dashboard.py" in command_text
    assert "--trade-date 20260213" in command_text

    kwargs = dict(captured["kwargs"])  # type: ignore[arg-type]
    env = kwargs.get("env")
    assert isinstance(env, dict)
    assert env["EQ_GUI_TRADE_DATE"] == "20260213"
    assert str(env["EQ_GUI_DUCKDB_PATH"]).endswith("emotionquant.duckdb")
