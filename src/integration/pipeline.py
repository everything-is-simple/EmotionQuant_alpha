"""集成推荐流水线（S2B）：MSS × IRS × PAS 三模块融合 → 最终推荐列表。

四种集成模式（对应执行卡 S2B）：
  - top_down       : 自上而下，MSS 周期驱动仓位上限
  - bottom_up      : 自下而上，PAS 个股活跃度优先
  - dual_verify    : 双重验证，两套排名取交集
  - complementary  : 互补融合，加权平均

硬约束（铁律）：
  - 每日最多推荐 20 只（MAX_RECOMMENDATIONS_PER_DAY）
  - 单行业最多推荐 5 只（MAX_RECOMMENDATIONS_PER_INDUSTRY）

输出: integrated_recommendation 表 + quality_gate_report 表。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from src.config.config import Config
from src.db.helpers import column_exists as _column_exists, table_exists as _table_exists
from src.models.enums import (
    GateDecision,
    MssCycle,
    PasDirection,
    RecommendationGrade,
    Trend,
)

# DESIGN_TRACE:
# - docs/design/core-algorithms/integration/integration-algorithm.md (§3 集成公式, §4 Gate 与桥接阻断)
# - Governance/SpiralRoadmap/execution-cards/S2C-EXECUTION-CARD.md (§3 Integration)
DESIGN_TRACE = {
    "integration_algorithm": "docs/design/core-algorithms/integration/integration-algorithm.md",
    "s2c_execution_card": "Governance/SpiralRoadmap/execution-cards/S2C-EXECUTION-CARD.md",
}

SUPPORTED_CONTRACT_VERSION = "nc-v1"
BASELINE_WEIGHT = round(1.0 / 3.0, 4)
MAX_MODULE_WEIGHT = 0.60
BASELINE_PLAN_ALIASES = {"baseline", "vp_balanced_v1"}
SUPPORTED_INTEGRATION_MODES = {"top_down", "bottom_up", "dual_verify", "complementary"}
MAX_RECOMMENDATIONS_PER_DAY = 20
MAX_RECOMMENDATIONS_PER_INDUSTRY = 5
TOP_DOWN_CYCLE_CAP = {
    MssCycle.EMERGENCE: 1.00,
    MssCycle.FERMENTATION: 0.80,
    MssCycle.ACCELERATION: 0.70,
    MssCycle.DIVERGENCE: 0.60,
    MssCycle.CLIMAX: 0.40,
    MssCycle.DIFFUSION: 0.50,
    MssCycle.RECESSION: 0.20,
    MssCycle.UNKNOWN: 0.20,
}
BOTTOM_UP_CYCLE_CAP = {
    MssCycle.EMERGENCE: 0.80,
    MssCycle.FERMENTATION: 0.80,
    MssCycle.ACCELERATION: 0.70,
    MssCycle.DIVERGENCE: 0.60,
    MssCycle.CLIMAX: 0.40,
    MssCycle.DIFFUSION: 0.50,
    MssCycle.RECESSION: 0.20,
    MssCycle.UNKNOWN: 0.20,
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
INTEGRATED_NUMERIC_COLUMNS = {
    "mss_score",
    "irs_score",
    "pas_score",
    "final_score",
    "w_mss",
    "w_irs",
    "w_pas",
    "position_size",
    "entry",
    "stop",
    "target",
    "risk_reward_ratio",
    "neutrality",
}
INTEGRATED_BOOLEAN_COLUMNS = {"t1_restriction_hit"}

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
    integration_mode: str
    frame: pd.DataFrame
    quality_status: str
    quality_frame: pd.DataFrame
    validation_gate: str
    integration_state: str
    go_nogo: str
    rr_filtered_count: int
    quality_message: str




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
                    continue
                if column_name in INTEGRATED_NUMERIC_COLUMNS and column_type in {
                    "TINYINT",
                    "SMALLINT",
                    "INTEGER",
                    "BIGINT",
                    "HUGEINT",
                    "UTINYINT",
                    "USMALLINT",
                    "UINTEGER",
                    "UBIGINT",
                    "UHUGEINT",
                    "DECIMAL",
                    "FLOAT",
                    "REAL",
                    "NUMERIC",
                } and column_type != "DOUBLE":
                    connection.execute(
                        f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE DOUBLE USING CAST({column_name} AS DOUBLE)"
                    )
                    continue
                if column_name in INTEGRATED_BOOLEAN_COLUMNS and column_type != "BOOLEAN":
                    connection.execute(
                        f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE BOOLEAN USING CAST({column_name} AS BOOLEAN)"
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
        Trend.UP: PasDirection.BULLISH,
        Trend.DOWN: PasDirection.BEARISH,
        Trend.SIDEWAYS: PasDirection.NEUTRAL,
    }
    return mapping.get(str(mss_trend), PasDirection.NEUTRAL)


def _direction_from_recommendation(recommendation: str) -> str:
    value = str(recommendation)
    if value in {RecommendationGrade.STRONG_BUY, RecommendationGrade.BUY}:
        return PasDirection.BULLISH
    if value in {RecommendationGrade.SELL, RecommendationGrade.AVOID}:
        return PasDirection.BEARISH
    return PasDirection.NEUTRAL


def _to_direction(mss_direction: str, irs_direction: str, pas_direction: str) -> str:
    direction_score = {
        PasDirection.BULLISH: 1.0,
        PasDirection.NEUTRAL: 0.0,
        PasDirection.BEARISH: -1.0,
    }
    avg = (
        direction_score.get(mss_direction, 0.0)
        + direction_score.get(irs_direction, 0.0)
        + direction_score.get(pas_direction, 0.0)
    ) / 3.0
    if avg > 0.3:
        return PasDirection.BULLISH
    if avg < -0.3:
        return PasDirection.BEARISH
    return PasDirection.NEUTRAL


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
    if final_score >= 75.0 and mss_cycle in {MssCycle.EMERGENCE, MssCycle.FERMENTATION}:
        candidate = RecommendationGrade.STRONG_BUY
    elif final_score >= 70.0:
        candidate = RecommendationGrade.BUY
    elif final_score >= 50.0:
        candidate = RecommendationGrade.HOLD
    elif final_score >= 30.0:
        candidate = RecommendationGrade.SELL
    else:
        candidate = RecommendationGrade.AVOID

    if mss_cycle == MssCycle.UNKNOWN and candidate in {RecommendationGrade.STRONG_BUY, RecommendationGrade.BUY}:
        return RecommendationGrade.HOLD
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
    if candidate in {GateDecision.PASS, GateDecision.WARN, GateDecision.FAIL}:
        return candidate
    return GateDecision.FAIL


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


def _safe_text(value: object, default: str = "") -> str:
    if value is None:
        return default
    try:
        if not pd.notna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    if text.lower() in {"<na>", "nan", "none"}:
        return default
    return text or default


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


def _cycle_cap_ratio_bottom_up(mss_cycle: str) -> float:
    return float(BOTTOM_UP_CYCLE_CAP.get(str(mss_cycle or "unknown"), 0.20))


def _normalize_integration_mode(mode: str) -> str:
    candidate = str(mode or "top_down").strip().lower() or "top_down"
    if candidate not in SUPPORTED_INTEGRATION_MODES:
        raise ValueError(f"unsupported integration_mode: {candidate}")
    return candidate


def _grade_priority(grade: str) -> int:
    mapping = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}
    return mapping.get(str(grade or "").strip().upper(), 5)


def _recommendation_priority(recommendation: str) -> int:
    mapping = {"STRONG_BUY": 0, "BUY": 1, "HOLD": 2, "SELL": 3, "AVOID": 4}
    return mapping.get(str(recommendation or "").strip().upper(), 5)


def _apply_recommendation_limits(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    ranked = frame.copy()
    ranked["__grade_priority"] = ranked["opportunity_grade"].map(_grade_priority)
    ranked["__recommendation_priority"] = ranked["recommendation"].map(_recommendation_priority)
    ranked = ranked.sort_values(
        by=["__grade_priority", "__recommendation_priority", "final_score", "position_size"],
        ascending=[True, True, False, False],
        kind="stable",
    )

    # 限额策略采用“全市场排序后顺序挑选”，确保每日20/行业5的硬约束可解释。
    picked_indices: list[int] = []
    industry_counts: dict[str, int] = {}
    for tup in ranked.itertuples():
        if len(picked_indices) >= MAX_RECOMMENDATIONS_PER_DAY:
            break
        industry_code = _safe_text(getattr(tup, "industry_code", ""), "UNKNOWN")
        current_count = int(industry_counts.get(industry_code, 0))
        if current_count >= MAX_RECOMMENDATIONS_PER_INDUSTRY:
            continue
        picked_indices.append(tup.Index)
        industry_counts[industry_code] = current_count + 1

    limited = ranked.loc[picked_indices].copy()
    limited = limited.drop(columns=["__grade_priority", "__recommendation_priority"], errors="ignore")
    return limited.reset_index(drop=True)


def _latest_snapshot_trade_date(
    connection: duckdb.DuckDBPyConnection,
    *,
    table_name: str,
    trade_date: str,
) -> str:
    if not _table_exists(connection, table_name):
        return ""
    row = connection.execute(
        f"SELECT MAX(CAST(trade_date AS VARCHAR)) FROM {table_name} "
        "WHERE CAST(trade_date AS VARCHAR) <= ?",
        [trade_date],
    ).fetchone()
    if not row:
        return ""
    return _safe_text(row[0], "")


def _load_stock_industry_lookup(
    connection: duckdb.DuckDBPyConnection,
    *,
    trade_date: str,
) -> tuple[dict[str, tuple[str, str]], dict[str, tuple[str, str]]]:
    if not _table_exists(connection, "raw_index_member"):
        return ({}, {})
    if not _table_exists(connection, "raw_index_classify"):
        return ({}, {})

    member_snapshot = _latest_snapshot_trade_date(
        connection,
        table_name="raw_index_member",
        trade_date=trade_date,
    )
    classify_snapshot = _latest_snapshot_trade_date(
        connection,
        table_name="raw_index_classify",
        trade_date=trade_date,
    )
    if not member_snapshot or not classify_snapshot:
        return ({}, {})

    # raw_index_member/raw_index_classify 采用最近快照，避免跨日混用导致行业映射漂移。
    frame = connection.execute(
        "SELECT m.con_code, m.index_code, m.in_date, m.out_date, "
        "c.industry_code, c.industry_name "
        "FROM raw_index_member m "
        "LEFT JOIN raw_index_classify c ON m.index_code = c.index_code "
        "WHERE CAST(m.trade_date AS VARCHAR) = ? "
        "AND CAST(c.trade_date AS VARCHAR) = ?",
        [member_snapshot, classify_snapshot],
    ).df()
    if frame.empty:
        return ({}, {})

    # 向量化构建 stock→industry 查找表（消除 iterrows）
    f = frame.copy()
    f["_ts"] = f["con_code"].astype(str).str.strip().str.upper()
    f = f[f["_ts"] != ""]
    f["_in"] = f["in_date"].astype(str).str.strip().replace("<NA>", "").replace("None", "").replace("nan", "")
    f["_out"] = f["out_date"].astype(str).str.strip().replace("<NA>", "").replace("None", "").replace("nan", "")
    # 过滤未生效/已失效的成员
    f = f[~((f["_in"] != "") & (f["_in"] > trade_date))]
    f = f[~((f["_out"] != "") & (f["_out"] <= trade_date))]
    f["_ic"] = f["industry_code"].fillna("UNKNOWN").astype(str).str.strip()
    f["_in_name"] = f["industry_name"].fillna("未知行业").astype(str).str.strip()
    f["_ic"] = f["_ic"].where(f["_ic"] != "", "UNKNOWN")
    f["_in_name"] = f["_in_name"].where(f["_in_name"] != "", "未知行业")
    f["_sc"] = f["_ts"].apply(lambda x: _to_stock_code("", x))

    # 取每个 stock_code / ts_code 的第一条记录
    lookup_by_stock: dict[str, tuple[str, str]] = {}
    lookup_by_ts: dict[str, tuple[str, str]] = {}
    f_dedup_sc = f[f["_sc"] != ""].drop_duplicates(subset="_sc", keep="first")
    for sc, ic, iname in zip(f_dedup_sc["_sc"], f_dedup_sc["_ic"], f_dedup_sc["_in_name"]):
        lookup_by_stock[sc] = (ic, iname)
    f_dedup_ts = f.drop_duplicates(subset="_ts", keep="first")
    for ts, ic, iname in zip(f_dedup_ts["_ts"], f_dedup_ts["_ic"], f_dedup_ts["_in_name"]):
        lookup_by_ts[ts] = (ic, iname)
    return (lookup_by_stock, lookup_by_ts)


def _resolve_weight_plan(
    *,
    database_path: Path,
    trade_date: str,
    selected_weight_plan: str,
) -> tuple[str, float, float, float, str]:
    if not selected_weight_plan:
        return ("", BASELINE_WEIGHT, BASELINE_WEIGHT, BASELINE_WEIGHT, "selected_weight_plan_missing")

    stock_industry_by_stock: dict[str, tuple[str, str]] = {}
    stock_industry_by_ts: dict[str, tuple[str, str]] = {}
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

    # 单模块权重上限校验（与 Validation 权重门一致）。
    if max(w_mss, w_irs, w_pas) > MAX_MODULE_WEIGHT:
        return ("", BASELINE_WEIGHT, BASELINE_WEIGHT, BASELINE_WEIGHT, "weight_plan_max_exceeded")

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
    integration_mode: str = "top_down",
) -> IntegrationRunResult:
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not database_path.exists():
        raise FileNotFoundError("duckdb_not_found")
    resolved_integration_mode = _normalize_integration_mode(integration_mode)

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

        mss_columns = ["trade_date", "mss_score"]
        optional_mss_columns = ("mss_temperature", "mss_cycle", "mss_trend", "contract_version")
        for column_name in optional_mss_columns:
            if _column_exists(connection, "mss_panorama", column_name):
                mss_columns.append(column_name)
        order_column = "created_at" if _column_exists(connection, "mss_panorama", "created_at") else "trade_date"
        mss_frame = connection.execute(
            f"SELECT {', '.join(mss_columns)} "
            "FROM mss_panorama WHERE trade_date = ? "
            f"ORDER BY {order_column} DESC LIMIT 1",
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

        pas_columns = [
            "trade_date",
            "stock_code",
            "ts_code",
            "pas_score",
            "pas_direction",
            "risk_reward_ratio",
            "contract_version",
        ]
        if _column_exists(connection, "stock_pas_daily", "opportunity_grade"):
            pas_columns.append("opportunity_grade")
        pas_frame = connection.execute(
            f"SELECT {', '.join(pas_columns)} "
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

        stock_industry_by_stock, stock_industry_by_ts = _load_stock_industry_lookup(
            connection,
            trade_date=trade_date,
        )

    mss_record = mss_frame.iloc[0].to_dict()
    gate_record = gate_frame.iloc[0].to_dict()
    default_irs_record = irs_frame.iloc[0].to_dict()
    irs_by_industry: dict[str, dict[str, object]] = {}
    _irs_dedup = irs_frame.copy()
    _irs_dedup["ic_key"] = _irs_dedup["industry_code"].fillna("").astype(str).str.strip()
    _irs_dedup = _irs_dedup[_irs_dedup["ic_key"] != ""].drop_duplicates(subset="ic_key", keep="first")
    for tup in _irs_dedup.itertuples(index=False):
        irs_by_industry[tup.ic_key] = {col: getattr(tup, col, None) for col in irs_frame.columns}

    validation_gate = _normalize_gate(str(gate_record.get("final_gate", "FAIL")))
    effective_gate = validation_gate
    validation_contract_version = str(gate_record.get("contract_version", "")).strip()
    selected_weight_plan = str(gate_record.get("selected_weight_plan", "")).strip()
    selected_plan_is_baseline = selected_weight_plan == "baseline"
    selected_plan_is_baseline_alias = selected_weight_plan in BASELINE_PLAN_ALIASES
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
    has_cold_start_industry = any(
        str(item.get("quality_flag", "")).strip() == "cold_start" for item in irs_by_industry.values()
    )
    has_stale_industry = any(
        str(item.get("quality_flag", "")).strip() == "stale" for item in irs_by_industry.values()
    )
    if validation_gate == "FAIL":
        integration_state = "blocked_gate_fail"
    elif with_validation_bridge and bridge_error:
        integration_state = "blocked_bridge_missing"
    elif (
        selected_weight_plan
        and not selected_plan_is_baseline_alias
        and (
            not candidate_exec_pass
            or tradability_pass_ratio < 0.90
            or impact_cost_bps > 35.0
        )
    ):
        effective_gate = "WARN"
        integration_state = "warn_candidate_exec"
        position_cap_ratio = min(position_cap_ratio, 0.80)
        weight_plan_id = "baseline"
        w_mss = BASELINE_WEIGHT
        w_irs = BASELINE_WEIGHT
        w_pas = BASELINE_WEIGHT
    elif has_cold_start_industry:
        effective_gate = "WARN"
        integration_state = "warn_data_cold_start"
        position_cap_ratio = min(position_cap_ratio, 0.80)
    elif has_stale_industry or fallback_plan == "last_valid":
        effective_gate = "WARN"
        integration_state = "warn_data_stale"
        position_cap_ratio = min(position_cap_ratio, 0.80)
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
        cycle_position_cap_top_down = _cycle_cap_ratio(mss_cycle)
        cycle_position_cap_bottom_up = min(
            cycle_position_cap_top_down,
            _cycle_cap_ratio_bottom_up(mss_cycle),
        )

        raw_lookup_by_stock: dict[str, dict[str, object]] = {}
        raw_lookup_by_ts: dict[str, dict[str, object]] = {}
        if not raw_frame.empty:
            _rf = raw_frame.copy()
            _rf["_sk"] = _rf["stock_code"].astype(str).str.strip()
            _rf["_tk"] = _rf["ts_code"].astype(str).str.strip().str.upper() if "ts_code" in _rf.columns else ""
            _rf_sc = _rf[_rf["_sk"] != ""].drop_duplicates(subset="_sk", keep="first").set_index("_sk")
            raw_lookup_by_stock = _rf_sc.drop(columns=["_tk"], errors="ignore").to_dict("index")
            if "_tk" in _rf.columns:
                _rf_ts = _rf[_rf["_tk"] != ""].drop_duplicates(subset="_tk", keep="first").set_index("_tk")
                raw_lookup_by_ts = _rf_ts.drop(columns=["_sk"], errors="ignore").to_dict("index")

        pas_metrics = pas_frame.copy()
        if "opportunity_grade" not in pas_metrics.columns:
            pas_metrics["opportunity_grade"] = pas_metrics["pas_score"].map(_to_opportunity_grade)
        pas_metrics["opportunity_grade"] = (
            pas_metrics["opportunity_grade"].astype(str).str.strip().str.upper()
        )
        pas_metrics["stock_code_key"] = pas_metrics.apply(
            lambda row: _to_stock_code(
                str(row.get("stock_code", "")),
                str(row.get("ts_code", "")),
            ),
            axis=1,
        )
        pas_metrics["ts_code_key"] = pas_metrics["ts_code"].astype(str).str.strip().str.upper()
        # 向量化行业查找（消除 iterrows）
        def _lookup_industry(sc: str, ts: str) -> tuple[str, str]:
            t = stock_industry_by_stock.get(sc) or stock_industry_by_ts.get(ts)
            return t if t else ("UNKNOWN", "未知行业")

        _ind_pairs = [
            _lookup_industry(sc, ts)
            for sc, ts in zip(pas_metrics["stock_code_key"], pas_metrics["ts_code_key"])
        ]
        pas_metrics["industry_code"] = [p[0] for p in _ind_pairs]
        pas_metrics["industry_name"] = [p[1] for p in _ind_pairs]
        pas_metrics["is_sa"] = pas_metrics["opportunity_grade"].isin({"S", "A"})
        pas_sa_ratio = float(pas_metrics["is_sa"].mean()) if len(pas_metrics) > 0 else 0.0
        industry_sa_ratio_map = (
            pas_metrics.groupby("industry_code")["is_sa"].mean().to_dict()
            if len(pas_metrics) > 0
            else {}
        )

        # 主循环：使用 itertuples 替代 iterrows（消除性能瓶颈）
        _default_ic = str(default_irs_record.get("industry_code", "UNKNOWN"))
        _default_in = str(default_irs_record.get("industry_name", "未知行业"))
        _position_cap_warn = effective_gate == "WARN"
        _temp_extreme = mss_temperature < 30.0 or mss_temperature > 80.0

        # 主循环保留逐股决策语义，但读取侧已向量化（查找字典 + 预计算映射）。
        for tup in pas_frame.itertuples(index=False):
            risk_reward_ratio = float(getattr(tup, "risk_reward_ratio", 0.0) or 0.0)
            if risk_reward_ratio < 1.0:
                rr_filtered_count += 1
                continue

            stock_code = _to_stock_code(
                str(getattr(tup, "stock_code", "") or ""),
                str(getattr(tup, "ts_code", "") or ""),
            )
            ts_code = str(getattr(tup, "ts_code", "") or "").strip().upper()
            industry_tuple = stock_industry_by_stock.get(stock_code) or stock_industry_by_ts.get(ts_code)
            if industry_tuple:
                industry_code, industry_name = industry_tuple
            else:
                industry_code = _default_ic
                industry_name = _default_in
            irs_record = irs_by_industry.get(industry_code, default_irs_record)
            irs_score = float(irs_record.get("irs_score", 0.0))
            irs_recommendation = str(irs_record.get("recommendation", "HOLD"))
            allocation_advice = str(irs_record.get("allocation_advice", "")).strip()
            irs_direction = _direction_from_recommendation(irs_recommendation)
            industry_sa_ratio = float(industry_sa_ratio_map.get(industry_code, 0.0))

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

            pas_score = float(getattr(tup, "pas_score", 0.0) or 0.0)
            effective_pas_score = pas_score * (0.85 if allocation_advice == "回避" else 1.0)
            pas_direction = str(getattr(tup, "pas_direction", "neutral") or "neutral")
            if pas_direction not in {"bullish", "bearish", "neutral"}:
                pas_direction = "neutral"
            opportunity_grade = str(getattr(tup, "opportunity_grade", "") or "").strip().upper()
            if opportunity_grade not in {"S", "A", "B", "C", "D"}:
                opportunity_grade = _to_opportunity_grade(pas_score)

            top_down_score = round(
                mss_score * w_mss + irs_score * w_irs + effective_pas_score * w_pas,
                4,
            )
            bottom_up_score = (
                effective_pas_score * 0.70 + irs_score * 0.20 + mss_score * 0.10
            )
            if pas_sa_ratio >= 0.20:
                bottom_up_score *= 1.05
            if industry_sa_ratio >= 0.20:
                bottom_up_score *= 1.05
            if allocation_advice == "回避":
                bottom_up_score *= 0.90
            bottom_up_score = round(max(0.0, min(100.0, bottom_up_score)), 4)

            td_recommendation = _to_recommendation(top_down_score, mss_cycle)
            bu_recommendation = _to_recommendation(bottom_up_score, mss_cycle)
            td_direction = _direction_from_recommendation(td_recommendation)
            bu_direction = _direction_from_recommendation(bu_recommendation)

            if resolved_integration_mode == "top_down":
                final_score = top_down_score
                recommendation = td_recommendation
                mode_position_cap = cycle_position_cap_top_down
            elif resolved_integration_mode == "bottom_up":
                final_score = bottom_up_score
                recommendation = bu_recommendation
                mode_position_cap = cycle_position_cap_bottom_up
            elif resolved_integration_mode == "dual_verify":
                final_score = round((top_down_score + bottom_up_score) / 2.0, 4)
                recommendation = _to_recommendation(final_score, mss_cycle)
                if td_direction != bu_direction and td_direction != "neutral" and bu_direction != "neutral":
                    recommendation = "HOLD"
                mode_position_cap = min(cycle_position_cap_top_down, cycle_position_cap_bottom_up)
            else:  # complementary
                final_score = round(top_down_score * 0.40 + bottom_up_score * 0.60, 4)
                recommendation = _to_recommendation(final_score, mss_cycle)
                if td_direction != bu_direction and td_direction != "neutral" and bu_direction != "neutral":
                    recommendation = "HOLD"
                mode_position_cap = cycle_position_cap_top_down

            direction = _to_direction(mss_direction, irs_direction, pas_direction)
            consistency = _to_consistency(mss_direction, irs_direction, pas_direction)
            neutrality = round(max(0.0, min(1.0, 1.0 - abs(final_score - 50.0) / 50.0)), 4)

            base_position_size = max(0.0, min(1.0, final_score / 100.0))
            if _temp_extreme:
                base_position_size *= 0.85
            position_cap = min(position_cap_ratio, mode_position_cap)
            if _position_cap_warn:
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
                    "integration_mode": resolved_integration_mode,
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
    integrated_frame = _apply_recommendation_limits(integrated_frame)
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
        integration_mode=resolved_integration_mode,
        frame=integrated_frame,
        quality_status=quality_status,
        quality_frame=quality_frame,
        validation_gate=effective_gate,
        integration_state=integration_state,
        go_nogo=go_nogo,
        rr_filtered_count=rr_filtered_count,
        quality_message=quality_message,
    )
