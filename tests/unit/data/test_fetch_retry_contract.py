"""
批量采集失败批次重试契约测试。

验证 run_fetch_retry 能够恢复上次运行中失败的批次，
并生成重试报告。
"""
from __future__ import annotations

import json
from pathlib import Path

from src.config.config import Config
from src.data.fetch_batch_pipeline import run_fetch_batch, run_fetch_retry


def test_fetch_retry_recovers_failed_batches(tmp_path: Path, monkeypatch) -> None:
    """重试应恢复失败批次，最终 failed_batches=0 且重试报告完整。"""
    monkeypatch.chdir(tmp_path)
    config = Config.from_env(env_file=None)

    first_run = run_fetch_batch(
        start_date="20260101",
        end_date="20260110",
        batch_size=3,
        workers=3,
        config=config,
        fail_once_batch_ids={2},
    )
    assert first_run.status == "partial_failed"
    assert first_run.failed_batches == 1

    before_retry = json.loads(first_run.progress_path.read_text(encoding="utf-8"))
    assert before_retry["failed_batch_ids"] == [2]
    assert before_retry["failed_batches"] == 1

    retry_run = run_fetch_retry(config=config)
    assert retry_run.retried_batches == 1
    assert retry_run.status == "completed"
    assert retry_run.failed_batches == 0

    after_retry = json.loads(retry_run.progress_path.read_text(encoding="utf-8"))
    assert after_retry["failed_batches"] == 0
    assert after_retry["failed_batch_ids"] == []
    assert after_retry["completed_batches"] == after_retry["total_batches"]
    assert retry_run.retry_report_path == Path("artifacts/spiral-s3a/20260110/fetch_retry_report.md")
    retry_report_text = retry_run.retry_report_path.read_text(encoding="utf-8")
    assert "retried_batches: 1" in retry_report_text
    assert "retried_success_batches: 1" in retry_report_text
