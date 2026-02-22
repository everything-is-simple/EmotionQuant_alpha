from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from src.config.config import Config
import src.data.fetch_batch_pipeline as fetch_batch_pipeline
from src.data.fetch_batch_pipeline import FetchBatchProgressEvent, run_fetch_batch


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
    throughput_text = result.throughput_benchmark_path.read_text(encoding="utf-8")
    assert "measured_wall_seconds:" in throughput_text
    assert "single_thread_batches_per_sec:" in throughput_text
    assert "effective_batches_per_sec:" in throughput_text


def test_fetch_batch_emits_realtime_progress_events(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = Config.from_env(env_file=None)
    events: list[FetchBatchProgressEvent] = []

    result = run_fetch_batch(
        start_date="20260101",
        end_date="20260110",
        batch_size=3,
        workers=3,
        config=config,
        progress_callback=events.append,
    )

    assert events
    assert events[0].current_status == "started"
    last_event = events[-1]
    assert last_event.current_batch_id is None
    assert last_event.current_status == "completed"
    assert last_event.total_batches == result.total_batches
    assert last_event.completed_batches == result.completed_batches
    assert last_event.failed_batches == result.failed_batches


def test_fetch_batch_uses_trade_cal_window_once_and_runs_only_open_days(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = Config.from_env(env_file=None)
    called_trade_dates: list[str] = []

    class _FakeFetcher:
        instances: list["_FakeFetcher"] = []

        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs
            self.calls: list[tuple[str, dict[str, str]]] = []
            _FakeFetcher.instances.append(self)

        def fetch_with_retry(self, api_name: str, params: dict[str, str]) -> list[dict[str, object]]:
            self.calls.append((api_name, dict(params)))
            assert api_name == "trade_cal"
            return [
                {"trade_date": "20260101", "is_open": 0},
                {"trade_date": "20260102", "is_open": 1},
                {"trade_date": "20260103", "is_open": 0},
                {"trade_date": "20260104", "is_open": 1},
            ]

    def _fake_run_l1_collection(**kwargs: object) -> SimpleNamespace:
        called_trade_dates.append(str(kwargs["trade_date"]))
        return SimpleNamespace(
            has_error=False,
            error_manifest_path=Path("artifacts/error_manifest_sample.json"),
        )

    monkeypatch.setattr(fetch_batch_pipeline, "_has_live_tushare_token", lambda _cfg: True)
    monkeypatch.setattr(fetch_batch_pipeline, "TuShareFetcher", _FakeFetcher)
    monkeypatch.setattr(fetch_batch_pipeline, "run_l1_collection", _fake_run_l1_collection)

    result = run_fetch_batch(
        start_date="20260101",
        end_date="20260104",
        batch_size=30,
        workers=3,
        config=config,
    )

    assert result.status == "completed"
    assert result.workers == 1
    assert called_trade_dates == ["20260102", "20260104"]
    assert len(_FakeFetcher.instances) == 1
    calls = _FakeFetcher.instances[0].calls
    assert calls == [
        (
            "trade_cal",
            {"start_date": "20260101", "end_date": "20260104"},
        )
    ]
