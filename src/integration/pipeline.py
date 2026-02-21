from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from src.config.config import Config

# DESIGN_TRACE:
# - docs/design/core-algorithms/integration/integration-algorithm.md (§3 集成公式, §4 Gate 与桥接阻断)
# - Governance/SpiralRoadmap/S2C-EXECUTION-CARD.md (§3 Integration)
DESIGN_TRACE = {
    "integration_algorithm": "docs/design/core-algorithms/integration/integration-algorithm.md",
    "s2c_execution_card": "Governance/SpiralRoadmap/S2C-EXECUTION-CARD.md",
}

SUPPORTED_CONTRACT_VERSION = "nc-v1"
BASELINE_WEIGHT = round(1.0 / 3.0, 4)
BASELINE_PLAN_ALIASES = {"baseline", "vp_balanced_v1"}
TOP_DOWN_CYCLE_CAP = {
    "emergence": 1.00,
    "fermentation": 0.80,
    "acceleration": 0.70,
    "divergence": 0.60,
    "climax": 0.40,
    "diffusion": 0.50,
    "recession": 0.20,
    "unknown": 0.20,
}
INTEGRATED_TEXT_COLUMNS = {
    "trade_date",
    "stock_code",
    "industry_code",
    "industry_name",
    "direction",
    "consistency",
    "integration_mode",
    "weight_plan_id",
    "validation_gate",
    "integration_state",
    "recommendation",
    "mss_cycle",
    "opportunity_grade",
    "limit_guard_result",
    "session_guard_result",
    "contract_version",
    "created_at",
}

INTEGRATED_COLUMNS = [
    "trade_date",
    "stock_code",
    "industry_code",
    "industry_name",
    "mss_score",
    "irs_score",
    "pas_score",
    "final_score",
    "direction",
    "consistency",
    "integration_mode",
    "weight_plan_id",
    "w_mss",
    "w_irs",
    "w_pas",
    "validation_gate",
    "integration_state",
    "recommendation",
    "position_size",
    "mss_cycle",
    "opportunity_grade",
    "entry",
    "stop",
    "target",
    "risk_reward_ratio",
    "neutrality",
    "t1_restriction_hit",
    "limit_guard_result",
    "session_guard_result",
    "contract_version",
    "created_at",
]

QUALITY_GATE_COLUMNS = [
    "trade_date",
    "status",
    "validation_gate",
    "go_nogo",
    "integrated_count",
    "rr_filtered_count",
    "contract_version",
    "message",
    "created_at",
]


@dataclass(frozen=True)
class IntegrationRunResult:
    trade_date: str
    count: int
    frame: pd.DataFrame
    quality_status: str
    quality_frame: pd.DataFrame
    validation_gate: str
    integration_state: str
    go_nogo: str
    rr_filtered_count: int
    quality_message: str


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _column_exists(
    connection: duckdb.DuckDBPyConnection, table_name: str, column_name: str
) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = ? AND column_name = ?",
        [table_name, column_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _persist(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
    trade_date: str,
) -> None:
    with duckdb.connect(str(database_path)) as connection:
        if table_name == "integrated_recommendation" and _table_exists(connection, table_name):
            column_info = connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
            for row in column_info:
                column_name = str(row[1])
                column_type = str(row[2]).strip().upper()
                if column_name in INTEGRATED_TEXT_COLUMNS and column_type != "VARCHAR":
                    connection.execute(
                        f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE VARCHAR USING CAST({column_name} AS VARCHAR)"
                    )
        connection.register("incoming_df", frame)
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM incoming_df WHERE 1=0"
        )
        connection.execute(f"DELETE FROM {table_name} WHERE trade_date = ?", [trade_date])
        connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_df")
        connection.unregister("incoming_df")


def _to_stock_code(stock_code: str, ts_code: str) -> str:
    candidate = str(stock_code or "").strip()
    if candidate:
        return candidate
    ts = str(ts_code or "").strip()
    if "." in ts:
        return ts.split(".", maxsplit=1)[0]
    return ts


def _direction_from_trend(mss_trend: str) -> str:
    mapping = {
        "up": "bullish",
        "down": "bearish",
        "sideways": "neutral",
    }
    return mapping.get(str(mss_trend), "neutral")


def _direction_from_recommendation(recommendation: str) -> str:
    value = str(recommendation)
    if value in {"STRONG_BUY", "BUY"}:
        return "bullish"
    if value in {"SELL", "AVOID"}:
        return "bearish"
    return "neutral"


def _to_direction(mss_direction: str, irs_direction: str, pas_direction: str) -> str:
    direction_score = {
        "bullish": 1.0,
        "neutral": 0.0,
        "bearish": -1.0,
    }
    avg = (
        direction_score.get(mss_direction, 0.0)
        + direction_score.get(irs_direction, 0.0)
        + direction_score.get(pas_direction, 0.0)
    ) / 3.0
    if avg > 0.3:
        return "bullish"
    if avg < -0.3:
        return "bearish"
    return "neutral"


def _to_consistency(mss_direction: str, irs_direction: str, pas_direction: str) -> str:
    items = [mss_direction, irs_direction, pas_direction]
    unique_count = len(set(items))
    if unique_count == 1:
        return "consistent"
    if unique_count == 3:
        return "divergent"
    return "partial"


def _to_opportunity_grade(pas_score: float) -> str:
    if pas_score >= 85.0:
        return "S"
    if pas_score >= 70.0:
        return "A"
    if pas_score >= 55.0:
        return "B"
    if pas_score >= 40.0:
        return "C"
    return "D"


def _to_recommendation(final_score: float, mss_cycle: str) -> str:
    if final_score >= 75.0 and mss_cycle in {"emergence", "fermentation"}:
        candidate = "STRONG_BUY"
    elif final_score >= 70.0:
        candidate = "BUY"
    elif final_score >= 50.0:
        candidate = "HOLD"
    elif final_score >= 30.0:
        candidate = "SELL"
    else:
        candidate = "AVOID"

    if mss_cycle == "unknown" and candidate in {"STRONG_BUY", "BUY"}:
        return "HOLD"
    return candidate


def _to_limit_guard_result(close_price: float, high_price: float, low_price: float) -> str:
    if close_price <= 0.0:
        return "BLOCKED_INVALID_PRICE"
    if high_price > 0.0 and close_price >= high_price * 0.999:
        return "WARN_NEAR_LIMIT_UP"
    if low_price > 0.0 and close_price <= low_price * 1.001:
        return "WARN_NEAR_LIMIT_DOWN"
    return "PASS"


def _normalize_gate(gate: str) -> str:
    candidate = str(gate).strip().upper()
    if candidate in {"PASS", "WARN", "FAIL"}:
        return candidate
    return "FAIL"


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    candidate = str(value or "").strip().lower()
    if candidate in {"1", "true", "t", "yes", "y"}:
        return True
    if candidate in {"0", "false", "f", "no", "n"}:
        return False
    return False


def _to_float(value: object, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    if not pd.notna(parsed):
        return float(fallback)
    return float(parsed)


def _to_position_cap_ratio(value: object) -> float:
    return float(max(0.0, min(1.0, _to_float(value, 1.0))))


def _cycle_cap_ratio(mss_cycle: str) -> float:
    return float(TOP_DOWN_CYCLE_CAP.get(str(mss_cycle or "unknown"), 0.20))


def _resolve_weight_plan(
    *,
    database_path: Path,
    trade_date: str,
    selected_weight_plan: str,
) -> tuple[str, float, float, float, str]:
    if not selected_weight_plan:
        return ("", BASELINE_WEIGHT, BASELINE_WEIGHT, BASELINE_WEIGHT, "selected_weight_plan_missing")

    with duckdb.connect(str(database_path), read_only=True) as connection:
        if not _table_exists(connection, "validation_weight_plan"):
            return (
                "",
                BASELINE_WEIGHT,
                BASELINE_WEIGHT,
                BASELINE_WEIGHT,
                "validation_weight_plan_table_missing",
            )
        frame = connection.execute(
            "SELECT plan_id, w_mss, w_irs, w_pas, contract_version "
            "FROM validation_weight_plan "
            "WHERE trade_date = ? AND plan_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            [trade_date, selected_weight_plan],
        ).df()

    if frame.empty:
        return (
            "",
            BASELINE_WEIGHT,
            BASELINE_WEIGHT,
            BASELINE_WEIGHT,
            "selected_weight_plan_not_found",
        )

    record = frame.iloc[0].to_dict()
    if str(record.get("contract_version", "")).strip() != SUPPORTED_CONTRACT_VERSION:
        return (
            "",
            BASELINE_WEIGHT,
            BASELINE_WEIGHT,
            BASELINE_WEIGHT,
            "weight_plan_contract_version_mismatch",
        )

    try:
        w_mss = float(record.get("w_mss", 0.0))
        w_irs = float(record.get("w_irs", 0.0))
        w_pas = float(record.get("w_pas", 0.0))
    except (TypeError, ValueError):
        return ("", BASELINE_WEIGHT, BASELINE_WEIGHT, BASELINE_WEIGHT, "weight_plan_value_invalid")

    weight_sum = w_mss + w_irs + w_pas
    if min(w_mss, w_irs, w_pas) <= 0.0 or abs(weight_sum - 1.0) > 0.05:
        return ("", BASELINE_WEIGHT, BASELINE_WEIGHT, BASELINE_WEIGHT, "weight_plan_sum_invalid")

    plan_id = str(record.get("plan_id", "")).strip()
    if not plan_id:
        return ("", BASELINE_WEIGHT, BASELINE_WEIGHT, BASELINE_WEIGHT, "weight_plan_id_missing")

    return (plan_id, w_mss, w_irs, w_pas, "")


def _quality_status(
    *,
    validation_gate: str,
    contract_version: str,
    integrated_count: int,
    rr_filtered_count: int,
    bridge_error: str,
    integration_state: str,
) -> tuple[str, str, str]:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        return ("FAIL", "NO_GO", "contract_version_mismatch")
    if validation_gate == "FAIL":
        return ("FAIL", "NO_GO", "validation_gate_fail")
    if bridge_error:
        return ("FAIL", "NO_GO", bridge_error)
    if integrated_count <= 0:
        return ("FAIL", "NO_GO", "integrated_recommendation_empty")
    if validation_gate == "WARN":
        if integration_state.startswith("warn_"):
            return ("WARN", "GO", integration_state)
        return ("WARN", "GO", "validation_gate_warn")
    if rr_filtered_count > 0:
        return ("WARN", "GO", "rr_filtered_records_detected")
    return ("PASS", "GO", "all_checks_passed")


def run_integrated_daily(
    *,
    trade_date: str,
    config: Config,
    with_validation_bridge: bool = False,
) -> IntegrationRunResult:
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not database_path.exists():
        raise FileNotFoundError("duckdb_not_found")

    with duckdb.connect(str(database_path), read_only=True) as connection:
        required_tables = (
            "mss_panorama",
            "irs_industry_daily",
            "stock_pas_daily",
            "validation_gate_decision",
        )
        missing = [name for name in required_tables if not _table_exists(connection, name)]
        if missing:
            raise ValueError(f"required_tables_missing: {','.join(sorted(missing))}")

        mss_frame = connection.execute(
            "SELECT trade_date, mss_score, mss_cycle, mss_trend, contract_version "
            "FROM mss_panorama WHERE trade_date = ? "
            "ORDER BY created_at DESC LIMIT 1",
            [trade_date],
        ).df()
        if mss_frame.empty:
            raise ValueError("mss_panorama_empty_for_trade_date")

        irs_frame = connection.execute(
            "SELECT trade_date, industry_code, industry_name, irs_score, recommendation, "
            "allocation_advice, quality_flag, contract_version "
            "FROM irs_industry_daily WHERE trade_date = ? "
            "ORDER BY created_at DESC",
            [trade_date],
        ).df()
        if irs_frame.empty:
            raise ValueError("irs_industry_daily_empty_for_trade_date")

        pas_frame = connection.execute(
            "SELECT trade_date, stock_code, ts_code, pas_score, pas_direction, "
            "risk_reward_ratio, contract_version "
            "FROM stock_pas_daily WHERE trade_date = ? ORDER BY stock_code",
            [trade_date],
        ).df()
        if pas_frame.empty:
            raise ValueError("stock_pas_daily_empty_for_trade_date")

        if _table_exists(connection, "raw_daily"):
            raw_frame = connection.execute(
                "SELECT trade_date, stock_code, ts_code, open, high, low, close "
                "FROM raw_daily WHERE trade_date = ? ORDER BY stock_code",
                [trade_date],
            ).df()
        else:
            raw_frame = pd.DataFrame.from_records([])

        gate_columns = ["trade_date", "final_gate", "contract_version"]
        optional_gate_columns = (
            "selected_weight_plan",
            "fallback_plan",
            "position_cap_ratio",
            "tradability_pass_ratio",
            "impact_cost_bps",
            "candidate_exec_pass",
            "reason",
        )
        for column_name in optional_gate_columns:
            if _column_exists(connection, "validation_gate_decision", column_name):
                gate_columns.append(column_name)
        gate_frame = connection.execute(
            f"SELECT {', '.join(gate_columns)} FROM validation_gate_decision WHERE trade_date = ? "
            "ORDER BY created_at DESC LIMIT 1",
            [trade_date],
        ).df()
        if gate_frame.empty:
            raise ValueError("validation_gate_decision_empty_for_trade_date")

    mss_record = mss_frame.iloc[0].to_dict()
    irs_record = irs_frame.iloc[0].to_dict()
    gate_record = gate_frame.iloc[0].to_dict()

    validation_gate = _normalize_gate(str(gate_record.get("final_gate", "FAIL")))
    effective_gate = validation_gate
    validation_contract_version = str(gate_record.get("contract_version", "")).strip()
    selected_weight_plan = str(gate_record.get("selected_weight_plan", "")).strip()
    selected_plan_is_baseline = selected_weight_plan in BASELINE_PLAN_ALIASES
    fallback_plan = str(gate_record.get("fallback_plan", "")).strip()
    position_cap_ratio = _to_position_cap_ratio(gate_record.get("position_cap_ratio", 1.0))
    tradability_pass_ratio = _to_float(gate_record.get("tradability_pass_ratio", 1.0), 1.0)
    impact_cost_bps = _to_float(gate_record.get("impact_cost_bps", 0.0), 0.0)
    candidate_exec_pass = _to_bool(gate_record.get("candidate_exec_pass", True))

    weight_plan_id = "baseline"
    w_mss = BASELINE_WEIGHT
    w_irs = BASELINE_WEIGHT
    w_pas = BASELINE_WEIGHT
    bridge_error = ""
    if validation_gate != "FAIL":
        if selected_weight_plan in {"", "baseline"}:
            if with_validation_bridge and not selected_weight_plan:
                bridge_error = "selected_weight_plan_missing"
        else:
            (
                weight_plan_id,
                w_mss,
                w_irs,
                w_pas,
                bridge_error,
            ) = _resolve_weight_plan(
                database_path=database_path,
                trade_date=trade_date,
                selected_weight_plan=selected_weight_plan,
            )
            if bridge_error and not with_validation_bridge:
                bridge_error = ""
                effective_gate = "WARN"
                weight_plan_id = "baseline"
                w_mss = BASELINE_WEIGHT
                w_irs = BASELINE_WEIGHT
                w_pas = BASELINE_WEIGHT

    integration_state = "normal"
    if validation_gate == "FAIL":
        integration_state = "blocked_gate_fail"
    elif with_validation_bridge and bridge_error:
        integration_state = "blocked_bridge_missing"
    elif fallback_plan == "last_valid":
        effective_gate = "WARN"
        integration_state = "warn_data_stale"
        position_cap_ratio = min(position_cap_ratio, 0.80)
        weight_plan_id = "baseline"
        w_mss = BASELINE_WEIGHT
        w_irs = BASELINE_WEIGHT
        w_pas = BASELINE_WEIGHT
    elif (
        selected_weight_plan
        and not selected_plan_is_baseline
        and not candidate_exec_pass
    ):
        effective_gate = "WARN"
        integration_state = "warn_candidate_exec"
        position_cap_ratio = min(position_cap_ratio, 0.80)
        weight_plan_id = "baseline"
        w_mss = BASELINE_WEIGHT
        w_irs = BASELINE_WEIGHT
        w_pas = BASELINE_WEIGHT
    elif effective_gate == "WARN":
        integration_state = "warn_gate_fallback"

    integrated_rows: list[dict[str, object]] = []
    rr_filtered_count = 0
    created_at = pd.Timestamp.utcnow().isoformat()

    if (
        effective_gate != "FAIL"
        and validation_contract_version == SUPPORTED_CONTRACT_VERSION
        and not (with_validation_bridge and bridge_error)
    ):
        mss_score = float(mss_record.get("mss_score", 0.0))
        mss_temperature = _to_float(mss_record.get("mss_temperature", mss_score), mss_score)
        mss_cycle = str(mss_record.get("mss_cycle", "unknown"))
        mss_trend = str(mss_record.get("mss_trend", "sideways"))
        mss_direction = _direction_from_trend(mss_trend)

        irs_score = float(irs_record.get("irs_score", 0.0))
        irs_recommendation = str(irs_record.get("recommendation", "HOLD"))
        allocation_advice = str(irs_record.get("allocation_advice", "")).strip()
        irs_direction = _direction_from_recommendation(irs_recommendation)
        industry_code = str(irs_record.get("industry_code", "UNKNOWN"))
        industry_name = str(irs_record.get("industry_name", "未知行业"))
        cycle_position_cap = _cycle_cap_ratio(mss_cycle)

        raw_lookup_by_stock: dict[str, dict[str, object]] = {}
        raw_lookup_by_ts: dict[str, dict[str, object]] = {}
        for _, raw_row in raw_frame.iterrows():
            raw_item = raw_row.to_dict()
            stock_key = str(raw_item.get("stock_code", "")).strip()
            ts_key = str(raw_item.get("ts_code", "")).strip()
            if stock_key and stock_key not in raw_lookup_by_stock:
                raw_lookup_by_stock[stock_key] = raw_item
            if ts_key and ts_key not in raw_lookup_by_ts:
                raw_lookup_by_ts[ts_key] = raw_item

        for _, pas_row in pas_frame.iterrows():
            pas_record = pas_row.to_dict()
            risk_reward_ratio = float(pas_record.get("risk_reward_ratio", 0.0))
            if risk_reward_ratio < 1.0:
                rr_filtered_count += 1
                continue

            stock_code = _to_stock_code(
                str(pas_record.get("stock_code", "")),
                str(pas_record.get("ts_code", "")),
            )
            ts_code = str(pas_record.get("ts_code", "")).strip()
            raw_item = raw_lookup_by_stock.get(stock_code) or raw_lookup_by_ts.get(ts_code) or {}

            open_price = float(raw_item.get("open", 0.0) or 0.0)
            high_price = float(raw_item.get("high", 0.0) or 0.0)
            low_price = float(raw_item.get("low", 0.0) or 0.0)
            close_price = float(raw_item.get("close", 0.0) or 0.0)

            entry = close_price if close_price > 0.0 else (open_price if open_price > 0.0 else 1.0)
            stop = low_price if low_price > 0.0 else entry * 0.98
            if stop >= entry:
                stop = entry * 0.98
            target = entry + (entry - stop) * risk_reward_ratio

            pas_score = float(pas_record.get("pas_score", 0.0))
            effective_pas_score = pas_score * (0.85 if allocation_advice == "回避" else 1.0)
            pas_direction = str(pas_record.get("pas_direction", "neutral"))
            if pas_direction not in {"bullish", "bearish", "neutral"}:
                pas_direction = "neutral"

            final_score = round(
                mss_score * w_mss + irs_score * w_irs + effective_pas_score * w_pas,
                4,
            )
            direction = _to_direction(mss_direction, irs_direction, pas_direction)
            consistency = _to_consistency(mss_direction, irs_direction, pas_direction)
            recommendation = _to_recommendation(final_score, mss_cycle)
            opportunity_grade = _to_opportunity_grade(pas_score)
            neutrality = round(max(0.0, min(1.0, 1.0 - abs(final_score - 50.0) / 50.0)), 4)

            base_position_size = max(0.0, min(1.0, final_score / 100.0))
            if mss_temperature < 30.0 or mss_temperature > 80.0:
                base_position_size *= 0.85
            position_cap = min(position_cap_ratio, cycle_position_cap)
            if effective_gate == "WARN":
                position_cap = min(position_cap, 0.80)
            position_size = round(min(base_position_size, position_cap), 4)

            integrated_rows.append(
                {
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "industry_code": industry_code,
                    "industry_name": industry_name,
                    "mss_score": round(mss_score, 4),
                    "irs_score": round(irs_score, 4),
                    "pas_score": round(pas_score, 4),
                    "final_score": final_score,
                    "direction": direction,
                    "consistency": consistency,
                    "integration_mode": "top_down",
                    "weight_plan_id": weight_plan_id,
                    "w_mss": round(w_mss, 4),
                    "w_irs": round(w_irs, 4),
                    "w_pas": round(w_pas, 4),
                    "validation_gate": effective_gate,
                    "integration_state": integration_state,
                    "recommendation": recommendation,
                    "position_size": position_size,
                    "mss_cycle": mss_cycle,
                    "opportunity_grade": opportunity_grade,
                    "entry": round(entry, 4),
                    "stop": round(stop, 4),
                    "target": round(target, 4),
                    "risk_reward_ratio": round(risk_reward_ratio, 4),
                    "neutrality": neutrality,
                    "t1_restriction_hit": False,
                    "limit_guard_result": _to_limit_guard_result(close_price, high_price, low_price),
                    "session_guard_result": "PASS",
                    "contract_version": SUPPORTED_CONTRACT_VERSION,
                    "created_at": created_at,
                }
            )

    integrated_frame = (
        pd.DataFrame.from_records(integrated_rows)
        if integrated_rows
        else pd.DataFrame(columns=INTEGRATED_COLUMNS)
    )
    integrated_frame = integrated_frame.reindex(columns=INTEGRATED_COLUMNS)
    integrated_count = int(len(integrated_frame))

    quality_status, go_nogo, quality_message = _quality_status(
        validation_gate=effective_gate,
        contract_version=validation_contract_version,
        integrated_count=integrated_count,
        rr_filtered_count=rr_filtered_count,
        bridge_error=bridge_error,
        integration_state=integration_state,
    )
    quality_frame = pd.DataFrame.from_records(
        [
            {
                "trade_date": trade_date,
                "status": quality_status,
                "validation_gate": effective_gate,
                "go_nogo": go_nogo,
                "integrated_count": integrated_count,
                "rr_filtered_count": rr_filtered_count,
                "contract_version": validation_contract_version,
                "message": quality_message,
                "created_at": created_at,
            }
        ]
    ).reindex(columns=QUALITY_GATE_COLUMNS)

    _persist(
        database_path=database_path,
        table_name="integrated_recommendation",
        frame=integrated_frame,
        trade_date=trade_date,
    )
    _persist(
        database_path=database_path,
        table_name="quality_gate_report",
        frame=quality_frame,
        trade_date=trade_date,
    )

    return IntegrationRunResult(
        trade_date=trade_date,
        count=integrated_count,
        frame=integrated_frame,
        quality_status=quality_status,
        quality_frame=quality_frame,
        validation_gate=effective_gate,
        integration_state=integration_state,
        go_nogo=go_nogo,
        rr_filtered_count=rr_filtered_count,
        quality_message=quality_message,
    )
