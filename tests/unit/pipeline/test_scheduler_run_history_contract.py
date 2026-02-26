"""S7a 运行历史契约测试。

验证 task_execution_log CRUD、run_once 非交易日跳过与幂等跳过。
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from src.config.config import Config
from src.pipeline.scheduler import (
    TaskLogEntry,
    get_run_history,
    log_task_end,
    log_task_start,
    run_once,
)


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s7a.hist"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _seed_trade_cal(config: Config, entries: list[tuple[str, int]]) -> None:
    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS raw_trade_cal ("
            "cal_date VARCHAR(8), is_open INTEGER"
            ")"
        )
        for cal_date, is_open in entries:
            conn.execute(
                "INSERT INTO raw_trade_cal (cal_date, is_open) VALUES (?, ?)",
                [cal_date, is_open],
            )


# ---------- task log CRUD ----------


def test_log_task_start_creates_entry(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    entry = log_task_start(config, "test_task", "20260226")
    assert isinstance(entry, TaskLogEntry)
    assert entry.task_name == "test_task"
    assert entry.trade_date == "20260226"
    assert entry.status == "running"


def test_log_task_end_updates_status(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    entry = log_task_start(config, "test_task", "20260226")
    updated = log_task_end(config, entry, status="success")
    assert updated.status == "success"
    assert updated.end_time is not None
    assert updated.duration_seconds is not None
    assert updated.duration_seconds >= 0


def test_log_task_end_records_error_message(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    entry = log_task_start(config, "test_task", "20260226")
    updated = log_task_end(config, entry, status="failed", error_message="boom")
    assert updated.error_message == "boom"
    assert updated.status == "failed"


# ---------- get_run_history ----------


def test_get_run_history_empty_when_no_log(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    history = get_run_history(config)
    assert history == []


def test_get_run_history_returns_entries(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    entry = log_task_start(config, "run_once", "20260226")
    log_task_end(config, entry, status="success")
    history = get_run_history(config, trade_date="20260226")
    assert len(history) >= 1
    assert history[0]["task_name"] == "run_once"
    assert history[0]["trade_date"] == "20260226"
    assert history[0]["status"] == "success"


def test_get_run_history_filtered_by_date(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    e1 = log_task_start(config, "run_once", "20260226")
    log_task_end(config, e1, status="success")
    e2 = log_task_start(config, "run_once", "20260227")
    log_task_end(config, e2, status="success")
    history = get_run_history(config, trade_date="20260226")
    assert all(h["trade_date"] == "20260226" for h in history)


# ---------- run_once integration ----------


def test_run_once_skips_non_trade_day(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    _seed_trade_cal(config, [("20260228", 0)])
    result = run_once(config, "20260228")
    assert result["status"] == "skipped"
    assert result["reason"] == "non_trade_day"


def test_run_once_skips_idempotent(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    # 预写入一条 success 记录
    entry = log_task_start(config, "run_once", "20260226")
    log_task_end(config, entry, status="success")
    result = run_once(config, "20260226")
    assert result["status"] == "skipped"
    assert result["reason"] == "idempotent_skip"


def test_run_once_succeeds_with_mock_runner(tmp_path: Path) -> None:
    config = _build_config(tmp_path)

    def mock_runner(argv: list[str]) -> int:
        return 0

    result = run_once(config, "20260226", pipeline_runner=mock_runner)
    assert result["status"] == "ok"
    assert result["retries"] == 0


def test_run_once_records_failure_after_retries(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    call_count = 0

    def failing_runner(argv: list[str]) -> int:
        nonlocal call_count
        call_count += 1
        return 1  # 始终失败

    # 用 monkeypatch-style：覆盖 RETRY_INTERVAL_SECONDS 避免等待
    import src.pipeline.scheduler as sched_mod

    original_interval = sched_mod.RETRY_INTERVAL_SECONDS
    sched_mod.RETRY_INTERVAL_SECONDS = 0  # 不等待
    try:
        result = run_once(config, "20260226", pipeline_runner=failing_runner)
    finally:
        sched_mod.RETRY_INTERVAL_SECONDS = original_interval

    assert result["status"] == "failed"
    assert call_count == 4  # 1 initial + 3 retries
