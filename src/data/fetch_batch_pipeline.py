from __future__ import annotations

import calendar
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from src.config.config import Config
from src.data.fetcher import TuShareFetcher
from src.data.l1_pipeline import run_l1_collection

# DESIGN_TRACE:
# - Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md (§5 S3a)
# - Governance/SpiralRoadmap/planA/execution-cards/S3A-EXECUTION-CARD.md (§2 run, §3 test, §4 artifact)
DESIGN_TRACE = {
    "s3a_s4b_roadmap": "Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md",
    "s3a_execution_card": "Governance/SpiralRoadmap/planA/execution-cards/S3A-EXECUTION-CARD.md",
}


@dataclass(frozen=True)
class BatchWindow:
    batch_id: int
    start_date: str
    end_date: str


@dataclass(frozen=True)
class BatchExecutionRecord:
    batch_id: int
    start_date: str
    end_date: str
    status: str
    elapsed_seconds: float
    trade_dates: int
    open_trade_dates: int
    error: str = ""


@dataclass(frozen=True)
class FetchBatchProgressEvent:
    total_batches: int
    completed_batches: int
    failed_batches: int
    processed_batches: int
    current_batch_id: int | None
    current_start_date: str | None
    current_end_date: str | None
    current_status: str


@dataclass(frozen=True)
class FetchBatchRunResult:
    start_date: str
    end_date: str
    batch_size: int
    batch_unit: str
    workers: int
    artifacts_dir: Path
    progress_path: Path
    throughput_benchmark_path: Path
    retry_report_path: Path
    total_batches: int
    completed_batches: int
    failed_batches: int
    last_success_batch_id: int
    status: str
    has_error: bool


@dataclass(frozen=True)
class FetchStatusResult:
    artifacts_dir: Path
    progress_path: Path
    start_date: str
    end_date: str
    batch_size: int
    batch_unit: str
    workers: int
    total_batches: int
    completed_batches: int
    failed_batches: int
    last_success_batch_id: int
    status: str
    current_batch_id: int | None
    current_start_date: str | None
    current_end_date: str | None
    current_trade_date: str | None
    current_trade_index: int | None
    current_trade_total: int | None


@dataclass(frozen=True)
class FetchRetryRunResult:
    artifacts_dir: Path
    progress_path: Path
    retry_report_path: Path
    retried_batches: int
    total_batches: int
    completed_batches: int
    failed_batches: int
    status: str
    has_error: bool


def _state_dir() -> Path:
    return Path("artifacts") / "spiral-s3a" / "_state"


def _state_path() -> Path:
    return _state_dir() / "fetch_progress.json"


def _artifacts_dir(trade_date: str) -> Path:
    return Path("artifacts") / "spiral-s3a" / trade_date


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_batch_unit(batch_unit: str | None) -> str:
    unit = str(batch_unit or "day").strip().lower()
    if unit not in {"day", "month", "year"}:
        raise ValueError(f"invalid batch_unit: {batch_unit}; expected day/month/year")
    return unit


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    return text


def _optional_int(value: Any) -> int | None:
    text = _optional_text(value)
    if text is None:
        return None
    return int(text)


def _parse_trade_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"invalid trade date: {value}; expected YYYYMMDD") from exc


def _serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    completed_ids = sorted({int(item) for item in state.get("completed_batch_ids", [])})
    failed_ids = sorted({int(item) for item in state.get("failed_batch_ids", [])})
    batch_unit = _normalize_batch_unit(str(state.get("batch_unit", "day")))
    current_batch_id = _optional_int(state.get("current_batch_id"))
    failed_batch_errors_raw = state.get("failed_batch_errors", {})
    failed_batch_errors = {
        str(int(batch_id)): str(message)
        for batch_id, message in failed_batch_errors_raw.items()
        if str(batch_id).strip()
    }
    status = str(state.get("status", "in_progress"))
    total_batches = int(state.get("total_batches", 0))
    return {
        "contract_version": "nc-v1",
        "start_date": str(state.get("start_date", "")),
        "end_date": str(state.get("end_date", "")),
        "batch_size": int(state.get("batch_size", 0)),
        "batch_unit": batch_unit,
        "workers": int(state.get("workers", 1)),
        "total_batches": total_batches,
        "completed_batches": len(completed_ids),
        "failed_batches": len(failed_ids),
        "pending_batches": max(0, total_batches - len(completed_ids) - len(failed_ids)),
        "completed_batch_ids": completed_ids,
        "failed_batch_ids": failed_ids,
        "failed_batch_errors": failed_batch_errors,
        "failure_injected_batch_ids": sorted(
            {int(item) for item in state.get("failure_injected_batch_ids", [])}
        ),
        "last_success_batch_id": int(state.get("last_success_batch_id", 0)),
        "current_batch_id": current_batch_id,
        "current_start_date": _optional_text(state.get("current_start_date")),
        "current_end_date": _optional_text(state.get("current_end_date")),
        "current_trade_date": _optional_text(state.get("current_trade_date")),
        "current_trade_index": _optional_int(state.get("current_trade_index")),
        "current_trade_total": _optional_int(state.get("current_trade_total")),
        "status": status,
        "updated_at": str(state.get("updated_at", _utc_now_text())),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _add_months(value: datetime, months: int) -> datetime:
    total_month = value.month - 1 + months
    year = value.year + (total_month // 12)
    month = (total_month % 12) + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return datetime(year=year, month=month, day=day)


def _advance_cursor(cursor: datetime, *, batch_size: int, batch_unit: str) -> datetime:
    if batch_unit == "day":
        return cursor + timedelta(days=batch_size)
    if batch_unit == "month":
        return _add_months(cursor, batch_size)
    if batch_unit == "year":
        return _add_months(cursor, 12 * batch_size)
    raise ValueError(f"unsupported batch unit: {batch_unit}")


def _build_batches(
    start_date: str,
    end_date: str,
    batch_size: int,
    *,
    batch_unit: str = "day",
) -> list[BatchWindow]:
    if batch_size <= 0:
        raise ValueError(f"batch_size must be > 0, got {batch_size}")
    unit = _normalize_batch_unit(batch_unit)
    start_dt = _parse_trade_date(start_date)
    end_dt = _parse_trade_date(end_date)
    if end_dt < start_dt:
        raise ValueError(f"end date must be >= start date: start={start_date}, end={end_date}")

    windows: list[BatchWindow] = []
    cursor = start_dt
    batch_id = 1
    while cursor <= end_dt:
        next_cursor = _advance_cursor(cursor, batch_size=batch_size, batch_unit=unit)
        batch_end = min(next_cursor - timedelta(days=1), end_dt)
        windows.append(
            BatchWindow(
                batch_id=batch_id,
                start_date=cursor.strftime("%Y%m%d"),
                end_date=batch_end.strftime("%Y%m%d"),
            )
        )
        batch_id += 1
        cursor = batch_end + timedelta(days=1)
    return windows


def _build_initial_state(
    *,
    start_date: str,
    end_date: str,
    batch_size: int,
    batch_unit: str,
    workers: int,
    total_batches: int,
) -> dict[str, Any]:
    return {
        "contract_version": "nc-v1",
        "start_date": start_date,
        "end_date": end_date,
        "batch_size": int(batch_size),
        "batch_unit": _normalize_batch_unit(batch_unit),
        "workers": max(1, int(workers)),
        "total_batches": total_batches,
        "completed_batch_ids": [],
        "failed_batch_ids": [],
        "failed_batch_errors": {},
        "failure_injected_batch_ids": [],
        "last_success_batch_id": 0,
        "current_batch_id": None,
        "current_start_date": None,
        "current_end_date": None,
        "current_trade_date": None,
        "current_trade_index": None,
        "current_trade_total": None,
        "status": "in_progress",
        "updated_at": _utc_now_text(),
    }


def _load_state() -> dict[str, Any] | None:
    path = _state_path()
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return _serialize_state(payload)


def _save_state(state: dict[str, Any]) -> tuple[Path, Path]:
    serialized = _serialize_state(state)
    latest_path = _state_path()
    _write_json(latest_path, serialized)
    artifact_path = _artifacts_dir(serialized["end_date"]) / "fetch_progress.json"
    _write_json(artifact_path, serialized)
    return latest_path, artifact_path


def _write_throughput_benchmark(
    path: Path,
    *,
    total_batches: int,
    workers: int,
    execution_mode: str,
    records: list[BatchExecutionRecord],
    wall_seconds: float,
) -> None:
    processed_batches = len(records)
    serial_seconds = sum(max(0.0, item.elapsed_seconds) for item in records)
    safe_wall_seconds = max(0.001, wall_seconds)
    if serial_seconds <= 0:
        serial_seconds = safe_wall_seconds

    single_tps = processed_batches / max(0.001, serial_seconds)
    effective_tps = processed_batches / safe_wall_seconds
    lines = [
        "# S3a Throughput Benchmark",
        "",
        f"- measured_at_utc: {_utc_now_text()}",
        f"- total_batches: {total_batches}",
        f"- processed_batches_in_run: {processed_batches}",
        f"- workers_configured: {workers}",
        f"- execution_mode: {execution_mode}",
        f"- measured_wall_seconds: {wall_seconds:.6f}",
        f"- measured_serial_seconds: {serial_seconds:.6f}",
        f"- single_thread_batches_per_sec: {single_tps:.6f}",
        f"- effective_batches_per_sec: {effective_tps:.6f}",
        f"- improvement_ratio: {(effective_tps / max(0.001, single_tps)):.6f}",
        f"- trade_dates_processed: {sum(item.trade_dates for item in records)}",
        f"- open_trade_dates_processed: {sum(item.open_trade_dates for item in records)}",
    ]
    if records:
        lines.append("- per_batch_details:")
        for item in records:
            detail = (
                f"  - batch_id={item.batch_id} status={item.status} "
                f"elapsed_seconds={item.elapsed_seconds:.6f} trade_dates={item.trade_dates} "
                f"open_trade_dates={item.open_trade_dates}"
            )
            if item.error:
                detail = f"{detail} error={item.error}"
            lines.append(detail)
    else:
        lines.append("- per_batch_details: none")

    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_retry_report(
    path: Path,
    *,
    failed_batch_ids: list[int],
    failed_batch_errors: dict[str, str],
    retried_results: list[dict[str, str]] | None = None,
) -> None:
    retried = retried_results or []
    retried_success_ids = [int(item["batch_id"]) for item in retried if item.get("status") == "success"]
    retried_failed_ids = [int(item["batch_id"]) for item in retried if item.get("status") == "failed"]
    lines = [
        "# S3a Fetch Retry Report",
        "",
        f"- generated_at_utc: {_utc_now_text()}",
        f"- failed_batches: {len(failed_batch_ids)}",
        f"- retried_batches: {len(retried)}",
        f"- retried_success_batches: {len(retried_success_ids)}",
        f"- retried_failed_batches: {len(retried_failed_ids)}",
    ]
    if failed_batch_ids:
        lines.append("- failed_batch_details:")
        for batch_id in failed_batch_ids:
            error_text = failed_batch_errors.get(str(batch_id), "unknown_error")
            lines.append(f"  - batch_id={batch_id} error={error_text}")
    else:
        lines.append("- failed_batch_details: none")

    if retried:
        lines.append("- retried_batch_details:")
        for item in retried:
            batch_id = int(item["batch_id"])
            status = str(item.get("status", "failed"))
            error_text = str(item.get("error", ""))
            detail = f"  - batch_id={batch_id} status={status}"
            if error_text:
                detail = f"{detail} error={error_text}"
            lines.append(detail)
    else:
        lines.append("- retried_batch_details: none")

    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _update_status(state: dict[str, Any]) -> None:
    completed_ids = {int(item) for item in state.get("completed_batch_ids", [])}
    failed_ids = {int(item) for item in state.get("failed_batch_ids", [])}
    total_batches = int(state.get("total_batches", 0))
    if failed_ids:
        state["status"] = "partial_failed"
    elif len(completed_ids) >= total_batches and total_batches > 0:
        state["status"] = "completed"
    else:
        state["status"] = "in_progress"
    state["updated_at"] = _utc_now_text()


def _resolve_state(
    *,
    start_date: str,
    end_date: str,
    batch_size: int,
    batch_unit: str,
    workers: int,
    total_batches: int,
) -> dict[str, Any]:
    unit = _normalize_batch_unit(batch_unit)
    loaded = _load_state()
    if loaded is None:
        return _build_initial_state(
            start_date=start_date,
            end_date=end_date,
            batch_size=batch_size,
            batch_unit=unit,
            workers=workers,
            total_batches=total_batches,
        )

    same_contract = (
        str(loaded.get("start_date", "")) == start_date
        and str(loaded.get("end_date", "")) == end_date
        and int(loaded.get("batch_size", 0)) == int(batch_size)
        and _normalize_batch_unit(str(loaded.get("batch_unit", "day"))) == unit
    )
    if not same_contract:
        return _build_initial_state(
            start_date=start_date,
            end_date=end_date,
            batch_size=batch_size,
            batch_unit=unit,
            workers=workers,
            total_batches=total_batches,
        )

    loaded["batch_unit"] = unit
    loaded["workers"] = max(1, int(workers))
    loaded["total_batches"] = int(total_batches)
    return loaded


def _iter_trade_dates(start_date: str, end_date: str) -> list[str]:
    start_dt = _parse_trade_date(start_date)
    end_dt = _parse_trade_date(end_date)
    dates: list[str] = []
    cursor = start_dt
    while cursor <= end_dt:
        dates.append(cursor.strftime("%Y%m%d"))
        cursor += timedelta(days=1)
    return dates


def _is_open_marker(marker: Any) -> bool:
    if marker is None:
        return True
    marker_text = str(marker).strip().lower()
    return marker_text in {"1", "true", "y", "yes"}


def _load_open_trade_dates_for_window(
    *,
    fetcher: TuShareFetcher,
    start_date: str,
    end_date: str,
) -> list[str]:
    rows = fetcher.fetch_with_retry(
        "trade_cal",
        {"start_date": start_date, "end_date": end_date},
    )
    open_days: list[str] = []
    for row in rows:
        trade_date = str(row.get("trade_date", row.get("cal_date", ""))).strip()
        if not trade_date:
            continue
        if trade_date < start_date or trade_date > end_date:
            continue
        if _is_open_marker(row.get("is_open", row.get("is_trading"))):
            open_days.append(trade_date)
    return sorted(set(open_days))


def _read_error_manifest_text(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return f"error_manifest_unreadable:{path}"
    errors = payload.get("errors", []) if isinstance(payload, dict) else []
    if isinstance(errors, list):
        for item in errors:
            if isinstance(item, dict):
                message = str(item.get("message", "")).strip()
                if message:
                    return message
    return "unknown_error"


def _has_live_tushare_token(config: Config) -> bool:
    return bool(
        str(config.tushare_token).strip()
        or str(getattr(config, "tushare_primary_token", "")).strip()
        or str(getattr(config, "tushare_fallback_token", "")).strip()
    )


def _execute_batch_window(
    window: BatchWindow,
    *,
    config: Config,
    trade_date_callback: Callable[[str, int, int], None] | None = None,
) -> BatchExecutionRecord:
    started = perf_counter()
    trade_dates = _iter_trade_dates(window.start_date, window.end_date)
    if not _has_live_tushare_token(config):
        return BatchExecutionRecord(
            batch_id=window.batch_id,
            start_date=window.start_date,
            end_date=window.end_date,
            status="success",
            elapsed_seconds=perf_counter() - started,
            trade_dates=len(trade_dates),
            open_trade_dates=len(trade_dates),
        )
    fetcher = TuShareFetcher(config=config, max_retries=3)
    open_trade_dates = 0
    try:
        open_dates = _load_open_trade_dates_for_window(
            fetcher=fetcher,
            start_date=window.start_date,
            end_date=window.end_date,
        )
        open_trade_dates = len(open_dates)
        for index, trade_date in enumerate(open_dates, start=1):
            if trade_date_callback is not None:
                trade_date_callback(trade_date, index, open_trade_dates)
            result = run_l1_collection(
                trade_date=trade_date,
                source="tushare",
                config=config,
                fetcher=fetcher,
            )
            if result.has_error:
                error_text = _read_error_manifest_text(result.error_manifest_path)
                return BatchExecutionRecord(
                    batch_id=window.batch_id,
                    start_date=window.start_date,
                    end_date=window.end_date,
                    status="failed",
                    elapsed_seconds=perf_counter() - started,
                    trade_dates=len(trade_dates),
                    open_trade_dates=open_trade_dates,
                    error=f"trade_date={trade_date} {error_text}",
                )
    except Exception as exc:
        return BatchExecutionRecord(
            batch_id=window.batch_id,
            start_date=window.start_date,
            end_date=window.end_date,
            status="failed",
            elapsed_seconds=perf_counter() - started,
            trade_dates=len(trade_dates),
            open_trade_dates=open_trade_dates,
            error=str(exc),
        )

    return BatchExecutionRecord(
        batch_id=window.batch_id,
        start_date=window.start_date,
        end_date=window.end_date,
        status="success",
        elapsed_seconds=perf_counter() - started,
        trade_dates=len(trade_dates),
        open_trade_dates=open_trade_dates,
    )


def _emit_progress_event(
    *,
    progress_callback: Callable[[FetchBatchProgressEvent], None] | None,
    total_batches: int,
    completed_ids: set[int],
    failed_ids: set[int],
    window: BatchWindow | None,
    current_status: str,
) -> None:
    if progress_callback is None:
        return
    progress_callback(
        FetchBatchProgressEvent(
            total_batches=int(total_batches),
            completed_batches=len(completed_ids),
            failed_batches=len(failed_ids),
            processed_batches=len(completed_ids) + len(failed_ids),
            current_batch_id=None if window is None else int(window.batch_id),
            current_start_date=None if window is None else window.start_date,
            current_end_date=None if window is None else window.end_date,
            current_status=current_status,
        )
    )


def run_fetch_batch(
    *,
    start_date: str,
    end_date: str,
    batch_size: int,
    batch_unit: str = "day",
    workers: int,
    config: Config,
    fail_once_batch_ids: set[int] | None = None,
    stop_after_batches: int | None = None,
    progress_callback: Callable[[FetchBatchProgressEvent], None] | None = None,
) -> FetchBatchRunResult:
    requested_workers = max(1, int(workers))
    unit = _normalize_batch_unit(batch_unit)
    has_live_token = _has_live_tushare_token(config)
    if has_live_token and requested_workers > 1:
        execution_mode = "real_tushare_parallel_batch_write_lock"
    elif has_live_token:
        execution_mode = "real_tushare_sequential_write_safe"
    else:
        execution_mode = "simulated_offline"
    effective_workers = requested_workers
    windows = _build_batches(start_date, end_date, batch_size, batch_unit=unit)
    state = _resolve_state(
        start_date=start_date,
        end_date=end_date,
        batch_size=batch_size,
        batch_unit=unit,
        workers=effective_workers,
        total_batches=len(windows),
    )

    fail_once = {int(item) for item in (fail_once_batch_ids or set())}
    completed_ids = {int(item) for item in state.get("completed_batch_ids", [])}
    failed_ids = {int(item) for item in state.get("failed_batch_ids", [])}
    injected_ids = {int(item) for item in state.get("failure_injected_batch_ids", [])}
    failed_batch_errors = {
        str(int(batch_id)): str(message)
        for batch_id, message in state.get("failed_batch_errors", {}).items()
    }
    state["status"] = "in_progress"
    state["current_batch_id"] = None
    state["current_start_date"] = None
    state["current_end_date"] = None
    state["current_trade_date"] = None
    state["current_trade_index"] = None
    state["current_trade_total"] = None
    state["completed_batch_ids"] = sorted(completed_ids)
    state["failed_batch_ids"] = sorted(failed_ids)
    state["failure_injected_batch_ids"] = sorted(injected_ids)
    state["failed_batch_errors"] = failed_batch_errors
    _, progress_path = _save_state(state)
    _emit_progress_event(
        progress_callback=progress_callback,
        total_batches=int(state.get("total_batches", len(windows))),
        completed_ids=completed_ids,
        failed_ids=failed_ids,
        window=None,
        current_status="started",
    )

    processed = 0
    execution_records: list[BatchExecutionRecord] = []
    started = perf_counter()
    stop_after_limit = None if stop_after_batches is None else max(0, int(stop_after_batches))
    pending_windows: list[BatchWindow] = []

    def _record_batch_result(window: BatchWindow, record: BatchExecutionRecord) -> None:
        nonlocal processed, progress_path
        batch_id = int(window.batch_id)
        state["current_batch_id"] = batch_id
        state["current_start_date"] = window.start_date
        state["current_end_date"] = window.end_date
        state["current_trade_date"] = None
        state["current_trade_index"] = None
        state["current_trade_total"] = None
        if record.status == "success":
            completed_ids.add(batch_id)
            failed_ids.discard(batch_id)
            failed_batch_errors.pop(str(batch_id), None)
            state["last_success_batch_id"] = max(int(state.get("last_success_batch_id", 0)), batch_id)
        else:
            failed_ids.add(batch_id)
            failed_batch_errors[str(batch_id)] = record.error or "batch_execution_failed"
        processed += 1
        state["completed_batch_ids"] = sorted(completed_ids)
        state["failed_batch_ids"] = sorted(failed_ids)
        state["failure_injected_batch_ids"] = sorted(injected_ids)
        state["failed_batch_errors"] = failed_batch_errors
        _update_status(state)
        _, progress_path = _save_state(state)
        _emit_progress_event(
            progress_callback=progress_callback,
            total_batches=int(state.get("total_batches", len(windows))),
            completed_ids=completed_ids,
            failed_ids=failed_ids,
            window=window,
            current_status=record.status,
        )

    for window in windows:
        if stop_after_limit is not None and (processed + len(pending_windows)) >= stop_after_limit:
            break
        batch_id = int(window.batch_id)
        if batch_id in completed_ids:
            continue
        if batch_id in failed_ids:
            failed_ids.discard(batch_id)
            failed_batch_errors.pop(str(batch_id), None)

        if batch_id in fail_once and batch_id not in injected_ids:
            injected_ids.add(batch_id)
            simulated_failure = BatchExecutionRecord(
                batch_id=batch_id,
                start_date=window.start_date,
                end_date=window.end_date,
                status="failed",
                elapsed_seconds=0.0,
                trade_dates=len(_iter_trade_dates(window.start_date, window.end_date)),
                open_trade_dates=0,
                error="simulated_batch_failure",
            )
            execution_records.append(simulated_failure)
            _record_batch_result(window, simulated_failure)
            continue

        pending_windows.append(window)

    if effective_workers <= 1 or len(pending_windows) <= 1:
        for window in pending_windows:
            batch_id = int(window.batch_id)
            state["current_batch_id"] = batch_id
            state["current_start_date"] = window.start_date
            state["current_end_date"] = window.end_date
            state["current_trade_date"] = None
            state["current_trade_index"] = None
            state["current_trade_total"] = None
            state["completed_batch_ids"] = sorted(completed_ids)
            state["failed_batch_ids"] = sorted(failed_ids)
            state["failure_injected_batch_ids"] = sorted(injected_ids)
            state["failed_batch_errors"] = failed_batch_errors
            state["status"] = "in_progress"
            _, progress_path = _save_state(state)

            def _on_trade_date_processed(trade_date: str, index: int, total: int) -> None:
                state["current_trade_date"] = trade_date
                state["current_trade_index"] = int(index)
                state["current_trade_total"] = int(total)
                state["status"] = "in_progress"
                state["updated_at"] = _utc_now_text()
                _save_state(state)

            record = _execute_batch_window(
                window,
                config=config,
                trade_date_callback=_on_trade_date_processed,
            )
            execution_records.append(record)
            _record_batch_result(window, record)
    else:
        state["current_batch_id"] = None
        state["current_start_date"] = None
        state["current_end_date"] = None
        state["current_trade_date"] = None
        state["current_trade_index"] = None
        state["current_trade_total"] = None
        state["status"] = "in_progress"
        _, progress_path = _save_state(state)
        with ThreadPoolExecutor(max_workers=effective_workers) as executor:
            futures = {
                executor.submit(_execute_batch_window, window, config=config): window
                for window in pending_windows
            }
            for future in as_completed(futures):
                window = futures[future]
                try:
                    record = future.result()
                except Exception as exc:  # pragma: no cover - defensive
                    record = BatchExecutionRecord(
                        batch_id=int(window.batch_id),
                        start_date=window.start_date,
                        end_date=window.end_date,
                        status="failed",
                        elapsed_seconds=0.0,
                        trade_dates=len(_iter_trade_dates(window.start_date, window.end_date)),
                        open_trade_dates=0,
                        error=str(exc),
                    )
                execution_records.append(record)
                _record_batch_result(window, record)

    wall_seconds = perf_counter() - started
    state["completed_batch_ids"] = sorted(completed_ids)
    state["failed_batch_ids"] = sorted(failed_ids)
    state["failure_injected_batch_ids"] = sorted(injected_ids)
    state["failed_batch_errors"] = failed_batch_errors
    state["current_batch_id"] = None
    state["current_start_date"] = None
    state["current_end_date"] = None
    state["current_trade_date"] = None
    state["current_trade_index"] = None
    state["current_trade_total"] = None
    _update_status(state)
    _emit_progress_event(
        progress_callback=progress_callback,
        total_batches=int(state.get("total_batches", len(windows))),
        completed_ids=completed_ids,
        failed_ids=failed_ids,
        window=None,
        current_status=str(state.get("status", "in_progress")),
    )

    _, progress_path = _save_state(state)
    artifacts_dir = _artifacts_dir(end_date)
    throughput_path = artifacts_dir / "throughput_benchmark.md"
    retry_report_path = artifacts_dir / "fetch_retry_report.md"
    _write_throughput_benchmark(
        throughput_path,
        total_batches=int(state.get("total_batches", len(windows))),
        workers=int(state.get("workers", workers)),
        execution_mode=execution_mode,
        records=execution_records,
        wall_seconds=wall_seconds,
    )
    _write_retry_report(
        retry_report_path,
        failed_batch_ids=list(state["failed_batch_ids"]),
        failed_batch_errors=dict(state["failed_batch_errors"]),
    )

    failed_batches = len(state["failed_batch_ids"])
    status = str(state.get("status", "in_progress"))
    return FetchBatchRunResult(
        start_date=start_date,
        end_date=end_date,
        batch_size=int(batch_size),
        batch_unit=unit,
        workers=int(state.get("workers", workers)),
        artifacts_dir=artifacts_dir,
        progress_path=progress_path,
        throughput_benchmark_path=throughput_path,
        retry_report_path=retry_report_path,
        total_batches=int(state.get("total_batches", len(windows))),
        completed_batches=len(state["completed_batch_ids"]),
        failed_batches=failed_batches,
        last_success_batch_id=int(state.get("last_success_batch_id", 0)),
        status=status,
        has_error=failed_batches > 0,
    )


def read_fetch_status(*, config: Config) -> FetchStatusResult:
    del config
    state = _load_state()
    if state is None:
        progress_path = _state_path()
        return FetchStatusResult(
            artifacts_dir=progress_path.parent,
            progress_path=progress_path,
            start_date="",
            end_date="",
            batch_size=0,
            batch_unit="day",
            workers=0,
            total_batches=0,
            completed_batches=0,
            failed_batches=0,
            last_success_batch_id=0,
            status="not_started",
            current_batch_id=None,
            current_start_date=None,
            current_end_date=None,
            current_trade_date=None,
            current_trade_index=None,
            current_trade_total=None,
        )

    progress_path = _artifacts_dir(str(state.get("end_date", ""))) / "fetch_progress.json"
    return FetchStatusResult(
        artifacts_dir=progress_path.parent,
        progress_path=progress_path,
        start_date=str(state.get("start_date", "")),
        end_date=str(state.get("end_date", "")),
        batch_size=int(state.get("batch_size", 0)),
        batch_unit=_normalize_batch_unit(str(state.get("batch_unit", "day"))),
        workers=int(state.get("workers", 0)),
        total_batches=int(state.get("total_batches", 0)),
        completed_batches=int(state.get("completed_batches", 0)),
        failed_batches=int(state.get("failed_batches", 0)),
        last_success_batch_id=int(state.get("last_success_batch_id", 0)),
        status=str(state.get("status", "not_started")),
        current_batch_id=_optional_int(state.get("current_batch_id")),
        current_start_date=_optional_text(state.get("current_start_date")),
        current_end_date=_optional_text(state.get("current_end_date")),
        current_trade_date=_optional_text(state.get("current_trade_date")),
        current_trade_index=_optional_int(state.get("current_trade_index")),
        current_trade_total=_optional_int(state.get("current_trade_total")),
    )


def run_fetch_retry(*, config: Config) -> FetchRetryRunResult:
    state = _load_state()
    if state is None:
        raise ValueError("no fetch progress found; run fetch-batch first")

    windows = _build_batches(
        str(state.get("start_date", "")),
        str(state.get("end_date", "")),
        int(state.get("batch_size", 0)),
        batch_unit=str(state.get("batch_unit", "day")),
    )
    window_map = {int(item.batch_id): item for item in windows}

    failed_ids = [int(item) for item in state.get("failed_batch_ids", [])]
    completed_ids = {int(item) for item in state.get("completed_batch_ids", [])}
    failed_batch_errors = {
        str(int(batch_id)): str(message)
        for batch_id, message in state.get("failed_batch_errors", {}).items()
    }
    retried_results: list[dict[str, str]] = []
    next_failed_ids: set[int] = set()

    for batch_id in failed_ids:
        window = window_map.get(batch_id)
        if window is None:
            next_failed_ids.add(batch_id)
            failed_batch_errors[str(batch_id)] = "batch_window_not_found"
            retried_results.append(
                {"batch_id": str(batch_id), "status": "failed", "error": "batch_window_not_found"}
            )
            continue

        record = _execute_batch_window(window, config=config)
        if record.status == "success":
            completed_ids.add(batch_id)
            failed_batch_errors.pop(str(batch_id), None)
            state["last_success_batch_id"] = max(int(state.get("last_success_batch_id", 0)), batch_id)
            retried_results.append({"batch_id": str(batch_id), "status": "success", "error": ""})
            continue

        next_failed_ids.add(batch_id)
        error_text = record.error or "batch_execution_failed"
        failed_batch_errors[str(batch_id)] = error_text
        retried_results.append(
            {"batch_id": str(batch_id), "status": "failed", "error": error_text}
        )

    state["completed_batch_ids"] = sorted(completed_ids)
    state["failed_batch_ids"] = sorted(next_failed_ids)
    state["failed_batch_errors"] = failed_batch_errors
    state["current_batch_id"] = None
    state["current_start_date"] = None
    state["current_end_date"] = None
    state["current_trade_date"] = None
    state["current_trade_index"] = None
    state["current_trade_total"] = None
    _update_status(state)

    _, progress_path = _save_state(state)
    artifacts_dir = _artifacts_dir(str(state.get("end_date", "")))
    retry_report_path = artifacts_dir / "fetch_retry_report.md"
    _write_retry_report(
        retry_report_path,
        failed_batch_ids=list(state["failed_batch_ids"]),
        failed_batch_errors=failed_batch_errors,
        retried_results=retried_results,
    )
    completed_batches = len(state.get("completed_batch_ids", []))
    failed_batches = len(state.get("failed_batch_ids", []))

    return FetchRetryRunResult(
        artifacts_dir=artifacts_dir,
        progress_path=progress_path,
        retry_report_path=retry_report_path,
        retried_batches=len(retried_results),
        total_batches=int(state.get("total_batches", 0)),
        completed_batches=completed_batches,
        failed_batches=failed_batches,
        status=str(state.get("status", "in_progress")),
        has_error=str(state.get("status", "in_progress")) != "completed",
    )
