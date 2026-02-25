from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config
from src.data.fetch_batch_pipeline import read_fetch_status
from src.db.helpers import column_exists as _table_has_column, table_exists as _table_exists

# DESIGN_TRACE:
# - Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md (§5 S3)
# - Governance/SpiralRoadmap/execution-cards/S3A-EXECUTION-CARD.md (§1 目标, §4 artifact)
# - Governance/SpiralRoadmap/execution-cards/S3-EXECUTION-CARD.md (§1 目标, §4 artifact)
# - Governance/SpiralRoadmap/execution-cards/S3R-EXECUTION-CARD.md (§2 run, §4 artifact)
# - docs/design/core-infrastructure/backtest/backtest-algorithm.md (§3 信号入口, §4 A股约束)
DESIGN_TRACE = {
    "s3a_s4b_roadmap": "Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md",
    "s3a_execution_card": "Governance/SpiralRoadmap/execution-cards/S3A-EXECUTION-CARD.md",
    "s3_execution_card": "Governance/SpiralRoadmap/execution-cards/S3-EXECUTION-CARD.md",
    "s3r_execution_card": "Governance/SpiralRoadmap/execution-cards/S3R-EXECUTION-CARD.md",
    "backtest_algorithm_design": "docs/design/core-infrastructure/backtest/backtest-algorithm.md",
}

SUPPORTED_ENGINE = {"qlib", "local_vectorized", "backtrader_compat"}
SUPPORTED_CONTRACT_VERSION = "nc-v1"
LIMIT_RATIO_MAIN_BOARD = 0.10
LIMIT_RATIO_GEM_STAR = 0.20
LIMIT_RATIO_ST = 0.05
LIMIT_PRICE_TOLERANCE_RATIO = 0.001
MIN_FILL_PROBABILITY = 0.35
QUEUE_PARTICIPATION_RATE = 0.15
LIQUIDITY_DRYUP_VOLUME_THRESHOLD = 50_000.0
LIQUIDITY_DRYUP_AMOUNT_THRESHOLD = 1_500_000.0
FEE_TIER_SMALL_NOTIONAL_THRESHOLD = 100_000.0
FEE_TIER_LARGE_NOTIONAL_THRESHOLD = 500_000.0
FEE_TIER_SMALL_MULTIPLIER = 1.15
FEE_TIER_MEDIUM_MULTIPLIER = 1.0
FEE_TIER_LARGE_MULTIPLIER = 0.90
IMPACT_MULTIPLIER_BY_LIQUIDITY_TIER = {"L1": 0.70, "L2": 1.00, "L3": 1.50}
LONG_ENTRY_RECOMMENDATIONS = {"STRONG_BUY", "BUY"}
CORE_SIGNAL_COLUMNS = ("mss_score", "irs_score", "pas_score")
WINDOW_TABLE_DATE_COLUMNS = {
    "raw_trade_cal": "trade_date",
    "raw_daily": "trade_date",
    "mss_panorama": "trade_date",
    "irs_industry_daily": "trade_date",
    "stock_pas_daily": "trade_date",
    "integrated_recommendation": "trade_date",
    "validation_weight_plan": "trade_date",
    "quality_gate_report": "trade_date",
}
CORE_INPUT_TABLES = ("mss_panorama", "irs_industry_daily", "stock_pas_daily")

BACKTEST_RESULT_COLUMNS = [
    "backtest_id",
    "engine",
    "start_date",
    "end_date",
    "quality_status",
    "go_nogo",
    "consumed_signal_rows",
    "total_trades",
    "win_rate",
    "total_return",
    "max_drawdown",
    "max_drawdown_days",
    "daily_return_mean",
    "daily_return_std",
    "daily_return_p05",
    "daily_return_p95",
    "daily_return_skew",
    "turnover_mean",
    "turnover_std",
    "turnover_cv",
    "commission_total",
    "stamp_tax_total",
    "transfer_fee_total",
    "impact_cost_total",
    "total_fee",
    "cost_bps",
    "impact_cost_ratio",
    "source_fetch_progress_path",
    "source_fetch_start_date",
    "source_fetch_end_date",
    "source_fetch_status",
    "bridge_check_status",
    "contract_version",
    "created_at",
]

BACKTEST_TRADE_COLUMNS = [
    "backtest_id",
    "trade_date",
    "signal_date",
    "execute_date",
    "stock_code",
    "direction",
    "filled_price",
    "shares",
    "amount",
    "pnl",
    "pnl_pct",
    "recommendation",
    "final_score",
    "risk_reward_ratio",
    "integration_mode",
    "weight_plan_id",
    "status",
    "reject_reason",
    "t1_restriction_hit",
    "limit_guard_result",
    "session_guard_result",
    "contract_version",
    "created_at",
]


@dataclass(frozen=True)
class BacktestRunResult:
    backtest_id: str
    engine: str
    start_date: str
    end_date: str
    artifacts_dir: Path
    backtest_results_path: Path
    backtest_trade_records_path: Path
    ab_metric_summary_path: Path
    performance_metrics_report_path: Path
    gate_report_path: Path
    consumption_path: Path
    error_manifest_path: Path
    consumed_signal_rows: int
    total_trades: int
    quality_status: str
    go_nogo: str
    bridge_check_status: str
    has_error: bool
    repair: str = ""
    s3r_patch_note_path: Path | None = None
    s3r_delta_report_path: Path | None = None


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_trade_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"invalid trade date: {value}; expected YYYYMMDD") from exc


def _validate_date_range(start_date: str, end_date: str) -> None:
    start_dt = _parse_trade_date(start_date)
    end_dt = _parse_trade_date(end_date)
    if end_dt < start_dt:
        raise ValueError(f"end date must be >= start date: start={start_date}, end={end_date}")


def _artifacts_dir(*, end_date: str, spiral_id: str = "s3") -> Path:
    return Path("artifacts") / f"spiral-{spiral_id}" / end_date


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_s3r_patch_note(
    *,
    path: Path,
    backtest_id: str,
    engine: str,
    start_date: str,
    end_date: str,
    quality_status: str,
    go_nogo: str,
) -> None:
    lines = [
        "# S3r Patch Note",
        "",
        f"- backtest_id: {backtest_id}",
        f"- engine: {engine}",
        f"- start_date: {start_date}",
        f"- end_date: {end_date}",
        "- repair_scope: backtest_gate_only",
        f"- quality_status_after_repair: {quality_status}",
        f"- go_nogo_after_repair: {go_nogo}",
        "- policy: only repair, no scope expansion",
        "",
    ]
    _write_markdown(path, lines)


def _write_s3r_delta_report(
    *,
    path: Path,
    consumed_signal_rows: int,
    total_trades: int,
    quality_status: str,
    go_nogo: str,
) -> None:
    lines = [
        "# S3r Delta Report",
        "",
        f"- consumed_signal_rows_after_repair: {consumed_signal_rows}",
        f"- total_trades_after_repair: {total_trades}",
        f"- quality_status_after_repair: {quality_status}",
        f"- go_nogo_after_repair: {go_nogo}",
        "- delta_summary: rerun backtest with S3r repair policy",
        "",
    ]
    _write_markdown(path, lines)


def _persist(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
    delete_key: str,
    delete_value: str,
) -> None:
    with duckdb.connect(str(database_path)) as connection:
        table_exists_row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()
        table_exists = bool(table_exists_row and int(table_exists_row[0]) > 0)

        if frame.empty:
            connection.register("incoming_df", frame)
            connection.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM incoming_df WHERE 1=0"
            )
            connection.unregister("incoming_df")
            if table_exists:
                has_delete_key = bool(
                    connection.execute(
                        "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = ? AND column_name = ?",
                        [table_name, delete_key],
                    ).fetchone()[0]
                )
                if has_delete_key:
                    connection.execute(f"DELETE FROM {table_name} WHERE {delete_key} = ?", [delete_value])
            return

        def quote_identifier(name: str) -> str:
            return '"' + str(name).replace('"', '""') + '"'

        connection.register("incoming_df", frame)
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM incoming_df WHERE 1=0"
        )

        table_columns = {
            str(row[1]): str(row[2]).strip().upper()
            for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        }
        incoming_columns = list(frame.columns)
        incoming_types = {
            str(row[0]): str(row[1]).strip().upper()
            for row in connection.execute("DESCRIBE incoming_df").fetchall()
        }

        for column_name in incoming_columns:
            if column_name in table_columns:
                continue
            column_type = incoming_types.get(column_name, "VARCHAR")
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {quote_identifier(column_name)} {column_type}"
            )

        table_columns = {
            str(row[1]): str(row[2]).strip().upper()
            for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        }
        if delete_key in table_columns:
            connection.execute(f"DELETE FROM {table_name} WHERE {delete_key} = ?", [delete_value])

        insert_columns = [column_name for column_name in incoming_columns if column_name in table_columns]
        if insert_columns:
            quoted_columns = ", ".join(quote_identifier(column_name) for column_name in insert_columns)
            connection.execute(
                f"INSERT INTO {table_name} ({quoted_columns}) SELECT {quoted_columns} FROM incoming_df"
            )
        connection.unregister("incoming_df")


def _empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _read_integrated_signals(
    *,
    database_path: Path,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'integrated_recommendation'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return _empty_frame(
                [
                    "trade_date",
                    "stock_code",
                    "final_score",
                    "recommendation",
                    "position_size",
                    "entry",
                    "risk_reward_ratio",
                    "integration_mode",
                    "weight_plan_id",
                    "contract_version",
                    "mss_score",
                    "irs_score",
                    "pas_score",
                ]
            )
        has_mss_score = _table_has_column(connection, "integrated_recommendation", "mss_score")
        has_irs_score = _table_has_column(connection, "integrated_recommendation", "irs_score")
        has_pas_score = _table_has_column(connection, "integrated_recommendation", "pas_score")
        mss_expr = "mss_score" if has_mss_score else "NULL AS mss_score"
        irs_expr = "irs_score" if has_irs_score else "NULL AS irs_score"
        pas_expr = "pas_score" if has_pas_score else "NULL AS pas_score"
        frame = connection.execute(
            "SELECT trade_date, stock_code, final_score, recommendation, position_size, entry, "
            "risk_reward_ratio, integration_mode, weight_plan_id, contract_version, "
            f"{mss_expr}, {irs_expr}, {pas_expr} "
            "FROM integrated_recommendation "
            "WHERE trade_date >= ? AND trade_date <= ? "
            "ORDER BY trade_date, final_score DESC, stock_code",
            [start_date, end_date],
        ).df()
    return frame


def _read_quality_gate(
    *,
    database_path: Path,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'quality_gate_report'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return _empty_frame(["trade_date", "status", "go_nogo", "message"])
        frame = connection.execute(
            "SELECT trade_date, status, go_nogo, message FROM quality_gate_report "
            "WHERE trade_date >= ? AND trade_date <= ? "
            "ORDER BY trade_date",
            [start_date, end_date],
        ).df()
    return frame


def _read_bridge_check(
    *,
    database_path: Path,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        integrated_exists = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'integrated_recommendation'"
        ).fetchone()
        plan_exists = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'validation_weight_plan'"
        ).fetchone()
        if (
            not integrated_exists
            or int(integrated_exists[0]) <= 0
            or not plan_exists
            or int(plan_exists[0]) <= 0
        ):
            return _empty_frame(
                ["trade_date", "stock_code", "weight_plan_id", "matched_plan_id"]
            )
        frame = connection.execute(
            "SELECT ir.trade_date, ir.stock_code, ir.weight_plan_id, vp.plan_id AS matched_plan_id "
            "FROM integrated_recommendation ir "
            "LEFT JOIN validation_weight_plan vp "
            "ON ir.trade_date = vp.trade_date AND ir.weight_plan_id = vp.plan_id "
            "WHERE ir.trade_date >= ? AND ir.trade_date <= ? "
            "ORDER BY ir.trade_date, ir.stock_code",
            [start_date, end_date],
        ).df()
    return frame


def _to_quality_status(gate_frame: pd.DataFrame) -> tuple[str, str, str]:
    if gate_frame.empty:
        return ("FAIL", "NO_GO", "quality_gate_report_missing")
    statuses = {str(item).upper() for item in gate_frame["status"].tolist()}
    if "FAIL" in statuses:
        return ("FAIL", "NO_GO", "quality_gate_fail")
    if "WARN" in statuses:
        return ("WARN", "GO", "quality_gate_warn")
    if statuses <= {"PASS"}:
        return ("PASS", "GO", "quality_gate_pass")
    return ("FAIL", "NO_GO", "quality_gate_status_invalid")


def _filter_quality_gate_by_signal_dates(
    *,
    gate_frame: pd.DataFrame,
    integrated_frame: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    if gate_frame.empty or integrated_frame.empty:
        return (gate_frame, [])
    if "trade_date" not in gate_frame.columns or "trade_date" not in integrated_frame.columns:
        return (gate_frame, [])

    signal_dates = {
        str(item).strip()
        for item in integrated_frame["trade_date"].tolist()
        if str(item).strip()
    }
    if not signal_dates:
        return (gate_frame, [])

    filtered_gate = gate_frame[
        gate_frame["trade_date"].astype(str).str.strip().isin(signal_dates)
    ].copy()
    gate_dates = {
        str(item).strip()
        for item in filtered_gate["trade_date"].tolist()
        if str(item).strip()
    }
    missing_gate_dates = sorted(signal_dates - gate_dates)
    return (filtered_gate, missing_gate_dates)


def _read_trading_days(*, database_path: Path, start_date: str, end_date: str) -> list[str]:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'raw_trade_cal'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return []
        frame = connection.execute(
            "SELECT DISTINCT trade_date "
            "FROM raw_trade_cal "
            "WHERE trade_date >= ? AND trade_date <= ? AND CAST(is_open AS INTEGER) = 1 "
            "ORDER BY trade_date",
            [start_date, end_date],
        ).df()
    return [str(item) for item in frame["trade_date"].tolist()]




def _read_window_table_counts(
    *,
    database_path: Path,
    start_date: str,
    end_date: str,
) -> dict[str, int]:
    counts = {name: 0 for name in WINDOW_TABLE_DATE_COLUMNS}
    with duckdb.connect(str(database_path), read_only=True) as connection:
        for table_name, date_column in WINDOW_TABLE_DATE_COLUMNS.items():
            if not _table_exists(connection, table_name):
                continue
            if not _table_has_column(connection, table_name, date_column):
                continue
            row = connection.execute(
                f"SELECT COUNT(*) FROM {table_name} WHERE {date_column} >= ? AND {date_column} <= ?",
                [start_date, end_date],
            ).fetchone()
            counts[table_name] = int(row[0]) if row else 0
    return counts


def _check_core_signal_columns(integrated_frame: pd.DataFrame) -> list[str]:
    violations: list[str] = []
    for column_name in CORE_SIGNAL_COLUMNS:
        if column_name not in integrated_frame.columns:
            violations.append(f"integrated_recommendation_column_missing_{column_name}")
            continue
        series = pd.to_numeric(integrated_frame[column_name], errors="coerce")
        if series.isna().any():
            violations.append(f"integrated_recommendation_column_null_{column_name}")
    return violations


def _read_stock_profiles(*, database_path: Path) -> dict[str, dict[str, str]]:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'raw_stock_basic'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return {}

        has_stock_code = _table_has_column(connection, "raw_stock_basic", "stock_code")
        has_ts_code = _table_has_column(connection, "raw_stock_basic", "ts_code")
        has_name = _table_has_column(connection, "raw_stock_basic", "name")
        if not has_stock_code and not has_ts_code:
            return {}

        if has_stock_code and has_ts_code:
            stock_code_expr = "COALESCE(NULLIF(stock_code, ''), SPLIT_PART(ts_code, '.', 1))"
        elif has_stock_code:
            stock_code_expr = "stock_code"
        else:
            stock_code_expr = "SPLIT_PART(ts_code, '.', 1)"

        name_expr = "name" if has_name else "''"
        frame = connection.execute(
            f"SELECT {stock_code_expr} AS stock_code, {name_expr} AS stock_name "
            "FROM raw_stock_basic"
        ).df()

    profiles: dict[str, dict[str, str]] = {}
    for _, row in frame.iterrows():
        stock_code = str(row.get("stock_code", "")).strip()
        if not stock_code:
            continue
        profiles[stock_code] = {"stock_name": str(row.get("stock_name", "")).strip()}
    return profiles


def _next_trade_day(trading_days: list[str], trade_date: str) -> str | None:
    for day in trading_days:
        if day > trade_date:
            return day
    return None


def _read_price_frame(
    *, database_path: Path, start_date: str, end_date: str
) -> pd.DataFrame:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'raw_daily'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return _empty_frame(["trade_date", "stock_code", "open", "high", "low", "close", "vol", "amount"])
        has_vol = _table_has_column(connection, "raw_daily", "vol")
        has_amount = _table_has_column(connection, "raw_daily", "amount")
        vol_expr = "vol" if has_vol else "0.0 AS vol"
        amount_expr = "amount" if has_amount else "0.0 AS amount"
        frame = connection.execute(
            "SELECT trade_date, "
            "COALESCE(NULLIF(stock_code, ''), SPLIT_PART(ts_code, '.', 1)) AS stock_code, "
            f"open, high, low, close, {vol_expr}, {amount_expr} "
            "FROM raw_daily "
            "WHERE trade_date >= ? AND trade_date <= ? "
            "ORDER BY trade_date, stock_code",
            [start_date, end_date],
        ).df()
    return frame


def _build_price_lookup(price_frame: pd.DataFrame) -> dict[tuple[str, str], dict[str, float]]:
    lookup: dict[tuple[str, str], dict[str, float]] = {}
    for _, row in price_frame.iterrows():
        trade_date = str(row.get("trade_date", ""))
        stock_code = str(row.get("stock_code", ""))
        lookup[(trade_date, stock_code)] = {
            "open": float(row.get("open", 0.0) or 0.0),
            "high": float(row.get("high", 0.0) or 0.0),
            "low": float(row.get("low", 0.0) or 0.0),
            "close": float(row.get("close", 0.0) or 0.0),
            "vol": float(row.get("vol", 0.0) or 0.0),
            "amount": float(row.get("amount", 0.0) or 0.0),
        }
    return lookup


def _build_prev_close_lookup(price_frame: pd.DataFrame) -> dict[tuple[str, str], float]:
    if price_frame.empty:
        return {}
    working = price_frame.copy()
    working["trade_date"] = working["trade_date"].astype(str)
    working["stock_code"] = working["stock_code"].astype(str)
    working["close"] = pd.to_numeric(working["close"], errors="coerce").fillna(0.0)
    working = working.sort_values(by=["stock_code", "trade_date"])
    working["prev_close"] = working.groupby("stock_code")["close"].shift(1)

    lookup: dict[tuple[str, str], float] = {}
    for _, row in working.iterrows():
        stock_code = str(row.get("stock_code", "")).strip()
        trade_date = str(row.get("trade_date", "")).strip()
        prev_close = float(row.get("prev_close", 0.0) or 0.0)
        if not stock_code or not trade_date or prev_close <= 0.0:
            continue
        lookup[(trade_date, stock_code)] = prev_close
    return lookup


def _resolve_limit_ratio(*, stock_code: str, stock_name: str) -> float:
    normalized_name = str(stock_name).upper()
    if "ST" in normalized_name:
        return LIMIT_RATIO_ST

    normalized_code = str(stock_code).strip()
    if normalized_code.startswith(("300", "301", "688", "689")):
        return LIMIT_RATIO_GEM_STAR
    return LIMIT_RATIO_MAIN_BOARD


def _price_tolerance(limit_price: float) -> float:
    return max(0.01, abs(limit_price) * LIMIT_PRICE_TOLERANCE_RATIO)


def _is_limit_up(*, price: dict[str, float], prev_close: float | None, limit_ratio: float) -> bool:
    open_price = float(price.get("open", 0.0))
    high_price = float(price.get("high", 0.0))
    if open_price <= 0.0 or high_price <= 0.0:
        return False
    if prev_close is not None and prev_close > 0.0 and limit_ratio > 0.0:
        limit_price = prev_close * (1.0 + limit_ratio)
        tolerance = _price_tolerance(limit_price)
        return open_price >= (limit_price - tolerance) and high_price >= (limit_price - tolerance)
    return open_price >= high_price * 0.999


def _is_limit_down(*, price: dict[str, float], prev_close: float | None, limit_ratio: float) -> bool:
    open_price = float(price.get("open", 0.0))
    low_price = float(price.get("low", 0.0))
    if open_price <= 0.0 or low_price <= 0.0:
        return False
    if prev_close is not None and prev_close > 0.0 and limit_ratio > 0.0:
        limit_price = prev_close * (1.0 - limit_ratio)
        tolerance = _price_tolerance(limit_price)
        return open_price <= (limit_price + tolerance) and low_price <= (limit_price + tolerance)
    return open_price <= low_price * 1.001


def _clip(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def _is_one_word_board(price: dict[str, float]) -> bool:
    open_price = float(price.get("open", 0.0) or 0.0)
    high_price = float(price.get("high", 0.0) or 0.0)
    low_price = float(price.get("low", 0.0) or 0.0)
    if open_price <= 0.0 or high_price <= 0.0 or low_price <= 0.0:
        return False
    epsilon = max(0.001, high_price * 0.0005)
    return (
        abs(high_price - low_price) <= epsilon
        and abs(open_price - high_price) <= epsilon
        and abs(open_price - low_price) <= epsilon
    )


def _resolve_liquidity_tier(volume: float) -> str:
    if volume >= 1_000_000.0:
        return "L1"
    if volume >= 200_000.0:
        return "L2"
    return "L3"


def _estimate_turnover(price: dict[str, float]) -> float:
    volume = max(0.0, float(price.get("vol", 0.0) or 0.0))
    amount = max(0.0, float(price.get("amount", 0.0) or 0.0))
    ref_price = float(price.get("close", 0.0) or 0.0)
    if ref_price <= 0.0:
        ref_price = float(price.get("open", 0.0) or 0.0)
    implied_amount = volume * max(0.0, ref_price)
    return max(amount, implied_amount)


def _is_liquidity_dryup(price: dict[str, float]) -> bool:
    volume = max(0.0, float(price.get("vol", 0.0) or 0.0))
    turnover = _estimate_turnover(price)
    return (
        volume < LIQUIDITY_DRYUP_VOLUME_THRESHOLD
        or turnover < LIQUIDITY_DRYUP_AMOUNT_THRESHOLD
    )


def _resolve_fee_tier(notional: float) -> tuple[str, float]:
    value = max(0.0, float(notional))
    if value <= FEE_TIER_SMALL_NOTIONAL_THRESHOLD:
        return ("S", FEE_TIER_SMALL_MULTIPLIER)
    if value >= FEE_TIER_LARGE_NOTIONAL_THRESHOLD:
        return ("L", FEE_TIER_LARGE_MULTIPLIER)
    return ("M", FEE_TIER_MEDIUM_MULTIPLIER)


def _resolve_impact_multiplier(liquidity_tier: str) -> float:
    return float(IMPACT_MULTIPLIER_BY_LIQUIDITY_TIER.get(str(liquidity_tier), 1.0))


def _estimate_impact_cost(
    *,
    price: dict[str, float],
    order_shares: int,
    amount: float,
    slippage_rate: float,
) -> tuple[float, str, float]:
    normalized_amount = max(0.0, float(amount))
    if normalized_amount <= 0.0:
        return (0.0, "L3", 0.0)
    volume = max(0.0, float(price.get("vol", 0.0) or 0.0))
    liquidity_tier = _resolve_liquidity_tier(volume)
    queue_capacity = max(1.0, volume * QUEUE_PARTICIPATION_RATE)
    queue_ratio = min(1.0, max(0.0, float(order_shares)) / queue_capacity)
    impact_multiplier = _resolve_impact_multiplier(liquidity_tier)
    base_slippage = max(0.0, float(slippage_rate))
    impact_cost = normalized_amount * base_slippage * impact_multiplier * (0.5 + queue_ratio)
    return (round(float(impact_cost), 6), str(liquidity_tier), round(float(queue_ratio), 8))


def _estimate_fill(
    *, price: dict[str, float], order_shares: int
) -> tuple[float, float, str]:
    if order_shares <= 0:
        return (0.0, 0.0, "L3")
    volume = max(0.0, float(price.get("vol", 0.0) or 0.0))
    liquidity_tier = _resolve_liquidity_tier(volume)
    if volume <= 0.0:
        return (0.0, 0.0, liquidity_tier)
    if _is_one_word_board(price):
        return (0.0, 0.0, liquidity_tier)
    queue_capacity = max(1.0, volume * QUEUE_PARTICIPATION_RATE)
    queue_ratio = min(1.0, float(order_shares) / queue_capacity)
    fill_probability = _clip(1.0 - queue_ratio, 0.0, 1.0)
    fill_ratio = _clip(1.0 - 0.50 * queue_ratio, 0.0, 1.0)
    return (fill_probability, fill_ratio, liquidity_tier)


def _compute_max_drawdown_days(equity_curve: list[float]) -> int:
    if not equity_curve:
        return 0
    peak = float(equity_curve[0])
    current_drawdown_days = 0
    max_drawdown_days = 0
    for equity in equity_curve:
        value = float(equity)
        if value >= peak:
            peak = value
            current_drawdown_days = 0
            continue
        current_drawdown_days += 1
        if current_drawdown_days > max_drawdown_days:
            max_drawdown_days = current_drawdown_days
    return int(max_drawdown_days)


def _compute_daily_return_distribution(equity_curve: list[float]) -> dict[str, float]:
    if len(equity_curve) <= 1:
        return {
            "daily_return_mean": 0.0,
            "daily_return_std": 0.0,
            "daily_return_p05": 0.0,
            "daily_return_p95": 0.0,
            "daily_return_skew": 0.0,
        }
    series = pd.Series(equity_curve, dtype=float)
    daily_returns = series.pct_change().replace([float("inf"), float("-inf")], 0.0).fillna(0.0).iloc[1:]
    if daily_returns.empty:
        return {
            "daily_return_mean": 0.0,
            "daily_return_std": 0.0,
            "daily_return_p05": 0.0,
            "daily_return_p95": 0.0,
            "daily_return_skew": 0.0,
        }
    skew_value = float(daily_returns.skew()) if len(daily_returns) >= 3 else 0.0
    if pd.isna(skew_value):
        skew_value = 0.0
    return {
        "daily_return_mean": round(float(daily_returns.mean()), 8),
        "daily_return_std": round(float(daily_returns.std(ddof=0)), 8),
        "daily_return_p05": round(float(daily_returns.quantile(0.05)), 8),
        "daily_return_p95": round(float(daily_returns.quantile(0.95)), 8),
        "daily_return_skew": round(skew_value, 8),
    }


def _compute_turnover_stability(
    *,
    trade_frame: pd.DataFrame,
    replay_days: list[str],
    initial_cash: float,
) -> dict[str, float]:
    if initial_cash <= 0.0 or not replay_days:
        return {
            "turnover_mean": 0.0,
            "turnover_std": 0.0,
            "turnover_cv": 0.0,
        }
    if trade_frame.empty:
        return {
            "turnover_mean": 0.0,
            "turnover_std": 0.0,
            "turnover_cv": 0.0,
        }
    filled = trade_frame[trade_frame["status"] == "filled"].copy()
    if filled.empty:
        return {
            "turnover_mean": 0.0,
            "turnover_std": 0.0,
            "turnover_cv": 0.0,
        }
    filled["amount"] = pd.to_numeric(filled["amount"], errors="coerce").fillna(0.0)
    turnover_by_day = (
        filled.groupby("trade_date")["amount"].sum().reindex(replay_days, fill_value=0.0).astype(float)
        / max(1.0, initial_cash)
    )
    turnover_mean = float(turnover_by_day.mean()) if not turnover_by_day.empty else 0.0
    turnover_std = float(turnover_by_day.std(ddof=0)) if not turnover_by_day.empty else 0.0
    turnover_cv = turnover_std / max(1e-12, abs(turnover_mean)) if turnover_mean > 0.0 else 0.0
    return {
        "turnover_mean": round(turnover_mean, 8),
        "turnover_std": round(turnover_std, 8),
        "turnover_cv": round(turnover_cv, 8),
    }


def run_backtest(
    *,
    start_date: str,
    end_date: str,
    engine: str,
    repair: str = "",
    config: Config,
) -> BacktestRunResult:
    _validate_date_range(start_date, end_date)
    normalized_engine = str(engine).strip()
    if normalized_engine not in SUPPORTED_ENGINE:
        raise ValueError(
            f"unsupported engine: {normalized_engine}; allowed={sorted(SUPPORTED_ENGINE)}"
        )
    repair_mode = str(repair or "").strip().lower()
    if repair_mode and repair_mode != "s3r":
        raise ValueError(f"unsupported repair mode: {repair_mode}")

    spiral_id = "s3r" if repair_mode == "s3r" else "s3"
    artifacts_dir = _artifacts_dir(end_date=end_date, spiral_id=spiral_id)
    id_prefix = "BTR" if repair_mode == "s3r" else "BT"
    backtest_id = f"{id_prefix}_{start_date}_{end_date}_{normalized_engine}"
    backtest_results_path = artifacts_dir / "backtest_results.parquet"
    backtest_trade_records_path = artifacts_dir / "backtest_trade_records.parquet"
    ab_metric_summary_path = artifacts_dir / "ab_metric_summary.md"
    performance_metrics_report_path = artifacts_dir / "performance_metrics_report.md"
    gate_report_path = artifacts_dir / "gate_report.md"
    consumption_path = artifacts_dir / "consumption.md"
    error_manifest_path = artifacts_dir / "error_manifest_sample.json"

    errors: list[dict[str, str]] = []
    warnings: list[str] = []

    def add_error(level: str, step: str, message: str) -> None:
        errors.append(
            {
                "error_level": level,
                "step": step,
                "start_date": start_date,
                "end_date": end_date,
                "message": message,
            }
        )

    def add_warning(message: str) -> None:
        warnings.append(str(message))

    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not database_path.exists():
        add_error("P0", "database", "duckdb_not_found")
    window_table_counts = {name: 0 for name in WINDOW_TABLE_DATE_COLUMNS}
    if database_path.exists():
        window_table_counts = _read_window_table_counts(
            database_path=database_path,
            start_date=start_date,
            end_date=end_date,
        )
    has_local_l1_window_coverage = (
        int(window_table_counts.get("raw_trade_cal", 0)) > 0
        and int(window_table_counts.get("raw_daily", 0)) > 0
    )

    fetch_status = read_fetch_status(config=config)
    if fetch_status.status != "completed":
        if has_local_l1_window_coverage:
            add_warning("fetch_progress_not_completed_but_local_l1_covered")
        else:
            add_error("P0", "s3a_consumption", "fetch_progress_not_completed")
    elif (
        fetch_status.start_date > start_date
        or fetch_status.end_date < end_date
    ):
        if has_local_l1_window_coverage:
            add_warning("fetch_progress_range_not_cover_backtest_window_but_local_l1_covered")
        else:
            add_error("P0", "s3a_consumption", "fetch_progress_range_not_cover_backtest_window")

    integrated_frame = _empty_frame(
        [
            "trade_date",
            "stock_code",
            "final_score",
            "recommendation",
            "position_size",
            "entry",
            "risk_reward_ratio",
            "integration_mode",
            "weight_plan_id",
            "contract_version",
            "mss_score",
            "irs_score",
            "pas_score",
        ]
    )
    gate_frame = _empty_frame(["trade_date", "status", "go_nogo", "message"])
    bridge_frame = _empty_frame(["trade_date", "stock_code", "weight_plan_id", "matched_plan_id"])

    if not errors:
        integrated_frame = _read_integrated_signals(
            database_path=database_path,
            start_date=start_date,
            end_date=end_date,
        )
        gate_frame = _read_quality_gate(
            database_path=database_path,
            start_date=start_date,
            end_date=end_date,
        )
        bridge_frame = _read_bridge_check(
            database_path=database_path,
            start_date=start_date,
            end_date=end_date,
        )

        if integrated_frame.empty:
            add_error("P0", "signal_input", "integrated_recommendation_empty")
        else:
            invalid_contract = integrated_frame[
                integrated_frame["contract_version"] != SUPPORTED_CONTRACT_VERSION
            ]
            if not invalid_contract.empty:
                add_error("P0", "contract", "integrated_recommendation_contract_version_mismatch")

            rr_filtered = integrated_frame[integrated_frame["risk_reward_ratio"] < 1.0]
            if not rr_filtered.empty:
                add_error("P0", "contract", "integrated_recommendation_rr_below_threshold")
            for violation in _check_core_signal_columns(integrated_frame):
                add_error("P0", "contract", violation)
            for table_name in CORE_INPUT_TABLES:
                if int(window_table_counts.get(table_name, 0)) <= 0:
                    add_error("P0", "signal_input", f"{table_name}_missing_for_backtest_window")

        gate_frame, missing_gate_dates = _filter_quality_gate_by_signal_dates(
            gate_frame=gate_frame,
            integrated_frame=integrated_frame,
        )
        if missing_gate_dates:
            add_error("P0", "quality_gate", "quality_gate_missing_for_integrated_signal_dates")

        quality_status, go_nogo, quality_message = _to_quality_status(gate_frame)
        if quality_status == "FAIL":
            add_error("P0", "quality_gate", quality_message)

        if bridge_frame.empty:
            add_error("P0", "bridge", "validation_weight_plan_bridge_missing")
        else:
            invalid_baseline = bridge_frame[
                bridge_frame["weight_plan_id"].astype(str).isin(["", "baseline"])
            ]
            if not invalid_baseline.empty:
                add_error("P0", "bridge", "weight_plan_id_baseline_not_allowed_for_s3")

            missing_bridge = bridge_frame[bridge_frame["matched_plan_id"].isna()]
            if not missing_bridge.empty:
                add_error("P0", "bridge", "validation_weight_plan_bridge_unresolved")

    created_at = _utc_now_text()
    trade_rows: list[dict[str, object]] = []
    max_position_pct = float(config.backtest_max_position_pct)
    initial_cash = float(config.backtest_initial_cash)
    cash = initial_cash
    equity_curve: list[float] = [initial_cash]
    replay_days: list[str] = []

    limit_up_blocked_count = 0
    limit_down_blocked_count = 0
    one_word_board_blocked_count = 0
    liquidity_dryup_blocked_count = 0
    t1_guard_blocked_count = 0
    low_fill_prob_blocked_count = 0
    zero_fill_blocked_count = 0
    missing_price_entry_count = 0
    missing_price_exit_count = 0
    signal_out_of_window_count = 0

    if not errors:
        replay_days = _read_trading_days(
            database_path=database_path,
            start_date=start_date,
            end_date=end_date,
        )
        if not replay_days:
            add_error("P0", "calendar", "raw_trade_cal_open_days_missing")

    price_lookup: dict[tuple[str, str], dict[str, float]] = {}
    prev_close_lookup: dict[tuple[str, str], float] = {}
    stock_profile_lookup: dict[str, dict[str, str]] = {}
    if not errors:
        price_frame = _read_price_frame(
            database_path=database_path,
            start_date=start_date,
            end_date=end_date,
        )
        price_lookup = _build_price_lookup(price_frame)
        prev_close_lookup = _build_prev_close_lookup(price_frame)
        stock_profile_lookup = _read_stock_profiles(database_path=database_path)
        if not price_lookup:
            add_error("P0", "market_data", "raw_daily_missing_for_backtest_window")

    def calc_fees(amount: float, direction: str) -> tuple[float, float, float, float]:
        fee_tier_label, fee_tier_multiplier = _resolve_fee_tier(amount)
        commission = max(
            float(config.backtest_min_commission),
            amount * float(config.backtest_commission_rate) * fee_tier_multiplier,
        )
        stamp_tax = amount * float(config.backtest_stamp_duty_rate) if direction == "sell" else 0.0
        transfer_fee = amount * float(config.backtest_transfer_fee_rate)
        total_fee = commission + stamp_tax + transfer_fee
        return (
            round(commission, 6),
            round(stamp_tax, 6),
            round(transfer_fee, 6),
            round(total_fee, 6),
            fee_tier_label,
        )

    fee_tier_counts = {"S": 0, "M": 0, "L": 0}
    liquidity_tier_counts = {"L1": 0, "L2": 0, "L3": 0}
    commission_total = 0.0
    stamp_tax_total = 0.0
    transfer_fee_total = 0.0
    impact_cost_total = 0.0
    executed_notional_total = 0.0

    positions: dict[str, dict[str, object]] = {}
    signals_by_execute_date: dict[str, list[dict[str, object]]] = {}
    long_entry_signal_count = 0
    mapped_long_entry_signal_count = 0
    if not errors:
        for _, row in integrated_frame.iterrows():
            recommendation = str(row.get("recommendation", "")).strip().upper()
            if recommendation not in LONG_ENTRY_RECOMMENDATIONS:
                continue
            position_size = float(row.get("position_size", 0.0) or 0.0)
            if position_size <= 0.0:
                continue
            long_entry_signal_count += 1
            signal_date = str(row.get("trade_date", ""))
            execute_date = _next_trade_day(replay_days, signal_date)
            if execute_date is None or execute_date > end_date:
                signal_out_of_window_count += 1
                continue
            mapped_long_entry_signal_count += 1
            signals_by_execute_date.setdefault(execute_date, []).append(row.to_dict())

        for replay_day in replay_days:
            # 1) Sell positions first if T+1 unlock reached.
            for stock_code, pos in list(positions.items()):
                can_sell_date = str(pos.get("can_sell_date", replay_day))
                if replay_day < can_sell_date:
                    continue

                price = price_lookup.get((replay_day, stock_code))
                if not price:
                    missing_price_exit_count += 1
                    continue
                stock_name = str(stock_profile_lookup.get(stock_code, {}).get("stock_name", "")).strip()
                limit_ratio = _resolve_limit_ratio(stock_code=stock_code, stock_name=stock_name)
                prev_close = prev_close_lookup.get((replay_day, stock_code))
                if _is_limit_down(price=price, prev_close=prev_close, limit_ratio=limit_ratio):
                    limit_down_blocked_count += 1
                    continue

                filled_price = float(price.get("open", 0.0) or 0.0)
                if filled_price <= 0.0:
                    filled_price = float(price.get("close", 0.0) or 0.0)
                if filled_price <= 0.0:
                    missing_price_exit_count += 1
                    continue

                shares = int(pos.get("shares", 0))
                amount = round(filled_price * shares, 4)
                (
                    commission,
                    stamp_tax,
                    transfer_fee,
                    total_fee,
                    fee_tier_label,
                ) = calc_fees(amount, "sell")
                impact_cost, liquidity_tier, _ = _estimate_impact_cost(
                    price=price,
                    order_shares=shares,
                    amount=amount,
                    slippage_rate=float(config.backtest_slippage_value),
                )
                total_fee = round(total_fee + impact_cost, 6)
                cash = round(cash + amount - total_fee, 4)
                buy_amount = float(pos.get("buy_amount", 0.0) or 0.0)
                buy_fee = float(pos.get("buy_fee", 0.0) or 0.0)
                pnl = round(amount - total_fee - buy_amount - buy_fee, 4)
                denominator = max(1.0, buy_amount + buy_fee)
                pnl_pct = round(pnl / denominator, 8)

                trade_rows.append(
                    {
                        "backtest_id": backtest_id,
                        "trade_date": replay_day,
                        "signal_date": str(pos.get("signal_date", replay_day)),
                        "execute_date": replay_day,
                        "stock_code": stock_code,
                        "direction": "sell",
                        "filled_price": round(filled_price, 4),
                        "shares": shares,
                        "amount": amount,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "recommendation": str(pos.get("recommendation", "HOLD")),
                        "final_score": round(float(pos.get("final_score", 50.0) or 50.0), 4),
                        "risk_reward_ratio": round(
                            float(pos.get("risk_reward_ratio", 0.0) or 0.0), 4
                        ),
                        "integration_mode": str(pos.get("integration_mode", "top_down")),
                        "weight_plan_id": str(pos.get("weight_plan_id", "")),
                        "status": "filled",
                        "reject_reason": "",
                        "t1_restriction_hit": False,
                        "limit_guard_result": "PASS",
                        "session_guard_result": "PASS",
                        "contract_version": str(pos.get("contract_version", SUPPORTED_CONTRACT_VERSION)),
                        "created_at": created_at,
                    }
                )
                commission_total += commission
                stamp_tax_total += stamp_tax
                transfer_fee_total += transfer_fee
                impact_cost_total += impact_cost
                executed_notional_total += amount
                fee_tier_counts[fee_tier_label] = fee_tier_counts.get(fee_tier_label, 0) + 1
                liquidity_tier_counts[liquidity_tier] = liquidity_tier_counts.get(liquidity_tier, 0) + 1
                del positions[stock_code]

            # 2) Execute buys mapped from signal_date -> execute_date(T+1).
            for signal in signals_by_execute_date.get(replay_day, []):
                stock_code = str(signal.get("stock_code", ""))
                if not stock_code:
                    continue
                if stock_code in positions:
                    t1_guard_blocked_count += 1
                    continue

                price = price_lookup.get((replay_day, stock_code))
                if not price:
                    missing_price_entry_count += 1
                    trade_rows.append(
                        {
                            "backtest_id": backtest_id,
                            "trade_date": replay_day,
                            "signal_date": str(signal.get("trade_date", replay_day)),
                            "execute_date": replay_day,
                            "stock_code": stock_code,
                            "direction": "buy",
                            "filled_price": 0.0,
                            "shares": 0,
                            "amount": 0.0,
                            "pnl": 0.0,
                            "pnl_pct": 0.0,
                            "recommendation": str(signal.get("recommendation", "HOLD")),
                            "final_score": round(float(signal.get("final_score", 50.0) or 50.0), 4),
                            "risk_reward_ratio": round(
                                float(signal.get("risk_reward_ratio", 0.0) or 0.0), 4
                            ),
                            "integration_mode": str(signal.get("integration_mode", "top_down")),
                            "weight_plan_id": str(signal.get("weight_plan_id", "")),
                            "status": "rejected",
                            "reject_reason": "REJECT_NO_MARKET_PRICE",
                            "t1_restriction_hit": False,
                            "limit_guard_result": "UNKNOWN",
                            "session_guard_result": "FAIL_NO_PRICE",
                            "contract_version": str(signal.get("contract_version", "")),
                            "created_at": created_at,
                        }
                    )
                    continue
                stock_name = str(stock_profile_lookup.get(stock_code, {}).get("stock_name", "")).strip()
                limit_ratio = _resolve_limit_ratio(stock_code=stock_code, stock_name=stock_name)
                prev_close = prev_close_lookup.get((replay_day, stock_code))
                if _is_one_word_board(price):
                    one_word_board_blocked_count += 1
                    trade_rows.append(
                        {
                            "backtest_id": backtest_id,
                            "trade_date": replay_day,
                            "signal_date": str(signal.get("trade_date", replay_day)),
                            "execute_date": replay_day,
                            "stock_code": stock_code,
                            "direction": "buy",
                            "filled_price": 0.0,
                            "shares": 0,
                            "amount": 0.0,
                            "pnl": 0.0,
                            "pnl_pct": 0.0,
                            "recommendation": str(signal.get("recommendation", "HOLD")),
                            "final_score": round(float(signal.get("final_score", 50.0) or 50.0), 4),
                            "risk_reward_ratio": round(
                                float(signal.get("risk_reward_ratio", 0.0) or 0.0), 4
                            ),
                            "integration_mode": str(signal.get("integration_mode", "top_down")),
                            "weight_plan_id": str(signal.get("weight_plan_id", "")),
                            "status": "rejected",
                            "reject_reason": "REJECT_ONE_WORD_BOARD",
                            "t1_restriction_hit": False,
                            "limit_guard_result": "PASS",
                            "session_guard_result": "PASS",
                            "contract_version": str(signal.get("contract_version", "")),
                            "created_at": created_at,
                        }
                    )
                    continue
                if _is_limit_up(price=price, prev_close=prev_close, limit_ratio=limit_ratio):
                    limit_up_blocked_count += 1
                    trade_rows.append(
                        {
                            "backtest_id": backtest_id,
                            "trade_date": replay_day,
                            "signal_date": str(signal.get("trade_date", replay_day)),
                            "execute_date": replay_day,
                            "stock_code": stock_code,
                            "direction": "buy",
                            "filled_price": 0.0,
                            "shares": 0,
                            "amount": 0.0,
                            "pnl": 0.0,
                            "pnl_pct": 0.0,
                            "recommendation": str(signal.get("recommendation", "HOLD")),
                            "final_score": round(float(signal.get("final_score", 50.0) or 50.0), 4),
                            "risk_reward_ratio": round(
                                float(signal.get("risk_reward_ratio", 0.0) or 0.0), 4
                            ),
                            "integration_mode": str(signal.get("integration_mode", "top_down")),
                            "weight_plan_id": str(signal.get("weight_plan_id", "")),
                            "status": "rejected",
                            "reject_reason": "REJECT_LIMIT_UP",
                            "t1_restriction_hit": False,
                            "limit_guard_result": "REJECT_LIMIT_UP",
                            "session_guard_result": "PASS",
                            "contract_version": str(signal.get("contract_version", "")),
                            "created_at": created_at,
                        }
                    )
                    continue
                if _is_liquidity_dryup(price):
                    liquidity_dryup_blocked_count += 1
                    trade_rows.append(
                        {
                            "backtest_id": backtest_id,
                            "trade_date": replay_day,
                            "signal_date": str(signal.get("trade_date", replay_day)),
                            "execute_date": replay_day,
                            "stock_code": stock_code,
                            "direction": "buy",
                            "filled_price": 0.0,
                            "shares": 0,
                            "amount": 0.0,
                            "pnl": 0.0,
                            "pnl_pct": 0.0,
                            "recommendation": str(signal.get("recommendation", "HOLD")),
                            "final_score": round(float(signal.get("final_score", 50.0) or 50.0), 4),
                            "risk_reward_ratio": round(
                                float(signal.get("risk_reward_ratio", 0.0) or 0.0), 4
                            ),
                            "integration_mode": str(signal.get("integration_mode", "top_down")),
                            "weight_plan_id": str(signal.get("weight_plan_id", "")),
                            "status": "rejected",
                            "reject_reason": "REJECT_LIQUIDITY_DRYUP",
                            "t1_restriction_hit": False,
                            "limit_guard_result": "PASS",
                            "session_guard_result": "PASS",
                            "contract_version": str(signal.get("contract_version", "")),
                            "created_at": created_at,
                        }
                    )
                    continue

                filled_price = float(price.get("open", 0.0) or 0.0)
                if filled_price <= 0.0:
                    filled_price = float(signal.get("entry", 0.0) or 0.0)
                if filled_price <= 0.0:
                    missing_price_entry_count += 1
                    continue

                position_size = float(signal.get("position_size", 0.0) or 0.0)
                capped_position = max(0.0, min(max_position_pct, position_size))
                raw_shares = int((cash * capped_position) / filled_price)
                shares = (raw_shares // 100) * 100
                if shares <= 0:
                    continue

                fill_probability, fill_ratio, _ = _estimate_fill(price=price, order_shares=shares)
                if fill_probability < MIN_FILL_PROBABILITY:
                    low_fill_prob_blocked_count += 1
                    trade_rows.append(
                        {
                            "backtest_id": backtest_id,
                            "trade_date": replay_day,
                            "signal_date": str(signal.get("trade_date", replay_day)),
                            "execute_date": replay_day,
                            "stock_code": stock_code,
                            "direction": "buy",
                            "filled_price": 0.0,
                            "shares": 0,
                            "amount": 0.0,
                            "pnl": 0.0,
                            "pnl_pct": 0.0,
                            "recommendation": str(signal.get("recommendation", "HOLD")),
                            "final_score": round(float(signal.get("final_score", 50.0) or 50.0), 4),
                            "risk_reward_ratio": round(
                                float(signal.get("risk_reward_ratio", 0.0) or 0.0), 4
                            ),
                            "integration_mode": str(signal.get("integration_mode", "top_down")),
                            "weight_plan_id": str(signal.get("weight_plan_id", "")),
                            "status": "rejected",
                            "reject_reason": "REJECT_LOW_FILL_PROB",
                            "t1_restriction_hit": False,
                            "limit_guard_result": "PASS",
                            "session_guard_result": "PASS",
                            "contract_version": str(signal.get("contract_version", "")),
                            "created_at": created_at,
                        }
                    )
                    continue
                filled_shares = (int(shares * fill_ratio) // 100) * 100
                if filled_shares <= 0:
                    zero_fill_blocked_count += 1
                    trade_rows.append(
                        {
                            "backtest_id": backtest_id,
                            "trade_date": replay_day,
                            "signal_date": str(signal.get("trade_date", replay_day)),
                            "execute_date": replay_day,
                            "stock_code": stock_code,
                            "direction": "buy",
                            "filled_price": 0.0,
                            "shares": 0,
                            "amount": 0.0,
                            "pnl": 0.0,
                            "pnl_pct": 0.0,
                            "recommendation": str(signal.get("recommendation", "HOLD")),
                            "final_score": round(float(signal.get("final_score", 50.0) or 50.0), 4),
                            "risk_reward_ratio": round(
                                float(signal.get("risk_reward_ratio", 0.0) or 0.0), 4
                            ),
                            "integration_mode": str(signal.get("integration_mode", "top_down")),
                            "weight_plan_id": str(signal.get("weight_plan_id", "")),
                            "status": "rejected",
                            "reject_reason": "REJECT_ZERO_FILL",
                            "t1_restriction_hit": False,
                            "limit_guard_result": "PASS",
                            "session_guard_result": "PASS",
                            "contract_version": str(signal.get("contract_version", "")),
                            "created_at": created_at,
                        }
                    )
                    continue

                amount = round(filled_price * filled_shares, 4)
                (
                    commission,
                    _,
                    transfer_fee,
                    buy_total_fee,
                    fee_tier_label,
                ) = calc_fees(amount, "buy")
                impact_cost, liquidity_tier, _ = _estimate_impact_cost(
                    price=price,
                    order_shares=filled_shares,
                    amount=amount,
                    slippage_rate=float(config.backtest_slippage_value),
                )
                buy_total_fee = round(buy_total_fee + impact_cost, 6)
                required_cash = amount + buy_total_fee
                if required_cash > cash:
                    continue
                cash = round(cash - required_cash, 4)

                can_sell_date = _next_trade_day(replay_days, replay_day) or replay_day
                positions[stock_code] = {
                    "shares": filled_shares,
                    "buy_price": filled_price,
                    "buy_amount": amount,
                    "buy_fee": buy_total_fee,
                    "signal_date": str(signal.get("trade_date", replay_day)),
                    "recommendation": str(signal.get("recommendation", "HOLD")),
                    "final_score": float(signal.get("final_score", 50.0) or 50.0),
                    "risk_reward_ratio": float(signal.get("risk_reward_ratio", 0.0) or 0.0),
                    "integration_mode": str(signal.get("integration_mode", "top_down")),
                    "weight_plan_id": str(signal.get("weight_plan_id", "")),
                    "contract_version": str(signal.get("contract_version", SUPPORTED_CONTRACT_VERSION)),
                    "can_sell_date": can_sell_date,
                }

                trade_rows.append(
                    {
                        "backtest_id": backtest_id,
                        "trade_date": replay_day,
                        "signal_date": str(signal.get("trade_date", replay_day)),
                        "execute_date": replay_day,
                        "stock_code": stock_code,
                        "direction": "buy",
                        "filled_price": round(filled_price, 4),
                        "shares": filled_shares,
                        "amount": amount,
                        "pnl": 0.0,
                        "pnl_pct": 0.0,
                        "recommendation": str(signal.get("recommendation", "HOLD")),
                        "final_score": round(float(signal.get("final_score", 50.0) or 50.0), 4),
                        "risk_reward_ratio": round(
                            float(signal.get("risk_reward_ratio", 0.0) or 0.0), 4
                        ),
                        "integration_mode": str(signal.get("integration_mode", "top_down")),
                        "weight_plan_id": str(signal.get("weight_plan_id", "")),
                        "status": "filled",
                        "reject_reason": "",
                        "t1_restriction_hit": False,
                        "limit_guard_result": "PASS",
                        "session_guard_result": "PASS",
                        "contract_version": str(signal.get("contract_version", "")),
                        "created_at": created_at,
                    }
                )
                commission_total += commission
                transfer_fee_total += transfer_fee
                impact_cost_total += impact_cost
                executed_notional_total += amount
                fee_tier_counts[fee_tier_label] = fee_tier_counts.get(fee_tier_label, 0) + 1
                liquidity_tier_counts[liquidity_tier] = liquidity_tier_counts.get(liquidity_tier, 0) + 1

            # 3) Mark-to-market equity for max drawdown tracking.
            market_value = 0.0
            for stock_code, pos in positions.items():
                price = price_lookup.get((replay_day, stock_code), {})
                close_price = float(price.get("close", 0.0) or 0.0)
                if close_price <= 0.0:
                    close_price = float(price.get("open", 0.0) or 0.0)
                if close_price <= 0.0:
                    close_price = float(pos.get("buy_price", 0.0) or 0.0)
                market_value += close_price * int(pos.get("shares", 0))
            equity_curve.append(round(cash + market_value, 4))

        filled_rows = [row for row in trade_rows if str(row.get("status", "")) == "filled"]
        if not filled_rows:
            if long_entry_signal_count <= 0:
                add_warning("no_long_entry_signal_in_window")
            elif mapped_long_entry_signal_count <= 0:
                add_warning("long_entry_signal_out_of_window")
            else:
                add_warning("no_filled_trade_after_execution_guards")

    trade_frame = (
        pd.DataFrame.from_records(trade_rows)
        if trade_rows
        else _empty_frame(BACKTEST_TRADE_COLUMNS)
    ).reindex(columns=BACKTEST_TRADE_COLUMNS)

    filled_frame = trade_frame[trade_frame["status"] == "filled"] if not trade_frame.empty else trade_frame
    sell_frame = filled_frame[filled_frame["direction"] == "sell"] if not filled_frame.empty else filled_frame

    total_trades = int(len(filled_frame))
    total_pnl = float(sell_frame["pnl"].sum()) if not sell_frame.empty else 0.0
    total_return = round(total_pnl / max(1.0, initial_cash), 8)
    win_rate = (
        round(float((sell_frame["pnl"] > 0).sum()) / len(sell_frame), 6)
        if not sell_frame.empty
        else 0.0
    )
    max_equity = max(equity_curve) if equity_curve else initial_cash
    min_equity = min(equity_curve) if equity_curve else initial_cash
    max_drawdown = round((max_equity - min_equity) / max(1.0, max_equity), 8)
    commission_total = round(float(commission_total), 6)
    stamp_tax_total = round(float(stamp_tax_total), 6)
    transfer_fee_total = round(float(transfer_fee_total), 6)
    impact_cost_total = round(float(impact_cost_total), 6)
    total_fee = round(commission_total + stamp_tax_total + transfer_fee_total + impact_cost_total, 6)
    cost_bps = round(total_fee / max(1.0, executed_notional_total) * 10_000.0, 6)
    impact_cost_ratio = round(
        impact_cost_total / max(1e-12, total_fee),
        8,
    ) if total_fee > 0.0 else 0.0
    max_drawdown_days = _compute_max_drawdown_days(equity_curve)
    daily_return_distribution = _compute_daily_return_distribution(equity_curve)
    turnover_stability = _compute_turnover_stability(
        trade_frame=trade_frame,
        replay_days=replay_days,
        initial_cash=initial_cash,
    )

    gate_quality_status, gate_go_nogo, gate_quality_message = _to_quality_status(gate_frame)
    if errors:
        gate_quality_status = "FAIL"
        gate_go_nogo = "NO_GO"
        gate_quality_message = ";".join(item["message"] for item in errors)
    else:
        warning_segments: list[str] = []
        if any(
            count > 0
            for count in (
                limit_up_blocked_count,
                limit_down_blocked_count,
                one_word_board_blocked_count,
                liquidity_dryup_blocked_count,
                t1_guard_blocked_count,
                low_fill_prob_blocked_count,
                zero_fill_blocked_count,
                missing_price_entry_count,
                missing_price_exit_count,
                signal_out_of_window_count,
            )
        ):
            warning_segments.append(
                f"limit_up_blocked={limit_up_blocked_count};"
                f"limit_down_blocked={limit_down_blocked_count};"
                f"one_word_board_blocked={one_word_board_blocked_count};"
                f"liquidity_dryup_blocked={liquidity_dryup_blocked_count};"
                f"t1_guard_blocked={t1_guard_blocked_count};"
                f"low_fill_prob_blocked={low_fill_prob_blocked_count};"
                f"zero_fill_blocked={zero_fill_blocked_count};"
                f"missing_price_entry={missing_price_entry_count};"
                f"missing_price_exit={missing_price_exit_count};"
                f"signal_out_of_window={signal_out_of_window_count}"
            )
        if warnings:
            warning_segments.append(f"warnings={','.join(warnings)}")
        if warning_segments:
            if gate_quality_status == "PASS":
                gate_quality_status = "WARN"
            gate_quality_message = f"{gate_quality_message};" + ";".join(warning_segments)

    bridge_check_status = (
        "PASS"
        if not errors and not bridge_frame.empty
        else "FAIL"
    )

    result_frame = pd.DataFrame.from_records(
        [
            {
                "backtest_id": backtest_id,
                "engine": normalized_engine,
                "start_date": start_date,
                "end_date": end_date,
                "quality_status": gate_quality_status,
                "go_nogo": gate_go_nogo,
                "consumed_signal_rows": int(len(integrated_frame)),
                "total_trades": total_trades,
                "win_rate": win_rate,
                "total_return": total_return,
                "max_drawdown": max_drawdown,
                "max_drawdown_days": max_drawdown_days,
                "daily_return_mean": daily_return_distribution["daily_return_mean"],
                "daily_return_std": daily_return_distribution["daily_return_std"],
                "daily_return_p05": daily_return_distribution["daily_return_p05"],
                "daily_return_p95": daily_return_distribution["daily_return_p95"],
                "daily_return_skew": daily_return_distribution["daily_return_skew"],
                "turnover_mean": turnover_stability["turnover_mean"],
                "turnover_std": turnover_stability["turnover_std"],
                "turnover_cv": turnover_stability["turnover_cv"],
                "commission_total": commission_total,
                "stamp_tax_total": stamp_tax_total,
                "transfer_fee_total": transfer_fee_total,
                "impact_cost_total": impact_cost_total,
                "total_fee": total_fee,
                "cost_bps": cost_bps,
                "impact_cost_ratio": impact_cost_ratio,
                "source_fetch_progress_path": str(fetch_status.progress_path),
                "source_fetch_start_date": fetch_status.start_date,
                "source_fetch_end_date": fetch_status.end_date,
                "source_fetch_status": fetch_status.status,
                "bridge_check_status": bridge_check_status,
                "contract_version": SUPPORTED_CONTRACT_VERSION,
                "created_at": created_at,
            }
        ]
    ).reindex(columns=BACKTEST_RESULT_COLUMNS)

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    result_frame.to_parquet(backtest_results_path, index=False)
    trade_frame.to_parquet(backtest_trade_records_path, index=False)

    if database_path.exists():
        _persist(
            database_path=database_path,
            table_name="backtest_results",
            frame=result_frame,
            delete_key="backtest_id",
            delete_value=backtest_id,
        )
        _persist(
            database_path=database_path,
            table_name="backtest_trade_records",
            frame=trade_frame,
            delete_key="backtest_id",
            delete_value=backtest_id,
        )

    a_metric = total_return
    b_metric = round(float((integrated_frame["mss_score"] - 50.0).mean() / 500.0), 8) if not integrated_frame.empty else 0.0
    irs_metric = round(float((integrated_frame["irs_score"] - 50.0).mean() / 550.0), 8) if not integrated_frame.empty else 0.0
    c_metric = round(float((integrated_frame["pas_score"] - 50.0).mean() / 600.0), 8) if not integrated_frame.empty else 0.0
    ab_lines = [
        "# S3 A/B/C Metric Summary",
        "",
        f"- backtest_id: {backtest_id}",
        f"- A_sentiment_main_total_return: {a_metric}",
        f"- B_baseline_mss_proxy_return: {b_metric}",
        f"- core_irs_proxy_return: {irs_metric}",
        f"- C_control_pas_proxy_return: {c_metric}",
        f"- conclusion: {'A_dominant' if a_metric >= max(b_metric, c_metric) else 'A_not_dominant'}",
        "",
    ]
    _write_markdown(ab_metric_summary_path, ab_lines)

    performance_lines = [
        "# S3 Performance Metrics",
        "",
        f"- backtest_id: {backtest_id}",
        f"- max_drawdown: {max_drawdown}",
        f"- max_drawdown_days: {max_drawdown_days}",
        "",
        "## Return Distribution",
        f"- daily_return_mean: {daily_return_distribution['daily_return_mean']}",
        f"- daily_return_std: {daily_return_distribution['daily_return_std']}",
        f"- daily_return_p05: {daily_return_distribution['daily_return_p05']}",
        f"- daily_return_p95: {daily_return_distribution['daily_return_p95']}",
        f"- daily_return_skew: {daily_return_distribution['daily_return_skew']}",
        "",
        "## Turnover Stability",
        f"- turnover_mean: {turnover_stability['turnover_mean']}",
        f"- turnover_std: {turnover_stability['turnover_std']}",
        f"- turnover_cv: {turnover_stability['turnover_cv']}",
        "",
        "## Cost & Slippage",
        f"- commission_total: {commission_total}",
        f"- stamp_tax_total: {stamp_tax_total}",
        f"- transfer_fee_total: {transfer_fee_total}",
        f"- impact_cost_total: {impact_cost_total}",
        f"- total_fee: {total_fee}",
        f"- cost_bps: {cost_bps}",
        f"- impact_cost_ratio: {impact_cost_ratio}",
        f"- fee_tier_counts: {fee_tier_counts}",
        f"- liquidity_tier_counts: {liquidity_tier_counts}",
        "",
    ]
    _write_markdown(performance_metrics_report_path, performance_lines)

    core_coverage_status = (
        "PASS"
        if all(int(window_table_counts.get(item, 0)) > 0 for item in CORE_INPUT_TABLES)
        else "FAIL"
    )
    consumption_lines = [
        "# S3 Consumption Record",
        "",
        "## S3a Inputs",
        f"- fetch_progress_path: {fetch_status.progress_path}",
        f"- fetch_status: {fetch_status.status}",
        f"- fetch_range: {fetch_status.start_date} ~ {fetch_status.end_date}",
        f"- last_success_batch_id: {fetch_status.last_success_batch_id}",
        "",
        "## S2c/S2b Inputs",
        f"- integrated_recommendation_rows: {len(integrated_frame)}",
        f"- quality_gate_rows: {len(gate_frame)}",
        f"- bridge_rows: {len(bridge_frame)}",
        f"- bridge_check_status: {bridge_check_status}",
        f"- replay_trading_days: {len(replay_days)}",
        "",
        "## Local DB Coverage",
        f"- local_duckdb_path: {database_path}",
        f"- raw_trade_cal_rows_in_window: {window_table_counts.get('raw_trade_cal', 0)}",
        f"- raw_daily_rows_in_window: {window_table_counts.get('raw_daily', 0)}",
        f"- mss_panorama_rows_in_window: {window_table_counts.get('mss_panorama', 0)}",
        f"- irs_industry_daily_rows_in_window: {window_table_counts.get('irs_industry_daily', 0)}",
        f"- stock_pas_daily_rows_in_window: {window_table_counts.get('stock_pas_daily', 0)}",
        f"- integrated_recommendation_rows_in_window: {window_table_counts.get('integrated_recommendation', 0)}",
        f"- validation_weight_plan_rows_in_window: {window_table_counts.get('validation_weight_plan', 0)}",
        f"- core_algorithm_coverage_status: {core_coverage_status}",
        "",
        f"- consumption_conclusion: {'ready_for_s4' if gate_go_nogo == 'GO' else 'blocked'}",
        "",
    ]
    _write_markdown(consumption_path, consumption_lines)

    gate_lines = [
        "# S3 Gate Report",
        "",
        f"- backtest_id: {backtest_id}",
        f"- quality_status: {gate_quality_status}",
        f"- go_nogo: {gate_go_nogo}",
        f"- warning_count: {len(warnings)}",
        f"- warnings: {warnings}",
        f"- gate_message: {gate_quality_message}",
        f"- bridge_check_status: {bridge_check_status}",
        f"- limit_up_blocked_count: {limit_up_blocked_count}",
        f"- limit_down_blocked_count: {limit_down_blocked_count}",
        f"- one_word_board_blocked_count: {one_word_board_blocked_count}",
        f"- liquidity_dryup_blocked_count: {liquidity_dryup_blocked_count}",
        f"- t1_guard_blocked_count: {t1_guard_blocked_count}",
        f"- low_fill_prob_blocked_count: {low_fill_prob_blocked_count}",
        f"- zero_fill_blocked_count: {zero_fill_blocked_count}",
        f"- missing_price_entry_count: {missing_price_entry_count}",
        f"- missing_price_exit_count: {missing_price_exit_count}",
        f"- signal_out_of_window_count: {signal_out_of_window_count}",
        f"- local_duckdb_path: {database_path}",
        f"- mss_panorama_rows_in_window: {window_table_counts.get('mss_panorama', 0)}",
        f"- irs_industry_daily_rows_in_window: {window_table_counts.get('irs_industry_daily', 0)}",
        f"- stock_pas_daily_rows_in_window: {window_table_counts.get('stock_pas_daily', 0)}",
        f"- core_algorithm_coverage_status: {core_coverage_status}",
        "",
    ]
    _write_markdown(gate_report_path, gate_lines)

    error_payload = {
        "backtest_id": backtest_id,
        "start_date": start_date,
        "end_date": end_date,
        "warning_count": len(warnings),
        "warnings": warnings,
        "error_count": len(errors),
        "errors": errors,
    }
    _write_json(error_manifest_path, error_payload)
    if errors:
        error_manifest_path = artifacts_dir / "error_manifest.json"
        _write_json(error_manifest_path, error_payload)

    s3r_patch_note_path: Path | None = None
    s3r_delta_report_path: Path | None = None
    if repair_mode == "s3r":
        s3r_patch_note_path = artifacts_dir / "s3r_patch_note.md"
        s3r_delta_report_path = artifacts_dir / "s3r_delta_report.md"
        _write_s3r_patch_note(
            path=s3r_patch_note_path,
            backtest_id=backtest_id,
            engine=normalized_engine,
            start_date=start_date,
            end_date=end_date,
            quality_status=gate_quality_status,
            go_nogo=gate_go_nogo,
        )
        _write_s3r_delta_report(
            path=s3r_delta_report_path,
            consumed_signal_rows=int(len(integrated_frame)),
            total_trades=total_trades,
            quality_status=gate_quality_status,
            go_nogo=gate_go_nogo,
        )

    return BacktestRunResult(
        backtest_id=backtest_id,
        engine=normalized_engine,
        start_date=start_date,
        end_date=end_date,
        artifacts_dir=artifacts_dir,
        backtest_results_path=backtest_results_path,
        backtest_trade_records_path=backtest_trade_records_path,
        ab_metric_summary_path=ab_metric_summary_path,
        performance_metrics_report_path=performance_metrics_report_path,
        gate_report_path=gate_report_path,
        consumption_path=consumption_path,
        error_manifest_path=error_manifest_path,
        consumed_signal_rows=int(len(integrated_frame)),
        total_trades=total_trades,
        quality_status=gate_quality_status,
        go_nogo=gate_go_nogo,
        bridge_check_status=bridge_check_status,
        has_error=bool(errors),
        repair=repair_mode,
        s3r_patch_note_path=s3r_patch_note_path,
        s3r_delta_report_path=s3r_delta_report_path,
    )
