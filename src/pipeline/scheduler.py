"""S7a 每日调度模块（SchedulerCore + CalendarGuard + RunHistory）。

提供 ``eq scheduler install/status/run-once`` CLI 入口。
调度层不改业务语义，仅做编排与运维增强。

与 data-layer-api.md §6 DataScheduler API /
data-layer-algorithm.md §7.2 DailyPipelineScheduler 对齐。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import duckdb

from src.config.config import Config
from src.db.helpers import table_exists as _table_exists

# DESIGN_TRACE:
# - docs/design/core-infrastructure/data-layer/data-layer-api.md (§6 DataScheduler API)
# - docs/design/core-infrastructure/data-layer/data-layer-algorithm.md (§7.2 DailyPipelineScheduler, §6.2 task_execution_log)
# - Governance/SpiralRoadmap/execution-cards/S7A-EXECUTION-CARD.md (§3 模块级补齐任务)
# - docs/design/enhancements/eq-improvement-plan-core-frozen.md (ENH-11 定时调度器)
DESIGN_TRACE = {
    "data_layer_api": "docs/design/core-infrastructure/data-layer/data-layer-api.md",
    "data_layer_algorithm": "docs/design/core-infrastructure/data-layer/data-layer-algorithm.md",
    "s7a_execution_card": "Governance/SpiralRoadmap/execution-cards/S7A-EXECUTION-CARD.md",
    "enhancement_plan": "docs/design/enhancements/eq-improvement-plan-core-frozen.md",
}

# 默认调度参数
DEFAULT_SCHEDULE_TIME = "16:00"
DEFAULT_TIMEZONE = "Asia/Shanghai"
MAX_RETRY_COUNT = 3
RETRY_INTERVAL_SECONDS = 300  # 5 分钟


# ---------- task_execution_log DDL ----------

_TASK_LOG_DDL = """\
CREATE TABLE IF NOT EXISTS task_execution_log (
    task_name VARCHAR(50) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds REAL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT
)
"""

_SCHEDULER_CONFIG_DDL = """\
CREATE TABLE IF NOT EXISTS scheduler_config (
    key VARCHAR(50) PRIMARY KEY,
    value VARCHAR(200) NOT NULL,
    updated_at TIMESTAMP NOT NULL
)
"""


def _ensure_db_dir(config: Config) -> Path:
    """确保 DuckDB 目录存在并返回 db_path。"""
    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def _ensure_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """确保调度表存在。"""
    conn.execute(_TASK_LOG_DDL)
    conn.execute(_SCHEDULER_CONFIG_DDL)


# ---------- CalendarGuard ----------


@dataclass(frozen=True)
class CalendarCheckResult:
    """交易日判定结果。"""

    trade_date: str
    is_trade_day: bool
    reason: str  # "trade_day" / "non_trade_day" / "calendar_missing"


def check_trade_calendar(
    config: Config, trade_date: str
) -> CalendarCheckResult:
    """消费 raw_trade_cal 判断是否交易日。

    若 raw_trade_cal 不存在或无记录，返回 calendar_missing，不阻断。
    """
    db_path = _ensure_db_dir(config)
    with duckdb.connect(str(db_path), read_only=False) as conn:
        if not _table_exists(conn, "raw_trade_cal"):
            return CalendarCheckResult(
                trade_date=trade_date,
                is_trade_day=True,
                reason="calendar_missing",
            )
        row = conn.execute(
            "SELECT is_open FROM raw_trade_cal WHERE cal_date = ?",
            [trade_date],
        ).fetchone()
    if row is None:
        return CalendarCheckResult(
            trade_date=trade_date,
            is_trade_day=True,
            reason="calendar_missing",
        )
    is_open = int(row[0]) == 1
    return CalendarCheckResult(
        trade_date=trade_date,
        is_trade_day=is_open,
        reason="trade_day" if is_open else "non_trade_day",
    )


# ---------- RunHistory ----------


@dataclass
class TaskLogEntry:
    """单条任务执行记录。"""

    task_name: str
    trade_date: str
    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: float | None = None
    status: str = "running"  # running / success / failed
    error_message: str | None = None


def log_task_start(
    config: Config, task_name: str, trade_date: str
) -> TaskLogEntry:
    """记录任务开始。"""
    entry = TaskLogEntry(
        task_name=task_name,
        trade_date=trade_date,
        start_time=datetime.now(),
    )
    db_path = _ensure_db_dir(config)
    with duckdb.connect(str(db_path)) as conn:
        _ensure_tables(conn)
        conn.execute(
            "INSERT INTO task_execution_log "
            "(task_name, trade_date, start_time, status) "
            "VALUES (?, ?, ?, ?)",
            [entry.task_name, entry.trade_date, entry.start_time, entry.status],
        )
    return entry


def log_task_end(
    config: Config,
    entry: TaskLogEntry,
    *,
    status: str,
    error_message: str | None = None,
) -> TaskLogEntry:
    """记录任务结束。"""
    entry.end_time = datetime.now()
    entry.duration_seconds = (entry.end_time - entry.start_time).total_seconds()
    entry.status = status
    entry.error_message = error_message
    db_path = _ensure_db_dir(config)
    with duckdb.connect(str(db_path)) as conn:
        _ensure_tables(conn)
        conn.execute(
            "UPDATE task_execution_log "
            "SET end_time = ?, duration_seconds = ?, status = ?, error_message = ? "
            "WHERE task_name = ? AND trade_date = ? AND start_time = ?",
            [
                entry.end_time,
                entry.duration_seconds,
                entry.status,
                entry.error_message,
                entry.task_name,
                entry.trade_date,
                entry.start_time,
            ],
        )
    return entry


def check_idempotency(
    config: Config, task_name: str, trade_date: str
) -> bool:
    """检查同 trade_date+task_name 是否已成功执行。

    Returns True 如果已有 success 记录（幂等跳过）。
    """
    db_path = _ensure_db_dir(config)
    with duckdb.connect(str(db_path), read_only=False) as conn:
        if not _table_exists(conn, "task_execution_log"):
            return False
        row = conn.execute(
            "SELECT COUNT(*) FROM task_execution_log "
            "WHERE task_name = ? AND trade_date = ? AND status = 'success'",
            [task_name, trade_date],
        ).fetchone()
    return row is not None and int(row[0]) > 0


def get_run_history(
    config: Config, trade_date: str | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    """查询运行历史。"""
    db_path = _ensure_db_dir(config)
    with duckdb.connect(str(db_path), read_only=False) as conn:
        if not _table_exists(conn, "task_execution_log"):
            return []
        if trade_date:
            rows = conn.execute(
                "SELECT * FROM task_execution_log "
                "WHERE trade_date = ? ORDER BY start_time DESC LIMIT ?",
                [trade_date, limit],
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM task_execution_log "
                "ORDER BY start_time DESC LIMIT ?",
                [limit],
            ).fetchall()
        cols = [d[0] for d in conn.description]
    return [dict(zip(cols, r)) for r in rows]


# ---------- SchedulerCore ----------


@dataclass(frozen=True)
class SchedulerStatus:
    """调度器状态。"""

    installed: bool
    schedule_time: str
    timezone: str
    last_run_date: str | None
    last_run_status: str | None


def install_scheduler(config: Config) -> SchedulerStatus:
    """注册每日任务到 scheduler_config 表。"""
    db_path = _ensure_db_dir(config)
    now = datetime.now()
    with duckdb.connect(str(db_path)) as conn:
        _ensure_tables(conn)
        for key, value in [
            ("installed", "true"),
            ("schedule_time", DEFAULT_SCHEDULE_TIME),
            ("timezone", DEFAULT_TIMEZONE),
            ("installed_at", now.isoformat()),
        ]:
            conn.execute(
                "INSERT OR REPLACE INTO scheduler_config (key, value, updated_at) "
                "VALUES (?, ?, ?)",
                [key, value, now],
            )
    return get_scheduler_status(config)


def get_scheduler_status(config: Config) -> SchedulerStatus:
    """查询调度器当前状态。"""
    db_path = _ensure_db_dir(config)
    with duckdb.connect(str(db_path), read_only=False) as conn:
        if not _table_exists(conn, "scheduler_config"):
            return SchedulerStatus(
                installed=False,
                schedule_time=DEFAULT_SCHEDULE_TIME,
                timezone=DEFAULT_TIMEZONE,
                last_run_date=None,
                last_run_status=None,
            )
        rows = conn.execute(
            "SELECT key, value FROM scheduler_config"
        ).fetchall()
        cfg = {str(r[0]): str(r[1]) for r in rows}

        last_run_date = None
        last_run_status = None
        if _table_exists(conn, "task_execution_log"):
            last = conn.execute(
                "SELECT trade_date, status FROM task_execution_log "
                "ORDER BY start_time DESC LIMIT 1"
            ).fetchone()
            if last:
                last_run_date = str(last[0])
                last_run_status = str(last[1])

    return SchedulerStatus(
        installed=cfg.get("installed") == "true",
        schedule_time=cfg.get("schedule_time", DEFAULT_SCHEDULE_TIME),
        timezone=cfg.get("timezone", DEFAULT_TIMEZONE),
        last_run_date=last_run_date,
        last_run_status=last_run_status,
    )


def run_once(
    config: Config,
    trade_date: str,
    *,
    pipeline_runner: Any | None = None,
) -> dict[str, Any]:
    """手动触发单日全链路执行。

    Parameters
    ----------
    pipeline_runner : callable(argv) -> int, optional
        执行 main(argv) 的回调。默认使用 src.pipeline.main.main。
    """
    from src.pipeline.main import main as _pipeline_main

    runner = pipeline_runner or _pipeline_main

    # CalendarGuard
    cal = check_trade_calendar(config, trade_date)
    if not cal.is_trade_day:
        return {
            "event": "s7a_scheduler_run_once",
            "trade_date": trade_date,
            "skipped": True,
            "reason": cal.reason,
            "status": "skipped",
        }

    # 幂等检查
    if check_idempotency(config, "run_once", trade_date):
        return {
            "event": "s7a_scheduler_run_once",
            "trade_date": trade_date,
            "skipped": True,
            "reason": "idempotent_skip",
            "status": "skipped",
        }

    # 执行全链路
    entry = log_task_start(config, "run_once", trade_date)
    retries = 0
    last_error: str | None = None

    while retries <= MAX_RETRY_COUNT:
        try:
            rc = runner(["run-all", "--date", trade_date, "--skip-consistency"])
            if rc == 0:
                log_task_end(config, entry, status="success")
                return {
                    "event": "s7a_scheduler_run_once",
                    "trade_date": trade_date,
                    "retries": retries,
                    "status": "ok",
                }
            last_error = f"pipeline_exit_code={rc}"
        except Exception as exc:
            last_error = str(exc)

        retries += 1
        if retries <= MAX_RETRY_COUNT:
            time.sleep(RETRY_INTERVAL_SECONDS)

    log_task_end(config, entry, status="failed", error_message=last_error)
    return {
        "event": "s7a_scheduler_run_once",
        "trade_date": trade_date,
        "retries": retries - 1,
        "status": "failed",
        "error": last_error,
    }
