"""数据拉取层：TuShare API 封装、重试、限流、双通道故障转移。

核心组件：
- TuShareFetcher: 带重试 + 限流 + 双通道 failover 的数据拉取器
- RealTuShareClient: 真实 TuShare SDK 适配器（支持 tushare / tinyshare）
- SimulatedTuShareClient: 确定性离线模拟客户端（用于契约测试）
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import importlib
import time
from typing import Any, Callable, Protocol

from src.config.config import Config

# DESIGN_TRACE:
# - docs/design/core-infrastructure/data-layer/data-layer-api.md (§2 数据采集 API, §3 适配器与重试)
# - Governance/SpiralRoadmap/execution-cards/S0A-EXECUTION-CARD.md (§2 run, §3 test, §4 artifact)
DESIGN_TRACE = {
    "data_layer_api": "docs/design/core-infrastructure/data-layer/data-layer-api.md",
    "s0a_execution_card": "Governance/SpiralRoadmap/execution-cards/S0A-EXECUTION-CARD.md",
}


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
    """确定性离线模拟客户端，用于 S0b 契约测试。

    返回固定的模拟数据，不依赖网络。当 Config 中无任何 token 时自动启用。
    """

    _SIMULATED_CLOSED_TRADE_DAYS = frozenset(
        {
            # New year closure.
            "20260101",
            # 2026 lunar new year closure window.
            "20260216",
            "20260217",
            "20260218",
            "20260219",
            "20260220",
        }
    )

    @staticmethod
    def _sw31_pairs() -> list[tuple[str, str]]:
        return [
            (f"801{idx + 100:03d}.SI", f"{idx + 1:06d}")
            for idx in range(31)
        ]

    @staticmethod
    def _stock_codes() -> list[str]:
        return [f"{idx + 1:06d}" for idx in range(31)]

    @staticmethod
    def _parse_trade_date(trade_date: str) -> date:
        normalized = str(trade_date).strip()
        if len(normalized) != 8 or not normalized.isdigit():
            raise ValueError(f"invalid trade_date format: {trade_date!r}")
        return date.fromisoformat(
            f"{normalized[0:4]}-{normalized[4:6]}-{normalized[6:8]}"
        )

    @classmethod
    def _iter_trade_dates(cls, start_date: str, end_date: str) -> list[str]:
        start = cls._parse_trade_date(start_date)
        end = cls._parse_trade_date(end_date)
        if end < start:
            raise ValueError(f"trade_cal end_date({end_date}) must be >= start_date({start_date})")
        cursor = start
        values: list[str] = []
        while cursor <= end:
            values.append(cursor.strftime("%Y%m%d"))
            cursor += timedelta(days=1)
        return values

    @classmethod
    def _is_open_trade_day(cls, trade_date: str) -> bool:
        if trade_date in cls._SIMULATED_CLOSED_TRADE_DAYS:
            return False
        day = cls._parse_trade_date(trade_date)
        return day.weekday() < 5

    def call(self, api_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if api_name == "daily":
            trade_date = str(params.get("trade_date", ""))
            if not trade_date:
                raise ValueError("daily requires trade_date")
            rows: list[dict[str, Any]] = []
            for idx, stock_code in enumerate(self._stock_codes()):
                open_price = 10.0
                close_price = 10.2
                high_price = max(open_price, close_price) * 1.01
                low_price = min(open_price, close_price) * 0.99
                vol = 500000 + idx * 100
                amount = close_price * vol
                rows.append(
                    {
                        "ts_code": f"{stock_code}.SZ",
                        "stock_code": stock_code,
                        "trade_date": trade_date,
                        "open": round(open_price, 4),
                        "high": round(high_price, 4),
                        "low": round(low_price, 4),
                        "close": round(close_price, 4),
                        "vol": vol,
                        "amount": round(amount, 2),
                    }
                )
            return rows

        if api_name == "trade_cal":
            start_date = str(params.get("start_date") or params.get("end_date") or "").strip()
            end_date = str(params.get("end_date") or params.get("start_date") or "").strip()
            if not start_date or not end_date:
                raise ValueError("trade_cal requires start_date/end_date")
            exchange = str(params.get("exchange") or "SSE").strip() or "SSE"
            rows: list[dict[str, Any]] = []
            for trade_date in self._iter_trade_dates(start_date=start_date, end_date=end_date):
                rows.append(
                    {
                        "exchange": exchange,
                        "trade_date": trade_date,
                        "is_open": 1 if self._is_open_trade_day(trade_date) else 0,
                    }
                )
            return rows

        if api_name == "limit_list":
            trade_date = str(params.get("trade_date", ""))
            if not trade_date:
                raise ValueError("limit_list requires trade_date")
            rows: list[dict[str, Any]] = []
            for idx, stock_code in enumerate(self._stock_codes()):
                rows.append(
                    {
                        "ts_code": f"{stock_code}.SZ",
                        "stock_code": stock_code,
                        "trade_date": trade_date,
                        "limit_type": "U",
                        "fd_amount": float(3_560_000.0),
                    }
                )
            return rows

        if api_name == "daily_basic":
            trade_date = str(params.get("trade_date", ""))
            if not trade_date:
                raise ValueError("daily_basic requires trade_date")
            rows: list[dict[str, Any]] = []
            for idx, stock_code in enumerate(self._stock_codes()):
                rows.append(
                    {
                        "ts_code": f"{stock_code}.SZ",
                        "stock_code": stock_code,
                        "trade_date": trade_date,
                        "turnover_rate": 1.25,
                        "pe_ttm": 12.8,
                        "pb": 1.35,
                        "total_mv": float(123_000_000_000.0 + idx * 10_000_000.0),
                    }
                )
            return rows

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
                    "index_code": index_code,
                    "con_code": f"{stock_code}.SZ",
                    "in_date": "20100101",
                    "out_date": None,
                    "trade_date": trade_date,
                }
                for (index_code, _), stock_code in zip(
                    self._sw31_pairs(), self._stock_codes(), strict=False
                )
            ]

        if api_name == "index_classify":
            return [
                {
                    "index_code": index_code,
                    "industry_code": industry_code,
                    "industry_name": f"行业{idx + 1}",
                    "level": "L1",
                    "src": "SW2021",
                }
                for idx, (index_code, industry_code) in enumerate(self._sw31_pairs())
            ]

        if api_name == "stock_basic":
            return [
                {
                    "ts_code": f"{stock_code}.SZ",
                    "stock_code": stock_code,
                    "name": f"模拟股票{idx + 1}",
                    "list_status": "L",
                    "exchange": "SZSE",
                }
                for idx, stock_code in enumerate(self._stock_codes())
            ]

        raise ValueError(f"unsupported api_name: {api_name}")


class RealTuShareClient:
    """真实 TuShare SDK 适配器，用于生产环境数据拉取。

    支持 tushare / tinyshare 两种 SDK，可配置第三方网关 http_url。
    自动将 TuShare DataFrame 输出转为 list[dict] 并补全 stock_code 字段。
    """

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

    def __init__(
        self,
        *,
        token: str,
        sdk_provider: str = "tushare",
        http_url: str = "",
    ) -> None:
        sanitized = token.strip()
        if not sanitized:
            raise ValueError("tushare_token is required for real client")
        gateway_http_url = str(http_url).strip()
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
        # Some third-party gateways require explicit token/http_url injection on DataApi.
        if hasattr(self._pro, "_DataApi__token"):
            setattr(self._pro, "_DataApi__token", sanitized)
        if gateway_http_url and hasattr(self._pro, "_DataApi__http_url"):
            setattr(self._pro, "_DataApi__http_url", gateway_http_url)

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
    """带重试、限流、双通道故障转移的 TuShare 数据拉取器。

    初始化时根据 Config 自动构建 primary + fallback 两个通道。
    每次调用按通道限流等待，主通道失败自动切换兜底通道。
    重试轨迹记录在 retry_report 中，便于诊断。
    """

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
            primary_http_url = str(
                config.tushare_primary_http_url or config.tushare_http_url
            ).strip()
            fallback_token = str(config.tushare_fallback_token).strip()
            fallback_provider = str(config.tushare_fallback_sdk_provider or "tushare").strip()
            fallback_http_url = str(config.tushare_fallback_http_url).strip()

            if primary_token:
                self._clients.append(
                    (
                        "primary",
                        RealTuShareClient(
                            token=primary_token,
                            sdk_provider=primary_provider,
                            http_url=primary_http_url,
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
                            http_url=fallback_http_url,
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
        self._channel_last_call_at: dict[str, float] = {}
        self._channel_min_interval_seconds: dict[str, float] = {}
        if config is not None:
            global_rate_limit = max(0, int(config.tushare_rate_limit_per_min))
            primary_rate_limit = max(0, int(config.tushare_primary_rate_limit_per_min))
            fallback_rate_limit = max(0, int(config.tushare_fallback_rate_limit_per_min))
            for channel_name, channel_client in self._clients:
                if not isinstance(channel_client, RealTuShareClient):
                    self._channel_min_interval_seconds[channel_name] = 0.0
                    continue
                if channel_name == "primary":
                    rate_limit = primary_rate_limit if primary_rate_limit > 0 else global_rate_limit
                elif channel_name == "fallback":
                    rate_limit = fallback_rate_limit if fallback_rate_limit > 0 else global_rate_limit
                else:
                    rate_limit = global_rate_limit
                self._channel_min_interval_seconds[channel_name] = (
                    60.0 / rate_limit if rate_limit > 0 else 0.0
                )
        else:
            for channel_name, _ in self._clients:
                self._channel_min_interval_seconds[channel_name] = 0.0

    def _respect_rate_limit(self, channel_name: str) -> None:
        # 按通道独立限流：计算上次调用距今多久，不足最小间隔则 sleep
        min_interval_seconds = self._channel_min_interval_seconds.get(channel_name, 0.0)
        if min_interval_seconds <= 0:
            return
        now = self._now_fn()
        last_call_at = self._channel_last_call_at.get(channel_name)
        if last_call_at is not None:
            elapsed = now - last_call_at
            remaining = min_interval_seconds - elapsed
            if remaining > 0:
                self._sleep_fn(remaining)
                now = self._now_fn()
        self._channel_last_call_at[channel_name] = now

    def fetch_with_retry(self, api_name: str, params: dict[str, Any]) -> Any:
        attempts: list[FetchAttempt] = []
        for attempt in range(1, self.max_retries + 1):
            try:
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
        # 主通道失败时自动切换兜底通道，所有通道都失败则抛出异常
        errors: list[str] = []
        for channel_name, channel_client in self._clients:
            try:
                self._respect_rate_limit(channel_name)
                return channel_client.call(api_name, params)
            except Exception as exc:  # pragma: no cover - exercised via contract tests
                errors.append(f"{channel_name}:{exc}")
        if errors:
            raise RuntimeError("; ".join(errors))
        raise RuntimeError("no_available_tushare_client")
