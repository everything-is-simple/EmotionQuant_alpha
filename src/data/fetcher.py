from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class FetchClient(Protocol):
    def call(self, api_name: str, params: dict[str, Any]) -> Any:
        ...


@dataclass(frozen=True)
class FetchAttempt:
    api_name: str
    attempt: int
    status: str
    error: str = ""


class FetchError(RuntimeError):
    def __init__(self, api_name: str, attempts: list[FetchAttempt]) -> None:
        self.api_name = api_name
        self.attempts = attempts
        last_error = attempts[-1].error if attempts else "unknown"
        super().__init__(f"fetch failed for {api_name}: {last_error}")


class SimulatedTuShareClient:
    """Deterministic offline TuShare-like client for S0b contract tests."""

    def call(self, api_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if api_name == "daily":
            trade_date = str(params.get("trade_date", ""))
            if not trade_date:
                raise ValueError("daily requires trade_date")
            return [
                {
                    "ts_code": "000001.SZ",
                    "stock_code": "000001",
                    "trade_date": trade_date,
                    "open": 10.0,
                    "high": 10.4,
                    "low": 9.8,
                    "close": 10.2,
                    "vol": 1200000,
                    "amount": 12240000.0,
                }
            ]

        if api_name == "trade_cal":
            trade_date = str(params.get("start_date") or params.get("end_date") or "")
            if not trade_date:
                raise ValueError("trade_cal requires start_date/end_date")
            return [
                {
                    "exchange": "SSE",
                    "trade_date": trade_date,
                    "is_open": 1,
                }
            ]

        if api_name == "limit_list":
            trade_date = str(params.get("trade_date", ""))
            if not trade_date:
                raise ValueError("limit_list requires trade_date")
            return [
                {
                    "ts_code": "000001.SZ",
                    "stock_code": "000001",
                    "trade_date": trade_date,
                    "limit_type": "U",
                    "fd_amount": 3560000.0,
                }
            ]

        raise ValueError(f"unsupported api_name: {api_name}")


class TuShareFetcher:
    """TuShare data fetcher with retry tracing."""

    def __init__(self, client: FetchClient | None = None, max_retries: int = 3) -> None:
        self.client = client or SimulatedTuShareClient()
        self.max_retries = max(1, max_retries)
        self.retry_report: list[FetchAttempt] = []

    def fetch_with_retry(self, api_name: str, params: dict[str, Any]) -> Any:
        attempts: list[FetchAttempt] = []
        for attempt in range(1, self.max_retries + 1):
            try:
                payload = self.client.call(api_name, params)
                item = FetchAttempt(
                    api_name=api_name,
                    attempt=attempt,
                    status="success",
                )
                attempts.append(item)
                self.retry_report.append(item)
                return payload
            except Exception as exc:  # pragma: no cover - exercised via tests
                item = FetchAttempt(
                    api_name=api_name,
                    attempt=attempt,
                    status="failed",
                    error=str(exc),
                )
                attempts.append(item)
                self.retry_report.append(item)
                if attempt >= self.max_retries:
                    raise FetchError(api_name=api_name, attempts=attempts) from exc

        raise FetchError(api_name=api_name, attempts=attempts)
