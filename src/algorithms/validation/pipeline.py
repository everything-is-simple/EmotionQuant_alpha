from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from src.config.config import Config


@dataclass(frozen=True)
class ValidationGateResult:
    trade_date: str
    count: int
    frame: pd.DataFrame
    final_gate: str
    has_fail: bool


def _persist(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
    trade_date: str,
) -> int:
    with duckdb.connect(str(database_path)) as connection:
        connection.register("incoming_df", frame)
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM incoming_df WHERE 1=0"
        )
        connection.execute(f"DELETE FROM {table_name} WHERE trade_date = ?", [trade_date])
        connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_df")
        connection.unregister("incoming_df")
    return int(len(frame))


def run_validation_gate(
    *,
    trade_date: str,
    config: Config,
    irs_count: int,
    pas_count: int,
    mss_exists: bool,
) -> ValidationGateResult:
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not database_path.exists():
        raise FileNotFoundError("duckdb_not_found")

    issues: list[str] = []
    if not mss_exists:
        issues.append("mss_panorama_missing")
    if irs_count <= 0:
        issues.append("irs_industry_daily_empty")
    if pas_count <= 0:
        issues.append("stock_pas_daily_empty")

    final_gate = "FAIL" if issues else "PASS"
    prescription = (
        "rebuild_l2_and_rerun_mss_irs_pas" if final_gate == "FAIL" else ""
    )
    frame = pd.DataFrame.from_records(
        [
            {
                "trade_date": trade_date,
                "final_gate": final_gate,
                "issues": ";".join(issues) if issues else "",
                "validation_prescription": prescription,
                "contract_version": "nc-v1",
                "created_at": pd.Timestamp.utcnow().isoformat(),
            }
        ]
    )
    count = _persist(
        database_path=database_path,
        table_name="validation_gate_decision",
        frame=frame,
        trade_date=trade_date,
    )
    return ValidationGateResult(
        trade_date=trade_date,
        count=count,
        frame=frame,
        final_gate=final_gate,
        has_fail=final_gate == "FAIL",
    )
