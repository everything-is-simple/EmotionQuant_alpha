from __future__ import annotations

from dataclasses import dataclass
import importlib
import time
from typing import Any, Callable, Protocol

from src.config.config import Config


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

        if api_name == "daily_basic":
            trade_date = str(params.get("trade_date", ""))
            if not trade_date:
                raise ValueError("daily_basic requires trade_date")
            return [
                {
                    "ts_code": "000001.SZ",
                    "stock_code": "000001",
                    "trade_date": trade_date,
                    "turnover_rate": 1.25,
                    "pe_ttm": 12.8,
                    "pb": 1.35,
                    "total_mv": 123000000000.0,
                }
            ]

        if api_name == "index_daily":
            trade_date = str(params.get("trade_date", ""))
            if not trade_date:
                raise ValueError("index_daily requires trade_date")
            return [
                {
                    "ts_code": "000001.SH",
                    "trade_date": trade_date,
                    "open": 3200.0,
                    "high": 3210.0,
                    "low": 3185.0,
                    "close": 3205.0,
                    "pct_chg": 0.42,
                }
            ]

        if api_name == "index_member":
            trade_date = str(
                params.get("trade_date", "")
                or params.get("start_date", "")
                or params.get("end_date", "")
            )
            return [
                {
                    "index_code": "801010.SI",
                    "con_code": "000001.SZ",
                    "in_date": "20100101",
                    "out_date": None,
                    "trade_date": trade_date,
                }
            ]

        if api_name == "index_classify":
            return [
                {
                    "index_code": "801010.SI",
                    "industry_name": "农林牧渔",
                    "level": "L1",
                    "src": "SW2021",
                }
            ]

        if api_name == "stock_basic":
            return [
                {
                    "ts_code": "000001.SZ",
                    "stock_code": "000001",
                    "name": "平安银行",
                    "list_status": "L",
                    "exchange": "SZSE",
                }
            ]

        raise ValueError(f"unsupported api_name: {api_name}")


class RealTuShareClient:
    """Real TuShare client adapter for production fetch flow."""

    _API_METHOD_MAP = {
        "daily": "daily",
        "daily_basic": "daily_basic",
        "trade_cal": "trade_cal",
        "limit_list": "limit_list_d",
        "index_daily": "index_daily",
        "index_member": "index_member",
        "index_classify": "index_classify",
        "stock_basic": "stock_basic",
    }
    _SDK_MODULES = {
        "tushare": "tushare",
        "tinyshare": "tinyshare",
    }

    def __init__(self, *, token: str, sdk_provider: str = "tushare") -> None:
        sanitized = token.strip()
        if not sanitized:
            raise ValueError("tushare_token is required for real client")
        provider = str(sdk_provider).strip().lower() or "tushare"
        module_name = self._SDK_MODULES.get(provider)
        if module_name is None:
            supported = ", ".join(sorted(self._SDK_MODULES))
            raise ValueError(
                f"unsupported tushare sdk provider: {sdk_provider!r}; supported: {supported}"
            )
        try:
            ts = importlib.import_module(module_name)
        except ImportError as exc:  # pragma: no cover - depends on runtime env
            raise RuntimeError(f"{module_name} package is not installed") from exc
        self._pro = ts.pro_api(sanitized)

    def call(self, api_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        method_name = self._API_METHOD_MAP.get(api_name)
        if method_name is None:
            raise ValueError(f"unsupported api_name: {api_name}")
        method = getattr(self._pro, method_name, None)
        if method is None and api_name == "limit_list":
            method = getattr(self._pro, "limit_list", None)
        if method is None:
            raise RuntimeError(f"tushare api not available: {method_name}")
        payload = method(**params)
        rows = self._normalize_records(payload)
        return self._normalize_fields(api_name=api_name, rows=rows, request_params=params)

    def _normalize_records(self, payload: Any) -> list[dict[str, Any]]:
        if payload is None:
            return []
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if hasattr(payload, "to_dict"):
            records = payload.to_dict(orient="records")
            return [row for row in records if isinstance(row, dict)]
        raise TypeError(f"unsupported payload type from tushare: {type(payload)!r}")

    def _normalize_fields(
        self,
        *,
        api_name: str,
        rows: list[dict[str, Any]],
        request_params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        requested_trade_date = str(
            request_params.get("trade_date", "")
            or request_params.get("start_date", "")
            or request_params.get("end_date", "")
        ).strip()
        for row in rows:
            item = dict(row)
            if api_name == "trade_cal" and not item.get("trade_date"):
                cal_date = str(item.get("cal_date", "")).strip()
                if cal_date:
                    item["trade_date"] = cal_date
            if (
                api_name in {"daily", "daily_basic", "index_daily", "limit_list", "index_member"}
                and not str(item.get("trade_date", "")).strip()
                and requested_trade_date
            ):
                item["trade_date"] = requested_trade_date
            ts_code = str(item.get("ts_code", ""))
            if (
                api_name in {"daily", "daily_basic", "limit_list", "stock_basic"}
                and not item.get("stock_code")
                and len(ts_code) >= 6
            ):
                item["stock_code"] = ts_code[:6]
            if api_name == "index_member":
                con_code = str(item.get("con_code", "")).strip()
                if not ts_code and con_code:
                    item["ts_code"] = con_code
                    ts_code = con_code
                if not item.get("stock_code") and len(ts_code) >= 6:
                    item["stock_code"] = ts_code[:6]
            normalized.append(item)
        return normalized


class TuShareFetcher:
    """TuShare data fetcher with retry tracing."""

    def __init__(
        self,
        client: FetchClient | None = None,
        max_retries: int = 3,
        *,
        config: Config | None = None,
        now_fn: Callable[[], float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self._clients: list[tuple[str, FetchClient]] = []
        if client is not None:
            self._clients = [("custom", client)]
        elif config is not None:
            primary_token = str(
                config.tushare_primary_token or config.tushare_token
            ).strip()
            primary_provider = str(
                config.tushare_primary_sdk_provider or config.tushare_sdk_provider or "tushare"
            ).strip()
            fallback_token = str(config.tushare_fallback_token).strip()
            fallback_provider = str(config.tushare_fallback_sdk_provider or "tushare").strip()

            if primary_token:
                self._clients.append(
                    (
                        "primary",
                        RealTuShareClient(
                            token=primary_token,
                            sdk_provider=primary_provider,
                        ),
                    )
                )
            if fallback_token and (fallback_token != primary_token or fallback_provider != primary_provider):
                self._clients.append(
                    (
                        "fallback",
                        RealTuShareClient(
                            token=fallback_token,
                            sdk_provider=fallback_provider,
                        ),
                    )
                )
        if not self._clients:
            self._clients = [("simulated", SimulatedTuShareClient())]
        # Keep legacy attribute for compatibility with existing callers/tests.
        self.client = self._clients[0][1]
        self.max_retries = max(1, max_retries)
        self.retry_report: list[FetchAttempt] = []
        self._now_fn = now_fn or time.monotonic
        self._sleep_fn = sleep_fn or time.sleep
        self._last_call_at: float | None = None
        self._min_interval_seconds = 0.0
        if config is not None and any(
            isinstance(channel_client, RealTuShareClient) for _, channel_client in self._clients
        ):
            rate_limit = max(0, int(config.tushare_rate_limit_per_min))
            self._min_interval_seconds = 60.0 / rate_limit if rate_limit > 0 else 0.0

    def _respect_rate_limit(self) -> None:
        if self._min_interval_seconds <= 0:
            return
        now = self._now_fn()
        if self._last_call_at is not None:
            elapsed = now - self._last_call_at
            remaining = self._min_interval_seconds - elapsed
            if remaining > 0:
                self._sleep_fn(remaining)
                now = self._now_fn()
        self._last_call_at = now

    def fetch_with_retry(self, api_name: str, params: dict[str, Any]) -> Any:
        attempts: list[FetchAttempt] = []
        for attempt in range(1, self.max_retries + 1):
            try:
                self._respect_rate_limit()
                payload = self._call_with_failover(api_name=api_name, params=params)
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

    def _call_with_failover(self, *, api_name: str, params: dict[str, Any]) -> Any:
        errors: list[str] = []
        for channel_name, channel_client in self._clients:
            try:
                return channel_client.call(api_name, params)
            except Exception as exc:  # pragma: no cover - exercised via contract tests
                errors.append(f"{channel_name}:{exc}")
        if errors:
            raise RuntimeError("; ".join(errors))
        raise RuntimeError("no_available_tushare_client")
