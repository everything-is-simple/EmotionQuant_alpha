from __future__ import annotations

import json
from pathlib import Path

from src.config.config import Config
from src.data.fetch_batch_pipeline import run_fetch_batch


def test_fetch_batch_generates_progress_and_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = Config.from_env(env_file=None)

    result = run_fetch_batch(
        start_date="20260101",
        end_date="20260110",
        batch_size=3,
        workers=3,
        config=config,
    )

    assert result.status == "completed"
    assert result.total_batches > 0
    assert result.completed_batches == result.total_batches
    assert result.failed_batches == 0
    assert result.last_success_batch_id == result.total_batches

    progress_payload = json.loads(result.progress_path.read_text(encoding="utf-8"))
    assert progress_payload["contract_version"] == "nc-v1"
    assert progress_payload["start_date"] == "20260101"
    assert progress_payload["end_date"] == "20260110"
    assert progress_payload["completed_batches"] == progress_payload["total_batches"]
    assert progress_payload["failed_batches"] == 0
    assert progress_payload["status"] == "completed"

    assert result.progress_path == Path("artifacts/spiral-s3a/20260110/fetch_progress.json")
    assert result.throughput_benchmark_path.exists()
    assert result.retry_report_path.exists()
