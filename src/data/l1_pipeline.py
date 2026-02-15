from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config.config import Config
from src.data.fetcher import FetchAttempt, TuShareFetcher
from src.data.repositories.daily import DailyRepository
from src.data.repositories.limit_list import LimitListRepository
from src.data.repositories.trade_calendars import TradeCalendarsRepository


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


def run_l1_collection(
    *,
    trade_date: str,
    source: str,
    config: Config,
    fetcher: TuShareFetcher | None = None,
) -> L1RunResult:
    if source.lower() != "tushare":
        raise ValueError(f"unsupported source for S0b: {source}")

    effective_fetcher = fetcher or TuShareFetcher()
    artifacts_dir = Path("artifacts") / "spiral-s0b" / trade_date

    repositories = {
        "raw_daily": DailyRepository(config),
        "raw_trade_cal": TradeCalendarsRepository(config),
        "raw_limit_list": LimitListRepository(config),
    }
    raw_counts: dict[str, int] = {}
    errors: list[dict[str, str]] = []
    trade_cal_contains_trade_date = False

    for dataset, repository in repositories.items():
        try:
            rows = repository.fetch(trade_date=trade_date, fetcher=effective_fetcher)
            saved_count = repository.save_to_database(rows)
            repository.save_to_parquet(rows)
            raw_counts[dataset] = saved_count
            if dataset == "raw_trade_cal":
                trade_cal_contains_trade_date = any(
                    str(row.get("trade_date", "")) == trade_date for row in rows
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
    if raw_counts.get("raw_daily", 0) <= 0:
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

    raw_counts_payload = {
        "trade_date": trade_date,
        "source": source,
        "raw_counts": raw_counts,
        "gate_checks": {
            "raw_daily_gt_zero": raw_counts.get("raw_daily", 0) > 0,
            "trade_cal_contains_trade_date": trade_cal_contains_trade_date,
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
