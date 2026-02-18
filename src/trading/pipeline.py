from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config

# DESIGN_TRACE:
# - Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md (§5 S4)
# - docs/design/core-infrastructure/trading/trading-algorithm.md (§2 信号生成, §3 风控, §5 执行)
DESIGN_TRACE = {
    "s3a_s4b_roadmap": "Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md",
    "trading_algorithm_design": "docs/design/core-infrastructure/trading/trading-algorithm.md",
}

SUPPORTED_MODE = {"paper"}
SUPPORTED_CONTRACT_VERSION = "nc-v1"
LIMIT_RATIO_MAIN_BOARD = 0.10
LIMIT_RATIO_GEM_STAR = 0.20
LIMIT_RATIO_ST = 0.05
LIMIT_PRICE_TOLERANCE_RATIO = 0.001

TRADE_RECORD_COLUMNS = [
    "trade_id",
    "trade_date",
    "stock_code",
    "industry_code",
    "direction",
    "order_type",
    "price",
    "shares",
    "amount",
    "commission",
    "stamp_tax",
    "transfer_fee",
    "total_fee",
    "status",
    "reject_reason",
    "t1_restriction_hit",
    "limit_guard_result",
    "session_guard_result",
    "risk_reward_ratio",
    "contract_version",
    "created_at",
]

POSITION_COLUMNS = [
    "trade_date",
    "stock_code",
    "industry_code",
    "shares",
    "cost_price",
    "market_price",
    "market_value",
    "buy_date",
    "can_sell_date",
    "is_frozen",
    "contract_version",
    "created_at",
]

RISK_EVENT_COLUMNS = [
    "trade_date",
    "stock_code",
    "event_type",
    "severity",
    "message",
    "contract_version",
    "created_at",
]


@dataclass(frozen=True)
class TradeRunResult:
    trade_date: str
    mode: str
    artifacts_dir: Path
    trade_records_path: Path
    positions_path: Path
    risk_events_path: Path
    paper_trade_replay_path: Path
    consumption_path: Path
    gate_report_path: Path
    error_manifest_path: Path
    total_orders: int
    filled_orders: int
    risk_event_count: int
    quality_status: str
    go_nogo: str
    has_error: bool


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _artifacts_dir(trade_date: str) -> Path:
    return Path("artifacts") / "spiral-s4" / trade_date


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _persist(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
    delete_trade_date: str,
) -> None:
    with duckdb.connect(str(database_path)) as connection:
        exists_row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()
        table_exists = bool(exists_row and int(exists_row[0]) > 0)
        if frame.empty:
            if table_exists and frame.columns.tolist() and "trade_date" in frame.columns:
                connection.execute(f"DELETE FROM {table_name} WHERE trade_date = ?", [delete_trade_date])
            return
        connection.register("incoming_df", frame)
        if not table_exists:
            connection.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM incoming_df WHERE 1=0"
            )
        if frame.columns.tolist() and "trade_date" in frame.columns:
            connection.execute(f"DELETE FROM {table_name} WHERE trade_date = ?", [delete_trade_date])
        connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_df")
        connection.unregister("incoming_df")


def _read_s3_backtest_status(database_path: Path, trade_date: str) -> tuple[bool, str]:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'backtest_results'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return (False, "backtest_results_missing")

        rec = connection.execute(
            "SELECT backtest_id, quality_status, go_nogo, end_date "
            "FROM backtest_results WHERE end_date <= ? "
            "ORDER BY end_date DESC, created_at DESC LIMIT 1",
            [trade_date],
        ).fetchone()
    if rec is None:
        return (False, "backtest_results_not_ready")
    quality_status = str(rec[1]).upper()
    go_nogo = str(rec[2]).upper()
    if quality_status not in {"PASS", "WARN"} or go_nogo != "GO":
        return (False, "backtest_gate_not_passed")
    return (True, str(rec[0]))


def _read_quality_gate_status(database_path: Path, trade_date: str) -> tuple[bool, str]:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'quality_gate_report'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return (False, "quality_gate_report_missing")
        rec = connection.execute(
            "SELECT status FROM quality_gate_report WHERE trade_date = ? ORDER BY created_at DESC LIMIT 1",
            [trade_date],
        ).fetchone()
    if rec is None:
        return (False, "quality_gate_row_missing")
    status = str(rec[0]).upper()
    if status == "FAIL":
        return (False, "quality_gate_fail")
    if status in {"PASS", "WARN"}:
        return (True, status)
    return (False, "quality_gate_status_invalid")


def _read_signals(database_path: Path, trade_date: str) -> pd.DataFrame:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'integrated_recommendation'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return _empty_frame(
                [
                    "trade_date",
                    "stock_code",
                    "industry_code",
                    "final_score",
                    "position_size",
                    "risk_reward_ratio",
                    "recommendation",
                    "direction",
                    "entry",
                    "contract_version",
                ]
            )
        frame = connection.execute(
            "SELECT trade_date, stock_code, industry_code, final_score, position_size, "
            "risk_reward_ratio, recommendation, direction, entry, contract_version "
            "FROM integrated_recommendation "
            "WHERE trade_date = ? "
            "ORDER BY final_score DESC, stock_code",
            [trade_date],
        ).df()
    return frame


def _read_prices(database_path: Path, trade_date: str) -> dict[str, dict[str, float]]:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'raw_daily'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return {}
        frame = connection.execute(
            "SELECT COALESCE(NULLIF(stock_code, ''), SPLIT_PART(ts_code, '.', 1)) AS stock_code, "
            "open, high, low, close "
            "FROM raw_daily WHERE trade_date = ? ORDER BY stock_code",
            [trade_date],
        ).df()
    lookup: dict[str, dict[str, float]] = {}
    for _, row in frame.iterrows():
        stock_code = str(row.get("stock_code", ""))
        lookup[stock_code] = {
            "open": float(row.get("open", 0.0) or 0.0),
            "high": float(row.get("high", 0.0) or 0.0),
            "low": float(row.get("low", 0.0) or 0.0),
            "close": float(row.get("close", 0.0) or 0.0),
        }
    return lookup


def _table_has_column(
    connection: duckdb.DuckDBPyConnection, table_name: str, column_name: str
) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = ? AND column_name = ?",
        [table_name, column_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _read_prev_close_lookup(database_path: Path, trade_date: str) -> dict[str, float]:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'raw_daily'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return {}
        has_stock_code = _table_has_column(connection, "raw_daily", "stock_code")
        has_ts_code = _table_has_column(connection, "raw_daily", "ts_code")
        if not has_stock_code and not has_ts_code:
            return {}

        if has_stock_code and has_ts_code:
            stock_code_expr = "COALESCE(NULLIF(stock_code, ''), SPLIT_PART(ts_code, '.', 1))"
        elif has_stock_code:
            stock_code_expr = "stock_code"
        else:
            stock_code_expr = "SPLIT_PART(ts_code, '.', 1)"

        frame = connection.execute(
            "WITH raw AS ("
            f"SELECT trade_date, {stock_code_expr} AS stock_code, close "
            "FROM raw_daily WHERE trade_date <= ?"
            "), shifted AS ("
            "SELECT trade_date, stock_code, "
            "LAG(close) OVER (PARTITION BY stock_code ORDER BY trade_date) AS prev_close "
            "FROM raw"
            ") "
            "SELECT stock_code, prev_close FROM shifted WHERE trade_date = ?",
            [trade_date, trade_date],
        ).df()

    lookup: dict[str, float] = {}
    for _, row in frame.iterrows():
        stock_code = str(row.get("stock_code", "")).strip()
        prev_close = float(row.get("prev_close", 0.0) or 0.0)
        if not stock_code or prev_close <= 0.0:
            continue
        lookup[stock_code] = prev_close
    return lookup


def _read_stock_profiles(database_path: Path) -> dict[str, dict[str, str]]:
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
            f"SELECT {stock_code_expr} AS stock_code, {name_expr} AS stock_name FROM raw_stock_basic"
        ).df()

    profiles: dict[str, dict[str, str]] = {}
    for _, row in frame.iterrows():
        stock_code = str(row.get("stock_code", "")).strip()
        if not stock_code:
            continue
        profiles[stock_code] = {"stock_name": str(row.get("stock_name", "")).strip()}
    return profiles


def _read_previous_positions(database_path: Path, trade_date: str) -> list[dict[str, object]]:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'positions'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return []
        prev_day = connection.execute(
            "SELECT MAX(trade_date) FROM positions WHERE trade_date < ?",
            [trade_date],
        ).fetchone()
        prev_trade_date = str(prev_day[0]) if prev_day and prev_day[0] is not None else ""
        if not prev_trade_date:
            return []
        frame = connection.execute(
            "SELECT trade_date, stock_code, industry_code, shares, cost_price, market_price, market_value, "
            "buy_date, can_sell_date, is_frozen, contract_version, created_at "
            "FROM positions WHERE trade_date = ? ORDER BY stock_code",
            [prev_trade_date],
        ).df()
    return frame.to_dict(orient="records")


def _read_available_cash(database_path: Path, trade_date: str, initial_cash: float) -> float:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'trade_records'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return round(initial_cash, 4)
        frame = connection.execute(
            "SELECT direction, amount, total_fee FROM trade_records "
            "WHERE trade_date < ? AND status = 'filled' ORDER BY trade_date, trade_id",
            [trade_date],
        ).df()

    cash = float(initial_cash)
    for _, row in frame.iterrows():
        direction = str(row.get("direction", "")).strip().lower()
        amount = float(row.get("amount", 0.0) or 0.0)
        total_fee = float(row.get("total_fee", 0.0) or 0.0)
        if direction == "buy":
            cash -= amount + total_fee
        elif direction == "sell":
            cash += amount - total_fee
    return round(cash, 4)


def _read_next_trade_day(database_path: Path, trade_date: str) -> str:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'raw_trade_cal'"
        ).fetchone()
        if not row or int(row[0]) <= 0:
            return trade_date
        rec = connection.execute(
            "SELECT trade_date FROM raw_trade_cal "
            "WHERE trade_date > ? AND CAST(is_open AS INTEGER) = 1 "
            "ORDER BY trade_date LIMIT 1",
            [trade_date],
        ).fetchone()
    return str(rec[0]) if rec else trade_date


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
        if open_price >= (limit_price - tolerance) and high_price >= (limit_price - tolerance):
            return True
    return open_price >= high_price * 0.999


def _is_limit_down(*, price: dict[str, float], prev_close: float | None, limit_ratio: float) -> bool:
    open_price = float(price.get("open", 0.0))
    low_price = float(price.get("low", 0.0))
    if open_price <= 0.0 or low_price <= 0.0:
        return False
    if prev_close is not None and prev_close > 0.0 and limit_ratio > 0.0:
        limit_price = prev_close * (1.0 - limit_ratio)
        tolerance = _price_tolerance(limit_price)
        if open_price <= (limit_price + tolerance) and low_price <= (limit_price + tolerance):
            return True
    return open_price <= low_price * 1.001


def run_paper_trade(
    *,
    trade_date: str,
    mode: str,
    config: Config,
) -> TradeRunResult:
    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in SUPPORTED_MODE:
        raise ValueError(f"unsupported trade mode: {mode}; only paper is supported")

    artifacts_dir = _artifacts_dir(trade_date)
    trade_records_path = artifacts_dir / "trade_records_sample.parquet"
    positions_path = artifacts_dir / "positions_sample.parquet"
    risk_events_path = artifacts_dir / "risk_events_sample.parquet"
    replay_path = artifacts_dir / "paper_trade_replay.md"
    consumption_path = artifacts_dir / "consumption.md"
    gate_report_path = artifacts_dir / "gate_report.md"
    error_manifest_path = artifacts_dir / "error_manifest_sample.json"

    errors: list[dict[str, str]] = []

    def add_error(level: str, step: str, message: str) -> None:
        errors.append(
            {
                "error_level": level,
                "step": step,
                "trade_date": trade_date,
                "message": message,
            }
        )

    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not database_path.exists():
        add_error("P0", "database", "duckdb_not_found")

    backtest_reference = ""
    if not errors:
        backtest_ready, backtest_reference = _read_s3_backtest_status(database_path, trade_date)
        if not backtest_ready:
            add_error("P0", "s3_consumption", backtest_reference)

    if not errors:
        gate_ok, gate_msg = _read_quality_gate_status(database_path, trade_date)
        if not gate_ok:
            add_error("P0", "quality_gate", gate_msg)

    signal_frame = _empty_frame(
        [
            "trade_date",
            "stock_code",
            "industry_code",
            "final_score",
            "position_size",
            "risk_reward_ratio",
            "recommendation",
            "direction",
            "entry",
            "contract_version",
        ]
    )
    prices: dict[str, dict[str, float]] = {}
    prev_close_lookup: dict[str, float] = {}
    stock_profile_lookup: dict[str, dict[str, str]] = {}
    previous_positions: list[dict[str, object]] = []
    next_trade_day = trade_date
    if not errors:
        signal_frame = _read_signals(database_path, trade_date)
        prices = _read_prices(database_path, trade_date)
        prev_close_lookup = _read_prev_close_lookup(database_path, trade_date)
        stock_profile_lookup = _read_stock_profiles(database_path)
        previous_positions = _read_previous_positions(database_path, trade_date)
        next_trade_day = _read_next_trade_day(database_path, trade_date)

        if signal_frame.empty:
            add_error("P0", "signal_input", "integrated_recommendation_empty")
        invalid_contract = signal_frame[
            signal_frame["contract_version"] != SUPPORTED_CONTRACT_VERSION
        ]
        if not invalid_contract.empty:
            add_error("P0", "contract", "integrated_recommendation_contract_version_mismatch")

    created_at = _utc_now_text()
    trade_records: list[dict[str, object]] = []
    risk_events: list[dict[str, object]] = []
    positions_by_code: dict[str, dict[str, object]] = {}

    initial_cash = float(config.backtest_initial_cash)
    available_cash = initial_cash
    max_position_pct = float(config.trading_max_position_pct)
    max_total_position = float(config.trading_max_total_position)
    min_score = float(config.trading_min_quality_score)
    top_n = int(config.trading_top_n)

    if database_path.exists():
        available_cash = _read_available_cash(database_path, trade_date, initial_cash)

    for row in previous_positions:
        stock_code = str(row.get("stock_code", "")).strip()
        shares = int(row.get("shares", 0) or 0)
        if not stock_code or shares <= 0:
            continue
        day_price = prices.get(stock_code, {})
        close_price = float(day_price.get("close", 0.0) or 0.0)
        if close_price <= 0.0:
            close_price = float(row.get("market_price", row.get("cost_price", 0.0)) or 0.0)
        market_price = round(close_price, 4) if close_price > 0.0 else 0.0
        can_sell_date = str(row.get("can_sell_date", trade_date) or trade_date)
        positions_by_code[stock_code] = {
            "trade_date": trade_date,
            "stock_code": stock_code,
            "industry_code": str(row.get("industry_code", "")),
            "shares": shares,
            "cost_price": round(float(row.get("cost_price", 0.0) or 0.0), 4),
            "market_price": market_price,
            "market_value": round(market_price * shares, 4),
            "buy_date": str(row.get("buy_date", trade_date) or trade_date),
            "can_sell_date": can_sell_date,
            "is_frozen": trade_date < can_sell_date,
            "contract_version": str(row.get("contract_version", SUPPORTED_CONTRACT_VERSION))
            or SUPPORTED_CONTRACT_VERSION,
            "created_at": str(row.get("created_at", created_at) or created_at),
            "risk_reward_ratio": 1.0,
        }

    trade_seq = 1

    def next_trade_id() -> str:
        nonlocal trade_seq
        trade_id = f"TRD_{trade_date}_{trade_seq:04d}"
        trade_seq += 1
        return trade_id

    def calc_fee(amount: float, direction: str) -> tuple[float, float, float, float]:
        commission = max(float(config.trading_min_commission), amount * float(config.trading_commission_rate))
        stamp_tax = amount * float(config.trading_stamp_duty_rate) if direction == "sell" else 0.0
        transfer_fee = amount * float(config.trading_transfer_fee_rate)
        total_fee = commission + stamp_tax + transfer_fee
        return (
            round(commission, 6),
            round(stamp_tax, 6),
            round(transfer_fee, 6),
            round(total_fee, 6),
        )

    def try_execute_sell(stock_code: str) -> bool:
        nonlocal available_cash
        pos = positions_by_code.get(stock_code)
        if pos is None:
            return False
        shares = int(pos.get("shares", 0) or 0)
        if shares <= 0:
            positions_by_code.pop(stock_code, None)
            return False

        industry_code = str(pos.get("industry_code", ""))
        rr_ratio = float(pos.get("risk_reward_ratio", 1.0) or 1.0)
        price = prices.get(stock_code)
        if not price:
            risk_events.append(
                {
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "event_type": "REJECT_NO_PRICE",
                    "severity": "WARN",
                    "message": "sell_missing_raw_daily_price",
                    "contract_version": SUPPORTED_CONTRACT_VERSION,
                    "created_at": created_at,
                }
            )
            trade_records.append(
                {
                    "trade_id": next_trade_id(),
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "industry_code": industry_code,
                    "direction": "sell",
                    "order_type": "auction",
                    "price": 0.0,
                    "shares": 0,
                    "amount": 0.0,
                    "commission": 0.0,
                    "stamp_tax": 0.0,
                    "transfer_fee": 0.0,
                    "total_fee": 0.0,
                    "status": "rejected",
                    "reject_reason": "REJECT_NO_MARKET_PRICE",
                    "t1_restriction_hit": False,
                    "limit_guard_result": "UNKNOWN",
                    "session_guard_result": "FAIL_NO_PRICE",
                    "risk_reward_ratio": round(rr_ratio, 4),
                    "contract_version": SUPPORTED_CONTRACT_VERSION,
                    "created_at": created_at,
                }
            )
            return False

        stock_name = str(stock_profile_lookup.get(stock_code, {}).get("stock_name", "")).strip()
        limit_ratio = _resolve_limit_ratio(stock_code=stock_code, stock_name=stock_name)
        prev_close = prev_close_lookup.get(stock_code)
        if _is_limit_down(price=price, prev_close=prev_close, limit_ratio=limit_ratio):
            risk_events.append(
                {
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "event_type": "REJECT_LIMIT_DOWN",
                    "severity": "WARN",
                    "message": "sell_blocked_by_limit_down",
                    "contract_version": SUPPORTED_CONTRACT_VERSION,
                    "created_at": created_at,
                }
            )
            risk_events.append(
                {
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "event_type": "SELL_RETRY_NEXT_DAY",
                    "severity": "INFO",
                    "message": "limit_down_retry_scheduled_next_trade_day",
                    "contract_version": SUPPORTED_CONTRACT_VERSION,
                    "created_at": created_at,
                }
            )
            trade_records.append(
                {
                    "trade_id": next_trade_id(),
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "industry_code": industry_code,
                    "direction": "sell",
                    "order_type": "auction",
                    "price": 0.0,
                    "shares": 0,
                    "amount": 0.0,
                    "commission": 0.0,
                    "stamp_tax": 0.0,
                    "transfer_fee": 0.0,
                    "total_fee": 0.0,
                    "status": "rejected",
                    "reject_reason": "REJECT_LIMIT_DOWN",
                    "t1_restriction_hit": False,
                    "limit_guard_result": "REJECT_LIMIT_DOWN",
                    "session_guard_result": "PASS",
                    "risk_reward_ratio": round(rr_ratio, 4),
                    "contract_version": SUPPORTED_CONTRACT_VERSION,
                    "created_at": created_at,
                }
            )
            return False

        filled_price = float(price.get("open", 0.0) or 0.0)
        if filled_price <= 0.0:
            filled_price = float(price.get("close", 0.0) or 0.0)
        if filled_price <= 0.0:
            return False

        amount = round(filled_price * shares, 4)
        commission, stamp_tax, transfer_fee, total_fee = calc_fee(amount, "sell")
        available_cash = round(available_cash + amount - total_fee, 4)
        trade_records.append(
            {
                "trade_id": next_trade_id(),
                "trade_date": trade_date,
                "stock_code": stock_code,
                "industry_code": industry_code,
                "direction": "sell",
                "order_type": "auction",
                "price": round(filled_price, 4),
                "shares": shares,
                "amount": amount,
                "commission": commission,
                "stamp_tax": stamp_tax,
                "transfer_fee": transfer_fee,
                "total_fee": total_fee,
                "status": "filled",
                "reject_reason": "",
                "t1_restriction_hit": False,
                "limit_guard_result": "PASS",
                "session_guard_result": "PASS",
                "risk_reward_ratio": round(rr_ratio, 4),
                "contract_version": SUPPORTED_CONTRACT_VERSION,
                "created_at": created_at,
            }
        )
        positions_by_code.pop(stock_code, None)
        return True

    def try_execute_buy(row: dict[str, object]) -> tuple[bool, bool]:
        nonlocal available_cash
        stock_code = str(row.get("stock_code", "")).strip()
        if not stock_code:
            return (False, False)
        industry_code = str(row.get("industry_code", ""))
        rr_ratio = float(row.get("risk_reward_ratio", 0.0) or 0.0)

        if stock_code in positions_by_code:
            risk_events.append(
                {
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "event_type": "SKIP_ALREADY_HELD",
                    "severity": "INFO",
                    "message": "position_already_exists_skip_new_buy",
                    "contract_version": SUPPORTED_CONTRACT_VERSION,
                    "created_at": created_at,
                }
            )
            return (False, False)

        price = prices.get(stock_code)
        if not price:
            risk_events.append(
                {
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "event_type": "REJECT_NO_PRICE",
                    "severity": "WARN",
                    "message": "missing_raw_daily_price",
                    "contract_version": SUPPORTED_CONTRACT_VERSION,
                    "created_at": created_at,
                }
            )
            return (False, False)

        stock_name = str(stock_profile_lookup.get(stock_code, {}).get("stock_name", "")).strip()
        limit_ratio = _resolve_limit_ratio(stock_code=stock_code, stock_name=stock_name)
        prev_close = prev_close_lookup.get(stock_code)
        if _is_limit_up(price=price, prev_close=prev_close, limit_ratio=limit_ratio):
            risk_events.append(
                {
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "event_type": "REJECT_LIMIT_UP",
                    "severity": "WARN",
                    "message": "buy_blocked_by_limit_up",
                    "contract_version": SUPPORTED_CONTRACT_VERSION,
                    "created_at": created_at,
                }
            )
            trade_records.append(
                {
                    "trade_id": next_trade_id(),
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "industry_code": industry_code,
                    "direction": "buy",
                    "order_type": "auction",
                    "price": 0.0,
                    "shares": 0,
                    "amount": 0.0,
                    "commission": 0.0,
                    "stamp_tax": 0.0,
                    "transfer_fee": 0.0,
                    "total_fee": 0.0,
                    "status": "rejected",
                    "reject_reason": "REJECT_LIMIT_UP",
                    "t1_restriction_hit": False,
                    "limit_guard_result": "REJECT_LIMIT_UP",
                    "session_guard_result": "PASS",
                    "risk_reward_ratio": round(rr_ratio, 4),
                    "contract_version": SUPPORTED_CONTRACT_VERSION,
                    "created_at": created_at,
                }
            )
            return (False, True)

        filled_price = float(price.get("open", 0.0) or 0.0)
        if filled_price <= 0.0:
            filled_price = float(row.get("entry", 0.0) or 0.0)
        if filled_price <= 0.0:
            return (False, False)

        position_size = float(row.get("position_size", 0.0) or 0.0)
        target_pct = max(0.0, min(max_position_pct, position_size))
        if target_pct <= 0.0:
            target_pct = max_position_pct

        current_total_position = sum(
            float(item.get("market_value", 0.0) or 0.0) for item in positions_by_code.values()
        )
        total_equity = max(1.0, available_cash + current_total_position)
        if (current_total_position / total_equity) > max_total_position:
            risk_events.append(
                {
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "event_type": "REJECT_MAX_TOTAL_POSITION",
                    "severity": "WARN",
                    "message": "blocked_by_total_position_cap",
                    "contract_version": SUPPORTED_CONTRACT_VERSION,
                    "created_at": created_at,
                }
            )
            return (False, False)

        raw_shares = int((available_cash * target_pct) / filled_price)
        shares = (raw_shares // 100) * 100
        if shares <= 0:
            return (False, False)

        amount = round(filled_price * shares, 4)
        commission, stamp_tax, transfer_fee, total_fee = calc_fee(amount, "buy")
        required_cash = amount + total_fee
        if required_cash > available_cash:
            return (False, False)
        available_cash = round(available_cash - required_cash, 4)

        trade_records.append(
            {
                "trade_id": next_trade_id(),
                "trade_date": trade_date,
                "stock_code": stock_code,
                "industry_code": industry_code,
                "direction": "buy",
                "order_type": "auction",
                "price": round(filled_price, 4),
                "shares": shares,
                "amount": amount,
                "commission": commission,
                "stamp_tax": stamp_tax,
                "transfer_fee": transfer_fee,
                "total_fee": total_fee,
                "status": "filled",
                "reject_reason": "",
                "t1_restriction_hit": False,
                "limit_guard_result": "PASS",
                "session_guard_result": "PASS",
                "risk_reward_ratio": round(rr_ratio, 4),
                "contract_version": SUPPORTED_CONTRACT_VERSION,
                "created_at": created_at,
            }
        )
        close_price = float(price.get("close", filled_price) or filled_price)
        positions_by_code[stock_code] = {
            "trade_date": trade_date,
            "stock_code": stock_code,
            "industry_code": industry_code,
            "shares": shares,
            "cost_price": round(filled_price, 4),
            "market_price": round(close_price, 4),
            "market_value": round(close_price * shares, 4),
            "buy_date": trade_date,
            "can_sell_date": next_trade_day,
            "is_frozen": next_trade_day > trade_date,
            "contract_version": SUPPORTED_CONTRACT_VERSION,
            "created_at": created_at,
            "risk_reward_ratio": rr_ratio,
        }
        return (True, False)

    if not errors:
        for stock_code, position in positions_by_code.items():
            can_sell_date = str(position.get("can_sell_date", trade_date) or trade_date)
            position["is_frozen"] = trade_date < can_sell_date
            day_price = prices.get(stock_code)
            if not day_price:
                continue
            close_price = float(day_price.get("close", 0.0) or 0.0)
            if close_price <= 0.0:
                continue
            shares = int(position.get("shares", 0) or 0)
            position["market_price"] = round(close_price, 4)
            position["market_value"] = round(close_price * shares, 4)

        for stock_code in list(positions_by_code.keys()):
            can_sell_date = str(positions_by_code[stock_code].get("can_sell_date", trade_date) or trade_date)
            if trade_date < can_sell_date:
                continue
            try_execute_sell(stock_code)

        selected = signal_frame.head(top_n)
        strict_candidates: list[dict[str, object]] = []
        fallback_candidates: list[dict[str, object]] = []
        for _, row in selected.iterrows():
            payload = row.to_dict()
            stock_code = str(payload.get("stock_code", ""))
            final_score = float(payload.get("final_score", 0.0) or 0.0)
            recommendation = str(payload.get("recommendation", "HOLD"))
            rr_ratio = float(payload.get("risk_reward_ratio", 0.0) or 0.0)
            direction = str(payload.get("direction", "neutral"))
            if rr_ratio >= 1.0 and recommendation not in {"SELL", "AVOID"}:
                fallback_candidates.append(payload)
            if (
                final_score >= min_score
                and recommendation not in {"SELL", "AVOID"}
                and rr_ratio >= 1.0
                and direction != "bearish"
            ):
                strict_candidates.append(payload)
            else:
                risk_events.append(
                    {
                        "trade_date": trade_date,
                        "stock_code": stock_code,
                        "event_type": "SIGNAL_FILTERED",
                        "severity": "WARN",
                        "message": "filtered_by_score_or_rr_or_recommendation",
                        "contract_version": SUPPORTED_CONTRACT_VERSION,
                        "created_at": created_at,
                    }
                )

        any_filled = False
        for payload in strict_candidates:
            filled, _ = try_execute_buy(payload)
            any_filled = any_filled or filled

        if not any_filled and fallback_candidates:
            risk_events.append(
                {
                    "trade_date": trade_date,
                    "stock_code": str(fallback_candidates[0].get("stock_code", "")),
                    "event_type": "WARN_FALLBACK_MINIMAL_ORDER",
                    "severity": "WARN",
                    "message": "strict_filters_empty_use_fallback_candidate",
                    "contract_version": SUPPORTED_CONTRACT_VERSION,
                    "created_at": created_at,
                }
            )
            try_execute_buy(fallback_candidates[0])

    trade_frame = (
        pd.DataFrame.from_records(trade_records)
        if trade_records
        else _empty_frame(TRADE_RECORD_COLUMNS)
    ).reindex(columns=TRADE_RECORD_COLUMNS)
    position_frame = (
        pd.DataFrame.from_records(list(positions_by_code.values()))
        if positions_by_code
        else _empty_frame(POSITION_COLUMNS)
    ).reindex(columns=POSITION_COLUMNS)
    risk_event_frame = (
        pd.DataFrame.from_records(risk_events)
        if risk_events
        else _empty_frame(RISK_EVENT_COLUMNS)
    ).reindex(columns=RISK_EVENT_COLUMNS)

    filled_orders = int((trade_frame["status"] == "filled").sum()) if not trade_frame.empty else 0
    total_orders = int(len(trade_frame))
    risk_event_count = int(len(risk_event_frame))
    filled_sell_orders = (
        int(((trade_frame["direction"] == "sell") & (trade_frame["status"] == "filled")).sum())
        if not trade_frame.empty
        else 0
    )
    rejected_limit_down_count = (
        int((trade_frame["reject_reason"] == "REJECT_LIMIT_DOWN").sum()) if not trade_frame.empty else 0
    )

    if errors:
        quality_status = "FAIL"
        go_nogo = "NO_GO"
    elif filled_orders <= 0 and position_frame.empty:
        add_error("P0", "order_pipeline", "no_filled_orders")
        quality_status = "FAIL"
        go_nogo = "NO_GO"
    elif risk_event_count > 0 or filled_orders <= 0:
        quality_status = "WARN"
        go_nogo = "GO"
    else:
        quality_status = "PASS"
        go_nogo = "GO"

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    trade_frame.to_parquet(trade_records_path, index=False)
    position_frame.to_parquet(positions_path, index=False)
    risk_event_frame.to_parquet(risk_events_path, index=False)

    replay_lines = [
        "# S4 Paper Trade Replay",
        "",
        f"- trade_date: {trade_date}",
        f"- carryover_position_count: {len(previous_positions)}",
        f"- total_orders: {total_orders}",
        f"- filled_orders: {filled_orders}",
        f"- filled_sell_orders: {filled_sell_orders}",
        f"- rejected_limit_down_count: {rejected_limit_down_count}",
        f"- end_of_day_positions: {len(position_frame)}",
        f"- risk_event_count: {risk_event_count}",
        f"- quality_status: {quality_status}",
        f"- go_nogo: {go_nogo}",
        "",
    ]
    _write_markdown(replay_path, replay_lines)

    consumption_lines = [
        "# S4 Consumption Record",
        "",
        f"- source_backtest: {backtest_reference}",
        f"- integrated_signal_rows: {len(signal_frame)}",
        f"- carryover_position_count: {len(previous_positions)}",
        f"- filled_orders: {filled_orders}",
        f"- filled_sell_orders: {filled_sell_orders}",
        f"- rejected_limit_down_count: {rejected_limit_down_count}",
        f"- risk_event_count: {risk_event_count}",
        f"- consumption_conclusion: {'ready_for_s3b' if go_nogo == 'GO' else 'blocked'}",
        "",
    ]
    _write_markdown(consumption_path, consumption_lines)

    gate_lines = [
        "# S4 Gate Report",
        "",
        f"- trade_date: {trade_date}",
        f"- quality_status: {quality_status}",
        f"- go_nogo: {go_nogo}",
        f"- total_orders: {total_orders}",
        f"- filled_orders: {filled_orders}",
        f"- filled_sell_orders: {filled_sell_orders}",
        f"- rejected_limit_down_count: {rejected_limit_down_count}",
        f"- risk_event_count: {risk_event_count}",
        "",
    ]
    _write_markdown(gate_report_path, gate_lines)

    error_payload = {
        "trade_date": trade_date,
        "error_count": len(errors),
        "errors": errors,
    }
    _write_json(error_manifest_path, error_payload)
    if errors:
        error_manifest_path = artifacts_dir / "error_manifest.json"
        _write_json(error_manifest_path, error_payload)

    if database_path.exists():
        _persist(
            database_path=database_path,
            table_name="trade_records",
            frame=trade_frame,
            delete_trade_date=trade_date,
        )
        _persist(
            database_path=database_path,
            table_name="positions",
            frame=position_frame,
            delete_trade_date=trade_date,
        )
        _persist(
            database_path=database_path,
            table_name="risk_events",
            frame=risk_event_frame,
            delete_trade_date=trade_date,
        )

    return TradeRunResult(
        trade_date=trade_date,
        mode=normalized_mode,
        artifacts_dir=artifacts_dir,
        trade_records_path=trade_records_path,
        positions_path=positions_path,
        risk_events_path=risk_events_path,
        paper_trade_replay_path=replay_path,
        consumption_path=consumption_path,
        gate_report_path=gate_report_path,
        error_manifest_path=error_manifest_path,
        total_orders=total_orders,
        filled_orders=filled_orders,
        risk_event_count=risk_event_count,
        quality_status=quality_status,
        go_nogo=go_nogo,
        has_error=bool(errors),
    )
