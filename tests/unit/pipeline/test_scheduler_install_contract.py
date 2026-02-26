"""S7a 调度器安装契约测试。

验证 eq scheduler install/status/run-once CLI 解析与 SchedulerCore 安装逻辑。
"""

from __future__ import annotations

from pathlib import Path

from src.config.config import Config
from src.pipeline.main import build_parser
from src.pipeline.scheduler import (
    DEFAULT_SCHEDULE_TIME,
    DEFAULT_TIMEZONE,
    SchedulerStatus,
    get_scheduler_status,
    install_scheduler,
)


def _build_config(tmp_path: Path) -> Config:
    env_file = tmp_path / ".env.s7a.install"
    data_path = tmp_path / "eq_data"
    env_file.write_text(
        f"DATA_PATH={data_path}\n"
        "ENVIRONMENT=test\n",
        encoding="utf-8",
    )
    return Config.from_env(env_file=str(env_file))


# ---------- CLI parser ----------


def test_scheduler_install_subcommand_registered() -> None:
    parser = build_parser()
    args = parser.parse_args(["scheduler", "install"])
    assert args.command == "scheduler"
    assert args.scheduler_action == "install"


def test_scheduler_status_subcommand_registered() -> None:
    parser = build_parser()
    args = parser.parse_args(["scheduler", "status"])
    assert args.command == "scheduler"
    assert args.scheduler_action == "status"


def test_scheduler_run_once_subcommand_registered() -> None:
    parser = build_parser()
    args = parser.parse_args(["scheduler", "run-once", "--date", "20260226"])
    assert args.command == "scheduler"
    assert args.scheduler_action == "run-once"
    assert args.date == "20260226"


# ---------- install / status ----------


def test_install_scheduler_creates_config(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    status = install_scheduler(config)
    assert isinstance(status, SchedulerStatus)
    assert status.installed is True
    assert status.schedule_time == DEFAULT_SCHEDULE_TIME
    assert status.timezone == DEFAULT_TIMEZONE


def test_get_scheduler_status_before_install(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    status = get_scheduler_status(config)
    assert status.installed is False


def test_get_scheduler_status_after_install(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    install_scheduler(config)
    status = get_scheduler_status(config)
    assert status.installed is True
    assert status.schedule_time == DEFAULT_SCHEDULE_TIME
    assert status.timezone == DEFAULT_TIMEZONE


def test_install_is_idempotent(tmp_path: Path) -> None:
    config = _build_config(tmp_path)
    s1 = install_scheduler(config)
    s2 = install_scheduler(config)
    assert s1.installed is True
    assert s2.installed is True
    assert s1.schedule_time == s2.schedule_time
