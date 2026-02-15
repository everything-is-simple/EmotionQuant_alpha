from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config
from src.data.models.snapshots import IndustrySnapshot, MarketSnapshot


@dataclass(frozen=True)
class L2RunResult:
    trade_date: str
    source: str
    artifacts_dir: Path
    market_snapshot_count: int
    industry_snapshot_count: int
    has_error: bool
    error_manifest_path: Path
    canary_report_path: Path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _normalize_stock_code(row: pd.Series) -> str:
    stock_code = str(row.get("stock_code", "")).strip()
    if stock_code:
        return stock_code
    ts_code = str(row.get("ts_code", "")).strip()
    if "." in ts_code:
        return ts_code.split(".", maxsplit=1)[0]
    return ts_code or "UNKNOWN"


def _build_market_snapshot(
    *,
    trade_date: str,
    daily: pd.DataFrame,
    limit_list: pd.DataFrame,
) -> MarketSnapshot:
    working = daily.copy()
    for column in ("open", "close", "amount"):
        if column not in working.columns:
            working[column] = 0.0
        working[column] = pd.to_numeric(working[column], errors="coerce").fillna(0.0)

    pct = (working["close"] - working["open"]) / working["open"].replace(0, pd.NA)
    pct = pct.fillna(0.0)

    limit_rows = limit_list.copy() if not limit_list.empty else limit_list
    if not limit_rows.empty and "limit_type" in limit_rows.columns:
        limit_up_count = int((limit_rows["limit_type"].astype(str) == "U").sum())
        limit_down_count = int((limit_rows["limit_type"].astype(str) == "D").sum())
    else:
        limit_up_count = 0
        limit_down_count = 0

    return MarketSnapshot(
        trade_date=trade_date,
        total_stocks=int(len(working)),
        rise_count=int((working["close"] > working["open"]).sum()),
        fall_count=int((working["close"] < working["open"]).sum()),
        flat_count=int((working["close"] == working["open"]).sum()),
        strong_up_count=int((pct >= 0.03).sum()),
        strong_down_count=int((pct <= -0.03).sum()),
        limit_up_count=limit_up_count,
        limit_down_count=limit_down_count,
        touched_limit_up=limit_up_count,
        pct_chg_std=float(pct.std(ddof=0)),
        amount_volatility=float(working["amount"].std(ddof=0)),
        data_quality="normal",
        stale_days=0,
        source_trade_date=trade_date,
    )


def _build_industry_snapshot(
    *,
    trade_date: str,
    daily: pd.DataFrame,
    limit_list: pd.DataFrame,
) -> IndustrySnapshot:
    working = daily.copy()
    for column in ("open", "close", "amount", "vol"):
        if column not in working.columns:
            working[column] = 0.0
        working[column] = pd.to_numeric(working[column], errors="coerce").fillna(0.0)

    pct = (working["close"] - working["open"]) / working["open"].replace(0, pd.NA)
    pct = pct.fillna(0.0)
    ranking = working.assign(pct=pct).sort_values("pct", ascending=False).head(5)
    top5_codes = [_normalize_stock_code(row) for _, row in ranking.iterrows()]
    top5_pct_chg = [float(round(float(value) * 100.0, 4)) for value in ranking["pct"]]

    limit_rows = limit_list.copy() if not limit_list.empty else limit_list
    if not limit_rows.empty and "limit_type" in limit_rows.columns:
        limit_up_count = int((limit_rows["limit_type"].astype(str) == "U").sum())
        limit_down_count = int((limit_rows["limit_type"].astype(str) == "D").sum())
    else:
        limit_up_count = 0
        limit_down_count = 0

    return IndustrySnapshot(
        trade_date=trade_date,
        industry_code="ALL",
        industry_name="全市场聚合",
        stock_count=int(len(working)),
        rise_count=int((working["close"] > working["open"]).sum()),
        fall_count=int((working["close"] < working["open"]).sum()),
        flat_count=int((working["close"] == working["open"]).sum()),
        industry_close=float(working["close"].mean()),
        industry_pct_chg=float(pct.mean() * 100.0),
        industry_amount=float(working["amount"].sum()),
        industry_turnover=float(working["vol"].sum()),
        limit_up_count=limit_up_count,
        limit_down_count=limit_down_count,
        top5_codes=top5_codes,
        top5_pct_chg=top5_pct_chg,
        top5_limit_up=min(limit_up_count, len(top5_codes)),
        data_quality="normal",
        stale_days=0,
        source_trade_date=trade_date,
    )


def _persist_snapshot_table(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
) -> int:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database_path)) as connection:
        connection.register("incoming_df", frame)
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} "
            "AS SELECT * FROM incoming_df WHERE 1=0"
        )
        connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_df")
        connection.unregister("incoming_df")
    return int(len(frame))


def _write_canary_report(
    *,
    path: Path,
    trade_date: str,
    market_snapshot_count: int,
    market_has_quality_fields: bool,
    industry_snapshot_count: int,
    errors: list[dict[str, str]],
) -> None:
    status = "PASS" if not errors else "FAIL"
    lines = [
        "# S0 Canary Report",
        "",
        f"- trade_date: {trade_date}",
        f"- status: {status}",
        f"- market_snapshot_count: {market_snapshot_count}",
        f"- industry_snapshot_count: {industry_snapshot_count}",
        f"- market_has_quality_fields: {str(market_has_quality_fields).lower()}",
        f"- error_count: {len(errors)}",
        "",
        "## Checks",
        f"- market_snapshot_exists: {'PASS' if market_snapshot_count > 0 else 'FAIL'}",
        f"- market_quality_fields: {'PASS' if market_has_quality_fields else 'FAIL'}",
        "",
        "## Errors",
    ]
    if not errors:
        lines.append("- none")
    else:
        for item in errors:
            lines.append(
                f"- [{item['error_level']}] {item['step']}: {item['message']}"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_l2_snapshot(
    *,
    trade_date: str,
    source: str,
    config: Config,
) -> L2RunResult:
    if source.lower() != "tushare":
        raise ValueError(f"unsupported source for S0c: {source}")

    artifacts_dir = Path("artifacts") / "spiral-s0c" / trade_date
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    parquet_root = Path(config.parquet_path) / "l2"
    errors: list[dict[str, str]] = []
    market_snapshot_count = 0
    industry_snapshot_count = 0
    market_has_quality_fields = False

    def add_error(level: str, step: str, message: str) -> None:
        errors.append(
            {
                "error_level": level,
                "step": step,
                "trade_date": trade_date,
                "message": message,
            }
        )

    try:
        if not database_path.exists():
            add_error("P0", "load_l1", "duckdb_not_found")
            raise RuntimeError("L1 database not found")

        with duckdb.connect(str(database_path), read_only=True) as connection:
            if not _table_exists(connection, "raw_daily"):
                add_error("P0", "load_l1", "raw_daily_table_missing")
                raise RuntimeError("raw_daily table missing")
            daily = connection.execute(
                "SELECT * FROM raw_daily WHERE trade_date = ?",
                [trade_date],
            ).df()
            if _table_exists(connection, "raw_limit_list"):
                limit_list = connection.execute(
                    "SELECT * FROM raw_limit_list WHERE trade_date = ?",
                    [trade_date],
                ).df()
            else:
                add_error("P1", "load_l1", "raw_limit_list_table_missing")
                limit_list = pd.DataFrame()

        if daily.empty:
            add_error("P0", "build_market_snapshot", "raw_daily_empty")
            raise RuntimeError("raw_daily is empty for trade_date")

        market_snapshot = _build_market_snapshot(
            trade_date=trade_date,
            daily=daily,
            limit_list=limit_list,
        )
        industry_snapshot = _build_industry_snapshot(
            trade_date=trade_date,
            daily=daily,
            limit_list=limit_list,
        )

        market_frame = pd.DataFrame.from_records([market_snapshot.to_storage_record()])
        industry_frame = pd.DataFrame.from_records([industry_snapshot.to_storage_record()])

        market_snapshot_count = _persist_snapshot_table(
            database_path=database_path,
            table_name="market_snapshot",
            frame=market_frame,
        )
        industry_snapshot_count = _persist_snapshot_table(
            database_path=database_path,
            table_name="industry_snapshot",
            frame=industry_frame,
        )

        parquet_root.mkdir(parents=True, exist_ok=True)
        market_frame.to_parquet(parquet_root / "market_snapshot.parquet", index=False)
        industry_frame.to_parquet(parquet_root / "industry_snapshot.parquet", index=False)

        artifacts_dir.mkdir(parents=True, exist_ok=True)
        market_frame.to_parquet(artifacts_dir / "market_snapshot_sample.parquet", index=False)
        industry_frame.to_parquet(
            artifacts_dir / "industry_snapshot_sample.parquet",
            index=False,
        )

        required_fields = {"data_quality", "stale_days", "source_trade_date"}
        market_has_quality_fields = required_fields <= set(market_frame.columns)
        if not market_has_quality_fields:
            add_error("P1", "gate", "market_snapshot_quality_fields_missing")

        if market_snapshot_count <= 0:
            add_error("P0", "gate", "market_snapshot_empty")
    except Exception as exc:  # pragma: no cover - validated through contract tests
        if not errors:
            add_error("P0", "run_l2_snapshot", str(exc))

    canary_report_path = artifacts_dir / "s0_canary_report.md"
    _write_canary_report(
        path=canary_report_path,
        trade_date=trade_date,
        market_snapshot_count=market_snapshot_count,
        market_has_quality_fields=market_has_quality_fields,
        industry_snapshot_count=industry_snapshot_count,
        errors=errors,
    )

    error_manifest_payload = {
        "trade_date": trade_date,
        "source": source,
        "error_count": len(errors),
        "errors": errors,
    }
    sample_path = artifacts_dir / "error_manifest_sample.json"
    _write_json(sample_path, error_manifest_payload)
    if errors:
        manifest_path = artifacts_dir / "error_manifest.json"
        _write_json(manifest_path, error_manifest_payload)
    else:
        manifest_path = sample_path

    return L2RunResult(
        trade_date=trade_date,
        source=source,
        artifacts_dir=artifacts_dir,
        market_snapshot_count=market_snapshot_count,
        industry_snapshot_count=industry_snapshot_count,
        has_error=bool(errors),
        error_manifest_path=manifest_path,
        canary_report_path=canary_report_path,
    )
