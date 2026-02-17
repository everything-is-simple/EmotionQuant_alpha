from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from src.config.config import Config

# DESIGN_TRACE:
# - docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md (§4 输出与表结构, §5 Gate 语义)
# - Governance/SpiralRoadmap/S2C-EXECUTION-CARD.md (§3 Validation)
DESIGN_TRACE = {
    "validation_algorithm": "docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md",
    "s2c_execution_card": "Governance/SpiralRoadmap/S2C-EXECUTION-CARD.md",
}


@dataclass(frozen=True)
class ValidationGateResult:
    trade_date: str
    count: int
    frame: pd.DataFrame
    final_gate: str
    selected_weight_plan: str
    has_fail: bool


SUPPORTED_CONTRACT_VERSION = "nc-v1"
DEFAULT_WEIGHT_PLAN_ID = "vp_balanced_v1"
DEFAULT_WEIGHT_MSS = 0.34
DEFAULT_WEIGHT_IRS = 0.33
DEFAULT_WEIGHT_PAS = 0.33


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _duckdb_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(series):
        return "BIGINT"
    if pd.api.types.is_float_dtype(series):
        return "DOUBLE"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "TIMESTAMP"
    return "VARCHAR"


def _ensure_columns(
    connection: duckdb.DuckDBPyConnection, table_name: str, frame: pd.DataFrame
) -> list[str]:
    if not _table_exists(connection, table_name):
        connection.register("schema_df", frame)
        connection.execute(
            f"CREATE TABLE {table_name} AS SELECT * FROM schema_df WHERE 1=0"
        )
        connection.unregister("schema_df")
    else:
        existing = {
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        }
        for column in frame.columns:
            if column in existing:
                continue
            column_type = _duckdb_type(frame[column])
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column} {column_type}"
            )

    return [
        str(row[1]) for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    ]


def _persist(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
    trade_date: str,
) -> int:
    with duckdb.connect(str(database_path)) as connection:
        table_columns = _ensure_columns(connection, table_name, frame)
        aligned = frame.copy()
        for column in table_columns:
            if column not in aligned.columns:
                aligned[column] = pd.NA
        aligned = aligned[table_columns]
        connection.register("incoming_df", aligned)
        connection.execute(f"DELETE FROM {table_name} WHERE trade_date = ?", [trade_date])
        connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_df")
        connection.unregister("incoming_df")
    return int(len(aligned))


def _build_weight_plan_frame(trade_date: str) -> pd.DataFrame:
    return pd.DataFrame.from_records(
        [
            {
                "trade_date": trade_date,
                "plan_id": DEFAULT_WEIGHT_PLAN_ID,
                "w_mss": DEFAULT_WEIGHT_MSS,
                "w_irs": DEFAULT_WEIGHT_IRS,
                "w_pas": DEFAULT_WEIGHT_PAS,
                "plan_status": "active",
                "contract_version": SUPPORTED_CONTRACT_VERSION,
                "created_at": pd.Timestamp.utcnow().isoformat(),
            }
        ]
    )


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
    selected_weight_plan = DEFAULT_WEIGHT_PLAN_ID if final_gate in {"PASS", "WARN"} else ""
    prescription = (
        "rebuild_l2_and_rerun_mss_irs_pas" if final_gate == "FAIL" else ""
    )
    weight_plan_frame = _build_weight_plan_frame(trade_date)
    frame = pd.DataFrame.from_records(
        [
            {
                "trade_date": trade_date,
                "final_gate": final_gate,
                "selected_weight_plan": selected_weight_plan,
                "issues": ";".join(issues) if issues else "",
                "validation_prescription": prescription,
                "contract_version": SUPPORTED_CONTRACT_VERSION,
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
    _persist(
        database_path=database_path,
        table_name="validation_weight_plan",
        frame=weight_plan_frame,
        trade_date=trade_date,
    )
    return ValidationGateResult(
        trade_date=trade_date,
        count=count,
        frame=frame,
        final_gate=final_gate,
        selected_weight_plan=selected_weight_plan,
        has_fail=final_gate == "FAIL",
    )
