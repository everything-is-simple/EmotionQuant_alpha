"""数据层 L1 采集流水线：按交易日拉取全量 L1 原始数据并落盘。

流程：
1. 确定哪些数据集需要拉取（日频 / 月频 / 半年频）
2. 通过 Repository.fetch() + TuShareFetcher 拉取数据
3. save_to_database() + save_to_parquet() 落盘
4. 评估数据质量门禁（Quality Gate）
5. 输出产物文件（raw_counts / retry_report / quality_gate_report）
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from src.config.config import Config
from src.db.helpers import column_exists as _table_has_column, table_exists as _table_exists
from src.data.fetcher import FetchAttempt, TuShareFetcher
from src.data.repositories.daily_basic import DailyBasicRepository
from src.data.repositories.daily import DailyRepository
from src.data.repositories.index_classify import IndexClassifyRepository
from src.data.repositories.index_daily import IndexDailyRepository
from src.data.repositories.index_member import IndexMemberRepository
from src.data.repositories.limit_list import LimitListRepository
from src.data.repositories.base import DuckDBLockRecoveryError
from src.data.repositories.stock_basic import StockBasicRepository
from src.data.repositories.trade_calendars import TradeCalendarsRepository
from src.data.quality_gate import STATUS_BLOCKED, evaluate_data_quality_gate
from src.data.quality_store import (
    decision_to_json,
    init_quality_context,
    persist_quality_outputs,
)


@dataclass(frozen=True)
class L1RunResult:
    trade_date: str
    source: str
    artifacts_dir: Path
    raw_counts: dict[str, int]
    trade_cal_contains_trade_date: bool
    has_error: bool
    error_manifest_path: Path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _write_fetch_retry_report(path: Path, attempts: list[FetchAttempt]) -> None:
    lines = [
        "# Fetch Retry Report",
        "",
        f"- total_attempts: {len(attempts)}",
    ]
    if not attempts:
        lines.append("- details: none")
    else:
        lines.append("- details:")
        for item in attempts:
            detail = f"  - api={item.api_name} attempt={item.attempt} status={item.status}"
            if item.error:
                detail = f"{detail} error={item.error}"
            lines.append(detail)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_l1_quality_gate_report(
    path: Path,
    *,
    decision_payload: dict[str, Any],
    report_rows: list[dict[str, Any]],
) -> None:
    lines = [
        "# L1 Quality Gate Report",
        "",
        f"- trade_date: {decision_payload.get('trade_date', '')}",
        f"- status: {decision_payload.get('status', '')}",
        f"- is_ready: {str(bool(decision_payload.get('is_ready', False))).lower()}",
        f"- coverage_ratio: {float(decision_payload.get('coverage_ratio', 0.0)):.4f}",
        f"- max_stale_days: {int(decision_payload.get('max_stale_days', 0) or 0)}",
        f"- cross_day_consistent: {str(bool(decision_payload.get('cross_day_consistent', False))).lower()}",
        "",
        "## Issues",
    ]
    issues = decision_payload.get("issues", [])
    if isinstance(issues, list) and issues:
        lines.extend([f"- {str(item)}" for item in issues])
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings"])
    warnings = decision_payload.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        lines.extend([f"- {str(item)}" for item in warnings])
    else:
        lines.append("- none")
    lines.extend(["", "## Checks"])
    for row in report_rows:
        lines.append(
            f"- {row.get('check_item', '')}: status={row.get('status', '')} "
            f"expected={row.get('expected_value', '')} actual={row.get('actual_value', '')} "
            f"action={row.get('action', '')}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _month_anchor(trade_date: str) -> str:
    return f"{trade_date[:6]}01"


def _half_year_anchor(trade_date: str) -> str:
    year = trade_date[:4]
    month = int(trade_date[4:6])
    return f"{year}0101" if month <= 6 else f"{year}0701"




def _has_snapshot_for_period(
    connection: duckdb.DuckDBPyConnection,
    *,
    table_name: str,
    period_prefix: str,
) -> bool:
    if not _table_exists(connection, table_name):
        return False
    if not _table_has_column(connection, table_name, "trade_date"):
        return False
    row = connection.execute(
        f"SELECT COUNT(*) FROM {table_name} WHERE CAST(trade_date AS VARCHAR) LIKE ?",
        [f"{period_prefix}%"],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _dataset_schedule(dataset: str) -> str:
    if dataset in {"raw_index_member", "raw_stock_basic"}:
        return "monthly"
    if dataset == "raw_index_classify":
        return "half_yearly"
    return "daily"


def _resolve_snapshot_trade_date(dataset: str, trade_date: str) -> str:
    schedule = _dataset_schedule(dataset)
    if schedule == "monthly":
        return _month_anchor(trade_date)
    if schedule == "half_yearly":
        return _half_year_anchor(trade_date)
    return trade_date


def _should_fetch_dataset(
    connection: duckdb.DuckDBPyConnection | None,
    *,
    dataset: str,
    trade_date: str,
) -> bool:
    schedule = _dataset_schedule(dataset)
    if schedule == "daily":
        return True
    if connection is None:
        return True
    snapshot_trade_date = _resolve_snapshot_trade_date(dataset, trade_date)
    return not _has_snapshot_for_period(
        connection,
        table_name=dataset,
        period_prefix=snapshot_trade_date[:6],
    )


def run_l1_collection(
    *,
    trade_date: str,
    source: str,
    config: Config,
    fetcher: TuShareFetcher | None = None,
) -> L1RunResult:
    """执行单个交易日的 L1 数据采集。

    依次拉取 8 个数据集（daily / daily_basic / index_daily / limit_list /
    trade_cal / stock_basic / index_member / index_classify），
    落盘后评估 Quality Gate，输出产物文件。
    """
    if source.lower() != "tushare":
        raise ValueError(f"unsupported source for S0b: {source}")

    effective_fetcher = fetcher or TuShareFetcher(config=config)
    artifacts_dir = Path("artifacts") / "spiral-s0b" / trade_date

    repositories = {
        "raw_daily": DailyRepository(config),
        "raw_daily_basic": DailyBasicRepository(config),
        "raw_index_daily": IndexDailyRepository(config),
        "raw_index_member": IndexMemberRepository(config),
        "raw_index_classify": IndexClassifyRepository(config),
        "raw_stock_basic": StockBasicRepository(config),
        "raw_trade_cal": TradeCalendarsRepository(config),
        "raw_limit_list": LimitListRepository(config),
    }
    raw_counts: dict[str, int] = {}
    fetch_plan: dict[str, dict[str, str | bool]] = {}
    errors: list[dict[str, str]] = []
    trade_cal_contains_trade_date = False
    trade_cal_is_open: bool | None = None

    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    thresholds = init_quality_context(database_path, config=config)
    min_coverage_ratio = float(thresholds["min_coverage_ratio"])
    stale_hard_limit_days = int(thresholds["stale_hard_limit_days"])

    for dataset, repository in repositories.items():
        snapshot_trade_date = _resolve_snapshot_trade_date(dataset, trade_date)
        should_fetch = True
        if database_path.exists():
            try:
                with duckdb.connect(str(database_path), read_only=True) as snapshot_connection:
                    should_fetch = _should_fetch_dataset(
                        snapshot_connection,
                        dataset=dataset,
                        trade_date=trade_date,
                    )
            except Exception:
                should_fetch = True
        fetch_plan[dataset] = {
            "schedule": _dataset_schedule(dataset),
            "snapshot_trade_date": snapshot_trade_date,
            "fetched": should_fetch,
        }
        if not should_fetch:
            raw_counts[dataset] = 0
            continue
        try:
            rows = repository.fetch(
                trade_date=trade_date,
                fetcher=effective_fetcher,
                snapshot_trade_date=snapshot_trade_date,
            )
            saved_count = repository.save_to_database(rows)
            repository.save_to_parquet(rows)
            raw_counts[dataset] = saved_count
            if dataset == "raw_trade_cal":
                trade_cal_contains_trade_date = any(
                    str(row.get("trade_date", "")) == trade_date for row in rows
                )
                for row in rows:
                    if str(row.get("trade_date", "")) != trade_date:
                        continue
                    marker = row.get("is_open", row.get("is_trading"))
                    marker_text = str(marker).strip().lower()
                    trade_cal_is_open = marker_text in {"1", "true", "y", "yes"}
                    break
        except DuckDBLockRecoveryError as exc:
            raw_counts[dataset] = 0
            errors.append(
                {
                    "dataset": dataset,
                    "error_type": "duckdb_lock_recovery_exhausted",
                    "message": exc.last_error_message,
                    "lock_holder_pid": exc.lock_holder_pid or "unknown",
                    "retry_attempts": str(exc.retry_attempts),
                    "wait_seconds_total": f"{exc.wait_seconds_total:.3f}",
                }
            )
        except Exception as exc:  # pragma: no cover - covered via contract test
            raw_counts[dataset] = 0
            errors.append(
                {
                    "dataset": dataset,
                    "error_type": "fetch_or_persist_error",
                    "message": str(exc),
                }
            )

    gate_issues: list[str] = []
    if trade_cal_is_open is not False and raw_counts.get("raw_daily", 0) <= 0:
        gate_issues.append("raw_daily_empty")
    if not trade_cal_contains_trade_date:
        gate_issues.append("trade_cal_missing_trade_date")

    for issue in gate_issues:
        errors.append(
            {
                "dataset": "gate",
                "error_type": "gate_violation",
                "message": issue,
            }
        )

    if trade_cal_is_open is False:
        required_datasets = ("raw_trade_cal",)
        optional_datasets = ("raw_daily", "raw_index_daily", "raw_daily_basic", "raw_limit_list")
    else:
        required_datasets = ("raw_daily", "raw_trade_cal", "raw_index_daily")
        optional_datasets = ("raw_daily_basic", "raw_limit_list")
    source_trade_dates = {
        dataset: str(fetch_plan.get(dataset, {}).get("snapshot_trade_date", trade_date))
        for dataset in required_datasets
    }
    required_covered = {
        dataset: raw_counts.get(dataset, 0) > 0
        for dataset in required_datasets
    }
    coverage_ratio = float(sum(1 for covered in required_covered.values() if covered)) / max(
        float(len(required_datasets)),
        1.0,
    )
    quality_by_dataset = {
        dataset: ("normal" if covered else "stale")
        for dataset, covered in required_covered.items()
    }
    stale_days_by_dataset = {
        dataset: (0 if covered else 1)
        for dataset, covered in required_covered.items()
    }
    for dataset in optional_datasets:
        optional_covered = raw_counts.get(dataset, 0) > 0
        quality_by_dataset[dataset] = "normal" if optional_covered else "cold_start"
        stale_days_by_dataset[dataset] = 0

    decision = evaluate_data_quality_gate(
        trade_date=trade_date,
        coverage_ratio=coverage_ratio,
        source_trade_dates=source_trade_dates,
        quality_by_dataset=quality_by_dataset,
        stale_days_by_dataset=stale_days_by_dataset,
        min_coverage=min_coverage_ratio,
        stale_hard_limit=stale_hard_limit_days,
    )
    if decision.status == STATUS_BLOCKED and not any(
        item.get("error_type") == "readiness_gate_blocked" for item in errors
    ):
        errors.append(
            {
                "dataset": "gate",
                "error_type": "readiness_gate_blocked",
                "message": ";".join(decision.issues) if decision.issues else "data_readiness_blocked",
            }
        )

    report_rows: list[dict[str, Any]] = []
    for dataset in ("raw_daily", "raw_trade_cal", "raw_index_daily", "raw_daily_basic", "raw_limit_list"):
        actual_count = int(raw_counts.get(dataset, 0))
        expected_value = ">0" if dataset in required_datasets else ">=0"
        if dataset in required_datasets:
            status = "PASS" if actual_count > 0 else "FAIL"
            action = "continue" if actual_count > 0 else "block"
        else:
            status = "PASS" if actual_count > 0 else "WARN"
            action = "continue" if actual_count > 0 else "fallback"
        report_rows.append(
            {
                "check_item": f"l1_{dataset}_count",
                "expected_value": expected_value,
                "actual_value": str(actual_count),
                "deviation": 0.0 if status != "FAIL" else 1.0,
                "status": status,
                "gate_status": decision.status,
                "affected_layers": "L1",
                "action": action,
            }
        )
    report_rows.append(
        {
            "check_item": "l1_readiness_gate",
            "expected_value": "ready/degraded",
            "actual_value": decision.status,
            "deviation": max(0.0, min_coverage_ratio - coverage_ratio),
            "status": "PASS" if decision.status == "ready" else ("WARN" if decision.status == "degraded" else "FAIL"),
            "gate_status": decision.status,
            "affected_layers": "L1",
            "action": "continue" if decision.is_ready else "block",
        }
    )
    persist_quality_outputs(
        database_path,
        decision=decision,
        report_rows=report_rows,
        config=config,
    )
    _write_l1_quality_gate_report(
        artifacts_dir / "l1_quality_gate_report.md",
        decision_payload=decision_to_json(decision),
        report_rows=report_rows,
    )

    raw_counts_payload = {
        "trade_date": trade_date,
        "source": source,
        "raw_counts": raw_counts,
        "fetch_plan": fetch_plan,
        "gate_checks": {
            "raw_daily_gt_zero": raw_counts.get("raw_daily", 0) > 0,
            "trade_cal_contains_trade_date": trade_cal_contains_trade_date,
            "trade_cal_is_open": trade_cal_is_open,
        },
    }
    _write_json(artifacts_dir / "raw_counts.json", raw_counts_payload)
    _write_fetch_retry_report(
        artifacts_dir / "fetch_retry_report.md",
        list(effective_fetcher.retry_report),
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

    return L1RunResult(
        trade_date=trade_date,
        source=source,
        artifacts_dir=artifacts_dir,
        raw_counts=raw_counts,
        trade_cal_contains_trade_date=trade_cal_contains_trade_date,
        has_error=bool(errors),
        error_manifest_path=manifest_path,
    )
