from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from src.config.config import Config
import src.gui.app as gui_app
from src.gui.app import run_gui


def test_gui_daily_report_reads_duckdb_in_read_only_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.s5.readonly"
    env_file.write_text(
        f"DATA_PATH={tmp_path / 'eq_data'}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    config = Config.from_env(env_file=str(env_file))
    duckdb_dir = Path(config.duckdb_dir)
    duckdb_dir.mkdir(parents=True, exist_ok=True)
    db_path = duckdb_dir / "emotionquant.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            "CREATE TABLE integrated_recommendation (trade_date VARCHAR, stock_code VARCHAR)"
        )
        connection.execute(
            "INSERT INTO integrated_recommendation VALUES ('20260213', '000001')"
        )

    read_only_flags: list[bool] = []
    original_connect = gui_app.duckdb.connect

    def _wrapped_connect(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        read_only_flags.append(bool(kwargs.get("read_only", False)))
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(gui_app.duckdb, "connect", _wrapped_connect)
    result = run_gui(config=config, trade_date="20260213", export_mode="daily-report")

    assert result.export_mode == "daily-report"
    assert read_only_flags
    assert all(read_only_flags)
    assert result.consumption_path is not None
    consumption_text = result.consumption_path.read_text(encoding="utf-8")
    assert "read_only_data_access: true" in consumption_text
