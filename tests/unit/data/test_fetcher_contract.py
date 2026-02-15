from __future__ import annotations

from typing import Any

import pytest

from src.data.fetcher import FetchError, SimulatedTuShareClient, TuShareFetcher


class FlakyClient:
    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.calls = 0

    def call(self, api_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError(f"temporary failure {self.calls}")
        return [{"api_name": api_name, "trade_date": params["trade_date"]}]


def test_fetcher_retries_then_succeeds() -> None:
    fetcher = TuShareFetcher(client=FlakyClient(fail_times=2), max_retries=3)
    payload = fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})

    assert payload == [{"api_name": "daily", "trade_date": "20260215"}]
    assert [item.status for item in fetcher.retry_report] == ["failed", "failed", "success"]
    assert fetcher.retry_report[-1].attempt == 3


def test_fetcher_raises_after_retry_exhausted() -> None:
    fetcher = TuShareFetcher(client=FlakyClient(fail_times=5), max_retries=2)

    with pytest.raises(FetchError) as exc_info:
        fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})

    assert exc_info.value.api_name == "daily"
    assert len(exc_info.value.attempts) == 2
    assert all(item.status == "failed" for item in exc_info.value.attempts)


def test_simulated_client_covers_s0b_required_apis() -> None:
    fetcher = TuShareFetcher(client=SimulatedTuShareClient(), max_retries=1)
    daily_rows = fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})
    trade_cal_rows = fetcher.fetch_with_retry(
        "trade_cal", {"start_date": "20260215", "end_date": "20260215"}
    )
    limit_rows = fetcher.fetch_with_retry("limit_list", {"trade_date": "20260215"})

    assert len(daily_rows) > 0
    assert any(row["trade_date"] == "20260215" for row in trade_cal_rows)
    assert len(limit_rows) > 0
