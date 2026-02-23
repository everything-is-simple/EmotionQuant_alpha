from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.config.config import Config
from src.gui.app import run_gui


def test_daily_report_export_writes_required_artifacts(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.s5.daily_report"
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
        connection.execute(
            "CREATE TABLE trade_records "
            "(trade_date VARCHAR, stock_code VARCHAR, status VARCHAR, direction VARCHAR)"
        )
        connection.execute(
            "INSERT INTO trade_records VALUES ('20260213', '000001', 'filled', 'buy')"
        )
        connection.execute(
            "CREATE TABLE validation_gate_decision (trade_date VARCHAR, final_gate VARCHAR)"
        )
        connection.execute(
            "INSERT INTO validation_gate_decision VALUES ('20260213', 'WARN')"
        )

    result = run_gui(config=config, trade_date="20260213", export_mode="daily-report")
    assert result.quality_status == "PASS"
    assert result.go_nogo == "GO"
    assert result.daily_report_path is not None
    assert result.gui_export_manifest_path is not None
    assert result.gate_report_path is not None
    assert result.consumption_path is not None

    assert result.daily_report_path.exists()
    assert result.gui_export_manifest_path.exists()
    assert result.gate_report_path.exists()
    assert result.consumption_path.exists()

    manifest = json.loads(result.gui_export_manifest_path.read_text(encoding="utf-8"))
    assert manifest["trade_date"] == "20260213"
    assert manifest["export_mode"] == "daily-report"
    assert manifest["read_only_data_access"] is True
    assert manifest["metrics"]["integrated_recommendation_count"] == 1
    assert manifest["metrics"]["filled_buy_trade_count"] == 1
    assert manifest["metrics"]["validation_final_gate"] == "WARN"
