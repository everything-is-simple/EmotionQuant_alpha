from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from src.config.config import Config

SUPPORTED_EXPORT_MODE = {"", "daily-report"}


@dataclass(frozen=True)
class GuiRunResult:
    trade_date: str
    export_mode: str
    artifacts_dir: Path
    daily_report_path: Path | None
    gui_export_manifest_path: Path | None
    gate_report_path: Path | None
    consumption_path: Path | None
    quality_status: str
    go_nogo: str
    dashboard_url: str | None
    has_error: bool


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validate_trade_date(value: str) -> None:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"invalid trade date: {value}; expected YYYYMMDD") from exc


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _read_daily_metrics(*, database_path: Path, trade_date: str) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    metrics: dict[str, Any] = {
        "integrated_recommendation_count": 0,
        "filled_buy_trade_count": 0,
        "validation_final_gate": "unknown",
    }

    if not database_path.exists():
        warnings.append("duckdb_not_found")
        return metrics, warnings

    with duckdb.connect(str(database_path), read_only=True) as connection:
        if _table_exists(connection, "integrated_recommendation"):
            row = connection.execute(
                "SELECT COUNT(*) FROM integrated_recommendation WHERE CAST(trade_date AS VARCHAR) = ?",
                [trade_date],
            ).fetchone()
            metrics["integrated_recommendation_count"] = int(row[0]) if row else 0
        else:
            warnings.append("integrated_recommendation_missing")

        if _table_exists(connection, "trade_records"):
            try:
                row = connection.execute(
                    "SELECT COUNT(*) FROM trade_records "
                    "WHERE CAST(trade_date AS VARCHAR) = ? AND status = 'filled' AND direction = 'buy'",
                    [trade_date],
                ).fetchone()
            except duckdb.Error:
                row = connection.execute(
                    "SELECT COUNT(*) FROM trade_records WHERE CAST(trade_date AS VARCHAR) = ?",
                    [trade_date],
                ).fetchone()
                warnings.append("trade_records_schema_fallback")
            metrics["filled_buy_trade_count"] = int(row[0]) if row else 0
        else:
            warnings.append("trade_records_missing")

        if _table_exists(connection, "validation_gate_decision"):
            row = connection.execute(
                "SELECT final_gate FROM validation_gate_decision "
                "WHERE CAST(trade_date AS VARCHAR) = ? LIMIT 1",
                [trade_date],
            ).fetchone()
            if row:
                metrics["validation_final_gate"] = str(row[0])
            else:
                warnings.append("validation_gate_decision_empty_for_trade_date")
        else:
            warnings.append("validation_gate_decision_missing")

    return metrics, warnings


def _write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _streamlit_dashboard_script_path() -> Path:
    return Path(__file__).with_name("dashboard.py")


def _build_streamlit_command(*, trade_date: str, streamlit_port: int) -> list[str]:
    script_path = _streamlit_dashboard_script_path()
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(script_path),
        "--server.port",
        str(streamlit_port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        "--",
        "--trade-date",
        trade_date,
    ]


def _launch_streamlit_dashboard(
    *,
    trade_date: str,
    database_path: Path,
    streamlit_port: int,
) -> subprocess.CompletedProcess[str]:
    command = _build_streamlit_command(trade_date=trade_date, streamlit_port=streamlit_port)
    env = os.environ.copy()
    env["EQ_GUI_TRADE_DATE"] = trade_date
    env["EQ_GUI_DUCKDB_PATH"] = str(database_path)
    return subprocess.run(command, check=False, env=env, text=True)


def run_gui(
    *,
    config: Config,
    trade_date: str,
    export_mode: str = "",
    launch_dashboard: bool = False,
    streamlit_port: int | None = None,
) -> GuiRunResult:
    normalized_date = str(trade_date).strip()
    _validate_trade_date(normalized_date)
    normalized_export = str(export_mode or "").strip()
    if normalized_export not in SUPPORTED_EXPORT_MODE:
        raise ValueError(
            f"unsupported gui export mode: {normalized_export}; supported={sorted(SUPPORTED_EXPORT_MODE)}"
        )

    artifacts_dir = Path("artifacts") / "spiral-s5" / normalized_date
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    effective_streamlit_port = int(streamlit_port or config.streamlit_port or 8501)
    if not normalized_export:
        if launch_dashboard:
            completed = _launch_streamlit_dashboard(
                trade_date=normalized_date,
                database_path=database_path,
                streamlit_port=effective_streamlit_port,
            )
            has_error = completed.returncode not in {0, 130}
            quality_status = "FAIL" if has_error else "PASS"
            go_nogo = "NO_GO" if has_error else "GO"
            return GuiRunResult(
                trade_date=normalized_date,
                export_mode="",
                artifacts_dir=artifacts_dir,
                daily_report_path=None,
                gui_export_manifest_path=None,
                gate_report_path=None,
                consumption_path=None,
                quality_status=quality_status,
                go_nogo=go_nogo,
                dashboard_url=f"http://127.0.0.1:{effective_streamlit_port}",
                has_error=has_error,
            )
        return GuiRunResult(
            trade_date=normalized_date,
            export_mode="",
            artifacts_dir=artifacts_dir,
            daily_report_path=None,
            gui_export_manifest_path=None,
            gate_report_path=None,
            consumption_path=None,
            quality_status="PASS",
            go_nogo="GO",
            dashboard_url=None,
            has_error=False,
        )

    metrics, warnings = _read_daily_metrics(database_path=database_path, trade_date=normalized_date)
    quality_status = "WARN" if warnings else "PASS"
    go_nogo = "GO"
    created_at = _utc_now_text()

    daily_report_path = artifacts_dir / "daily_report_sample.md"
    gui_export_manifest_path = artifacts_dir / "gui_export_manifest.json"
    gate_report_path = artifacts_dir / "gate_report.md"
    consumption_path = artifacts_dir / "consumption.md"

    _write_markdown(
        daily_report_path,
        [
            "# S5 Daily Report",
            "",
            f"- trade_date: {normalized_date}",
            f"- generated_at_utc: {created_at}",
            f"- integrated_recommendation_count: {metrics['integrated_recommendation_count']}",
            f"- filled_buy_trade_count: {metrics['filled_buy_trade_count']}",
            f"- validation_final_gate: {metrics['validation_final_gate']}",
            "",
            "## Notes",
            f"- warnings: {warnings if warnings else 'none'}",
        ],
    )
    _write_json(
        gui_export_manifest_path,
        {
            "trade_date": normalized_date,
            "export_mode": normalized_export,
            "generated_at_utc": created_at,
            "database_path": str(database_path),
            "read_only_data_access": True,
            "quality_status": quality_status,
            "go_nogo": go_nogo,
            "warnings": warnings,
            "metrics": metrics,
            "daily_report_path": str(daily_report_path),
            "gate_report_path": str(gate_report_path),
            "consumption_path": str(consumption_path),
        },
    )
    _write_markdown(
        gate_report_path,
        [
            "# S5 GUI Gate Report",
            "",
            f"- trade_date: {normalized_date}",
            f"- quality_status: {quality_status}",
            f"- go_nogo: {go_nogo}",
            f"- warning_count: {len(warnings)}",
            f"- warnings: {warnings if warnings else 'none'}",
        ],
    )
    _write_markdown(
        consumption_path,
        [
            "# S5 GUI Consumption",
            "",
            "- producer: eq gui --export daily-report",
            "- consumer: S6 run-all reproducibility baseline",
            "- consumed_fields: integrated_recommendation_count,filled_buy_trade_count,validation_final_gate",
            f"- trade_date: {normalized_date}",
            "- read_only_data_access: true",
            f"- daily_report_path: {daily_report_path}",
        ],
    )

    return GuiRunResult(
        trade_date=normalized_date,
        export_mode=normalized_export,
        artifacts_dir=artifacts_dir,
        daily_report_path=daily_report_path,
        gui_export_manifest_path=gui_export_manifest_path,
        gate_report_path=gate_report_path,
        consumption_path=consumption_path,
        quality_status=quality_status,
        go_nogo=go_nogo,
        dashboard_url=None,
        has_error=False,
    )
