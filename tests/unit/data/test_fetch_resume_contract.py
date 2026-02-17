from __future__ import annotations

import json
from pathlib import Path

from src.config.config import Config
from src.data.fetch_batch_pipeline import run_fetch_batch


def test_fetch_batch_resume_does_not_duplicate_completed_batches(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = Config.from_env(env_file=None)

    first_run = run_fetch_batch(
        start_date="20260101",
        end_date="20260112",
        batch_size=2,
        workers=2,
        config=config,
        stop_after_batches=2,
    )
    assert first_run.status == "in_progress"
    assert first_run.completed_batches == 2

    second_run = run_fetch_batch(
        start_date="20260101",
        end_date="20260112",
        batch_size=2,
        workers=2,
        config=config,
    )
    assert second_run.status == "completed"

    progress_payload = json.loads(second_run.progress_path.read_text(encoding="utf-8"))
    completed_ids = progress_payload["completed_batch_ids"]
    assert len(completed_ids) == len(set(completed_ids))
    assert progress_payload["completed_batches"] == progress_payload["total_batches"]
    assert progress_payload["failed_batches"] == 0
    assert second_run.progress_path == Path("artifacts/spiral-s3a/20260112/fetch_progress.json")
