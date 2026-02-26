"""S7a 交易日判定 + 幂等去重测试。

验证 CalendarGuard 消费 raw_trade_cal 跳过非交易日，
以及 check_idempotency 去重已成功任务。
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from src.config.config import Config
from src.pipeline.scheduler import (
    CalendarCheckResult,
    check_idempotency,
    check_trade_calendar,
    log_task_end,
    log_task_start,
)


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s7a.cal"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


def _seed_trade_cal(config: Config, entries: list[tuple[str, int]]) -> None:
    """写入测试用 raw_trade_cal 数据。"""
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


# ---------- CalendarGuard ----------


def test_trade_day_detected(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    _seed_trade_cal(config, [("20260226", 1)])
    result = check_trade_calendar(config, "20260226")
    assert isinstance(result, CalendarCheckResult)
    assert result.is_trade_day is True
    assert result.reason == "trade_day"


def test_non_trade_day_detected(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    _seed_trade_cal(config, [("20260228", 0)])
    result = check_trade_calendar(config, "20260228")
    assert result.is_trade_day is False
    assert result.reason == "non_trade_day"


def test_missing_calendar_defaults_to_trade_day(tmp_path: Path) -> None:
    """raw_trade_cal 不存在时，默认视为交易日。"""
    config = _build_config(tmp_path)
    result = check_trade_calendar(config, "20260226")
    assert result.is_trade_day is True
    assert result.reason == "calendar_missing"


def test_missing_date_in_calendar_defaults_to_trade_day(tmp_path: Path) -> None:
    """cal_date 无记录时，默认视为交易日。"""
    config = _build_config(tmp_path)
    _seed_trade_cal(config, [("20260226", 1)])
    result = check_trade_calendar(config, "20260301")
    assert result.is_trade_day is True
    assert result.reason == "calendar_missing"


# ---------- Idempotency ----------


def test_idempotency_false_when_no_log(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    assert check_idempotency(config, "run_once", "20260226") is False


def test_idempotency_false_when_task_running(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    log_task_start(config, "run_once", "20260226")
    # 状态是 running，不是 success
    assert check_idempotency(config, "run_once", "20260226") is False


def test_idempotency_true_after_success(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    entry = log_task_start(config, "run_once", "20260226")
    log_task_end(config, entry, status="success")
    assert check_idempotency(config, "run_once", "20260226") is True


def test_idempotency_false_after_failure(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    entry = log_task_start(config, "run_once", "20260226")
    log_task_end(config, entry, status="failed", error_message="test error")
    assert check_idempotency(config, "run_once", "20260226") is False


def test_idempotency_scoped_to_task_and_date(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    entry = log_task_start(config, "run_once", "20260226")
    log_task_end(config, entry, status="success")
    # 不同日期不幂等
    assert check_idempotency(config, "run_once", "20260227") is False
    # 不同任务不幂等
    assert check_idempotency(config, "other_task", "20260226") is False
