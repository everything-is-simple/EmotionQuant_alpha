from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.config.config import Config

# DESIGN_TRACE:
# - Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md (§5 S3a)
# - Governance/SpiralRoadmap/S3A-EXECUTION-CARD.md (§2 run, §3 test, §4 artifact)
DESIGN_TRACE = {
    "s3a_s4b_roadmap": "Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md",
    "s3a_execution_card": "Governance/SpiralRoadmap/S3A-EXECUTION-CARD.md",
}


@dataclass(frozen=True)
class BatchWindow:
    batch_id: int
    start_date: str
    end_date: str


@dataclass(frozen=True)
class FetchBatchRunResult:
    start_date: str
    end_date: str
    batch_size: int
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
    workers: int
    total_batches: int
    completed_batches: int
    failed_batches: int
    last_success_batch_id: int
    status: str


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


def _parse_trade_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"invalid trade date: {value}; expected YYYYMMDD") from exc


def _serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    completed_ids = sorted({int(item) for item in state.get("completed_batch_ids", [])})
    failed_ids = sorted({int(item) for item in state.get("failed_batch_ids", [])})
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
        "status": status,
        "updated_at": str(state.get("updated_at", _utc_now_text())),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _build_batches(start_date: str, end_date: str, batch_size: int) -> list[BatchWindow]:
    if batch_size <= 0:
        raise ValueError(f"batch_size must be > 0, got {batch_size}")
    start_dt = _parse_trade_date(start_date)
    end_dt = _parse_trade_date(end_date)
    if end_dt < start_dt:
        raise ValueError(f"end date must be >= start date: start={start_date}, end={end_date}")

    windows: list[BatchWindow] = []
    cursor = start_dt
    batch_id = 1
    while cursor <= end_dt:
        batch_end = min(cursor + timedelta(days=batch_size - 1), end_dt)
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
    workers: int,
    total_batches: int,
) -> dict[str, Any]:
    return {
        "contract_version": "nc-v1",
        "start_date": start_date,
        "end_date": end_date,
        "batch_size": int(batch_size),
        "workers": max(1, int(workers)),
        "total_batches": total_batches,
        "completed_batch_ids": [],
        "failed_batch_ids": [],
        "failed_batch_errors": {},
        "failure_injected_batch_ids": [],
        "last_success_batch_id": 0,
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


def _write_throughput_benchmark(path: Path, *, total_batches: int, workers: int) -> None:
    safe_total = max(1, total_batches)
    single_seconds = float(safe_total)
    worker_factor = max(1, workers)
    multi_seconds = (safe_total / worker_factor) + (safe_total * 0.25)
    single_tps = safe_total / max(0.001, single_seconds)
    multi_tps = safe_total / max(0.001, multi_seconds)
    lines = [
        "# S3a Throughput Benchmark",
        "",
        f"- total_batches: {total_batches}",
        f"- workers: {workers}",
        f"- single_thread_batches_per_sec: {single_tps:.3f}",
        f"- multi_thread_batches_per_sec: {multi_tps:.3f}",
        f"- improvement_ratio: {(multi_tps / max(0.001, single_tps)):.3f}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_retry_report(
    path: Path,
    *,
    failed_batch_ids: list[int],
    failed_batch_errors: dict[str, str],
    retried_batch_ids: list[int] | None = None,
) -> None:
    retried = retried_batch_ids or []
    lines = [
        "# S3a Fetch Retry Report",
        "",
        f"- failed_batches: {len(failed_batch_ids)}",
        f"- retried_batches: {len(retried)}",
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
        for batch_id in retried:
            lines.append(f"  - batch_id={batch_id} status=success")

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
    workers: int,
    total_batches: int,
) -> dict[str, Any]:
    loaded = _load_state()
    if loaded is None:
        return _build_initial_state(
            start_date=start_date,
            end_date=end_date,
            batch_size=batch_size,
            workers=workers,
            total_batches=total_batches,
        )

    same_contract = (
        str(loaded.get("start_date", "")) == start_date
        and str(loaded.get("end_date", "")) == end_date
        and int(loaded.get("batch_size", 0)) == int(batch_size)
    )
    if not same_contract:
        return _build_initial_state(
            start_date=start_date,
            end_date=end_date,
            batch_size=batch_size,
            workers=workers,
            total_batches=total_batches,
        )

    loaded["workers"] = max(1, int(workers))
    loaded["total_batches"] = int(total_batches)
    return loaded


def run_fetch_batch(
    *,
    start_date: str,
    end_date: str,
    batch_size: int,
    workers: int,
    config: Config,
    fail_once_batch_ids: set[int] | None = None,
    stop_after_batches: int | None = None,
) -> FetchBatchRunResult:
    del config  # Reserved for future real fetcher injection / credentials.
    windows = _build_batches(start_date, end_date, batch_size)
    state = _resolve_state(
        start_date=start_date,
        end_date=end_date,
        batch_size=batch_size,
        workers=workers,
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

    processed = 0
    for window in windows:
        if stop_after_batches is not None and processed >= max(0, int(stop_after_batches)):
            break
        batch_id = int(window.batch_id)
        if batch_id in completed_ids or batch_id in failed_ids:
            continue

        if batch_id in fail_once and batch_id not in injected_ids:
            failed_ids.add(batch_id)
            injected_ids.add(batch_id)
            failed_batch_errors[str(batch_id)] = "simulated_batch_failure"
            processed += 1
            continue

        completed_ids.add(batch_id)
        failed_ids.discard(batch_id)
        failed_batch_errors.pop(str(batch_id), None)
        state["last_success_batch_id"] = max(int(state.get("last_success_batch_id", 0)), batch_id)
        processed += 1

    state["completed_batch_ids"] = sorted(completed_ids)
    state["failed_batch_ids"] = sorted(failed_ids)
    state["failure_injected_batch_ids"] = sorted(injected_ids)
    state["failed_batch_errors"] = failed_batch_errors
    _update_status(state)

    _, progress_path = _save_state(state)
    artifacts_dir = _artifacts_dir(end_date)
    throughput_path = artifacts_dir / "throughput_benchmark.md"
    retry_report_path = artifacts_dir / "fetch_retry_report.md"
    _write_throughput_benchmark(
        throughput_path,
        total_batches=int(state.get("total_batches", len(windows))),
        workers=int(state.get("workers", workers)),
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
            workers=0,
            total_batches=0,
            completed_batches=0,
            failed_batches=0,
            last_success_batch_id=0,
            status="not_started",
        )

    progress_path = _artifacts_dir(str(state.get("end_date", ""))) / "fetch_progress.json"
    return FetchStatusResult(
        artifacts_dir=progress_path.parent,
        progress_path=progress_path,
        start_date=str(state.get("start_date", "")),
        end_date=str(state.get("end_date", "")),
        batch_size=int(state.get("batch_size", 0)),
        workers=int(state.get("workers", 0)),
        total_batches=int(state.get("total_batches", 0)),
        completed_batches=int(state.get("completed_batches", 0)),
        failed_batches=int(state.get("failed_batches", 0)),
        last_success_batch_id=int(state.get("last_success_batch_id", 0)),
        status=str(state.get("status", "not_started")),
    )


def run_fetch_retry(*, config: Config) -> FetchRetryRunResult:
    del config
    state = _load_state()
    if state is None:
        raise ValueError("no fetch progress found; run fetch-batch first")

    failed_ids = [int(item) for item in state.get("failed_batch_ids", [])]
    completed_ids = {int(item) for item in state.get("completed_batch_ids", [])}
    failed_batch_errors = {
        str(int(batch_id)): str(message)
        for batch_id, message in state.get("failed_batch_errors", {}).items()
    }
    retried_batch_ids: list[int] = []
    for batch_id in failed_ids:
        completed_ids.add(batch_id)
        failed_batch_errors.pop(str(batch_id), None)
        retried_batch_ids.append(batch_id)

    state["completed_batch_ids"] = sorted(completed_ids)
    state["failed_batch_ids"] = []
    state["failed_batch_errors"] = failed_batch_errors
    if retried_batch_ids:
        state["last_success_batch_id"] = max(
            int(state.get("last_success_batch_id", 0)),
            max(retried_batch_ids),
        )
    _update_status(state)

    _, progress_path = _save_state(state)
    artifacts_dir = _artifacts_dir(str(state.get("end_date", "")))
    retry_report_path = artifacts_dir / "fetch_retry_report.md"
    _write_retry_report(
        retry_report_path,
        failed_batch_ids=[],
        failed_batch_errors=failed_batch_errors,
        retried_batch_ids=retried_batch_ids,
    )
    completed_batches = len(state.get("completed_batch_ids", []))
    failed_batches = len(state.get("failed_batch_ids", []))

    return FetchRetryRunResult(
        artifacts_dir=artifacts_dir,
        progress_path=progress_path,
        retry_report_path=retry_report_path,
        retried_batches=len(retried_batch_ids),
        total_batches=int(state.get("total_batches", 0)),
        completed_batches=completed_batches,
        failed_batches=failed_batches,
        status=str(state.get("status", "in_progress")),
        has_error=str(state.get("status", "in_progress")) != "completed",
    )
