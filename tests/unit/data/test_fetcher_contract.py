"""
TuShareFetcher 契约测试。

覆盖：重试机制、模拟客户端 API 覆盖、真实 TuShare/TinyShare 通道切换、
主备通道自动降级、HTTP 网关配置、以及多通道独立频率限制。
"""
from __future__ import annotations

import types
from typing import Any

import pytest

from src.config.config import Config
from src.data.fetcher import FetchError, SimulatedTuShareClient, TuShareFetcher


class FlakyClient:
    """模拟不稳定的 API 客户端，前 N 次调用失败，之后成功。"""
    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.calls = 0

    def call(self, api_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError(f"temporary failure {self.calls}")
        return [{"api_name": api_name, "trade_date": params["trade_date"]}]


def test_fetcher_retries_then_succeeds() -> None:
    """重试次数内恢复成功时，应返回正确数据且重试报告记录完整。"""
    fetcher = TuShareFetcher(client=FlakyClient(fail_times=2), max_retries=3)
    payload = fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})

    assert payload == [{"api_name": "daily", "trade_date": "20260215"}]
    assert [item.status for item in fetcher.retry_report] == ["failed", "failed", "success"]
    assert fetcher.retry_report[-1].attempt == 3


def test_fetcher_raises_after_retry_exhausted() -> None:
    """重试次数耗尽后应抛出 FetchError，包含所有尝试记录。"""
    fetcher = TuShareFetcher(client=FlakyClient(fail_times=5), max_retries=2)

    with pytest.raises(FetchError) as exc_info:
        fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})

    assert exc_info.value.api_name == "daily"
    assert len(exc_info.value.attempts) == 2
    assert all(item.status == "failed" for item in exc_info.value.attempts)


def test_simulated_client_covers_s0b_required_apis() -> None:
    """模拟客户端必须覆盖 S0b 所需的全部 8 个 API（daily/daily_basic/trade_cal/limit_list/index_daily/index_member/index_classify/stock_basic）。"""
    fetcher = TuShareFetcher(client=SimulatedTuShareClient(), max_retries=1)
    daily_rows = fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})
    daily_basic_rows = fetcher.fetch_with_retry("daily_basic", {"trade_date": "20260215"})
    trade_cal_rows = fetcher.fetch_with_retry(
        "trade_cal", {"start_date": "20260215", "end_date": "20260215"}
    )
    limit_rows = fetcher.fetch_with_retry("limit_list", {"trade_date": "20260215"})
    index_daily_rows = fetcher.fetch_with_retry("index_daily", {"trade_date": "20260215"})
    index_member_rows = fetcher.fetch_with_retry(
        "index_member",
        {"start_date": "20260215", "end_date": "20260215"},
    )
    index_classify_rows = fetcher.fetch_with_retry("index_classify", {"src": "SW2021"})
    stock_basic_rows = fetcher.fetch_with_retry("stock_basic", {"list_status": "L"})

    assert len(daily_rows) > 0
    assert len(daily_basic_rows) > 0
    assert any(row["trade_date"] == "20260215" for row in trade_cal_rows)
    assert len(limit_rows) > 0
    assert len(index_daily_rows) > 0
    assert len(index_member_rows) > 0
    assert len(index_classify_rows) > 0
    assert len(stock_basic_rows) > 0


def test_simulated_trade_cal_marks_lunar_new_year_closure_days_as_closed() -> None:
    """模拟交易日历应正确标记春节休市日为关闭（is_open=0）。"""
    fetcher = TuShareFetcher(client=SimulatedTuShareClient(), max_retries=1)
    rows = fetcher.fetch_with_retry(
        "trade_cal",
        {"start_date": "20260212", "end_date": "20260219"},
    )

    status_by_date = {str(item["trade_date"]): int(item["is_open"]) for item in rows}
    assert status_by_date["20260212"] == 1
    assert status_by_date["20260213"] == 1
    assert status_by_date["20260218"] == 0
    assert status_by_date["20260219"] == 0


def test_fetcher_uses_real_tushare_client_when_token_exists(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """配置了 TUSHARE_TOKEN 时，应使用真实 TuShare SDK，并正确将 ts_code 转换为 stock_code。"""
    class FakeProApi:
        def daily(self, **_: Any) -> list[dict[str, Any]]:
            return [{"ts_code": "000001.SZ", "trade_date": "20260215"}]

        def daily_basic(self, **_: Any) -> list[dict[str, Any]]:
            return [{"ts_code": "000001.SZ", "trade_date": "20260215", "turnover_rate": 1.0}]

        def trade_cal(self, **_: Any) -> list[dict[str, Any]]:
            return [{"exchange": "SSE", "cal_date": "20260215", "is_open": 1}]

        def limit_list_d(self, **_: Any) -> list[dict[str, Any]]:
            return [{"ts_code": "000002.SZ", "trade_date": "20260215", "limit_type": "U"}]

        def index_daily(self, **_: Any) -> list[dict[str, Any]]:
            return [{"ts_code": "000001.SH", "trade_date": "20260215", "pct_chg": 0.2}]

        def index_member(self, **_: Any) -> list[dict[str, Any]]:
            return [{"index_code": "801010.SI", "con_code": "000001.SZ"}]

        def index_classify(self, **_: Any) -> list[dict[str, Any]]:
            return [{"index_code": "801010.SI", "industry_name": "农林牧渔"}]

        def stock_basic(self, **_: Any) -> list[dict[str, Any]]:
            return [{"ts_code": "000002.SZ", "name": "万科A"}]

    fake_tushare = types.SimpleNamespace(pro_api=lambda _token: FakeProApi())
    monkeypatch.setitem(__import__("sys").modules, "tushare", fake_tushare)

    env_file = tmp_path / ".env.fetcher.real"
    env_file.write_text(
        "ENVIRONMENT=test\n"
        "TUSHARE_TOKEN=test_token\n"
        "TUSHARE_RATE_LIMIT_PER_MIN=6000\n",
        encoding="utf-8",
    )
    config = Config.from_env(env_file=str(env_file))
    fetcher = TuShareFetcher(config=config, max_retries=1)

    daily_rows = fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})
    daily_basic_rows = fetcher.fetch_with_retry("daily_basic", {"trade_date": "20260215"})
    trade_cal_rows = fetcher.fetch_with_retry(
        "trade_cal", {"start_date": "20260215", "end_date": "20260215"}
    )
    limit_rows = fetcher.fetch_with_retry("limit_list", {"trade_date": "20260215"})
    index_daily_rows = fetcher.fetch_with_retry("index_daily", {"trade_date": "20260215"})
    index_member_rows = fetcher.fetch_with_retry(
        "index_member",
        {"start_date": "20260215", "end_date": "20260215"},
    )
    index_classify_rows = fetcher.fetch_with_retry("index_classify", {"src": "SW2021"})
    stock_basic_rows = fetcher.fetch_with_retry("stock_basic", {"list_status": "L"})

    assert daily_rows[0]["stock_code"] == "000001"
    assert daily_basic_rows[0]["stock_code"] == "000001"
    assert trade_cal_rows[0]["trade_date"] == "20260215"
    assert trade_cal_rows[0]["is_open"] == 1
    assert limit_rows[0]["stock_code"] == "000002"
    assert index_daily_rows[0]["trade_date"] == "20260215"
    assert index_member_rows[0]["stock_code"] == "000001"
    assert index_classify_rows[0]["index_code"] == "801010.SI"
    assert stock_basic_rows[0]["stock_code"] == "000002"


def test_fetcher_uses_tinyshare_provider_when_configured(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """配置 SDK_PROVIDER=tinyshare 时，应使用 tinyshare 通道获取数据。"""
    class FakeTinyProApi:
        def daily(self, **_: Any) -> list[dict[str, Any]]:
            return [{"ts_code": "000333.SZ", "trade_date": "20260215"}]

        def daily_basic(self, **_: Any) -> list[dict[str, Any]]:
            return [{"ts_code": "000333.SZ", "trade_date": "20260215", "turnover_rate": 0.9}]

        def trade_cal(self, **_: Any) -> list[dict[str, Any]]:
            return [{"exchange": "SSE", "cal_date": "20260215", "is_open": 1}]

        def limit_list_d(self, **_: Any) -> list[dict[str, Any]]:
            return [{"ts_code": "000001.SZ", "trade_date": "20260215", "limit_type": "U"}]

        def index_daily(self, **_: Any) -> list[dict[str, Any]]:
            return [{"ts_code": "000001.SH", "trade_date": "20260215", "pct_chg": 0.1}]

        def index_member(self, **_: Any) -> list[dict[str, Any]]:
            return [{"index_code": "801010.SI", "con_code": "000333.SZ"}]

        def index_classify(self, **_: Any) -> list[dict[str, Any]]:
            return [{"index_code": "801010.SI", "industry_name": "农林牧渔"}]

        def stock_basic(self, **_: Any) -> list[dict[str, Any]]:
            return [{"ts_code": "000333.SZ", "name": "美的集团"}]

    fake_tinyshare = types.SimpleNamespace(pro_api=lambda _token: FakeTinyProApi())
    monkeypatch.setitem(__import__("sys").modules, "tinyshare", fake_tinyshare)

    env_file = tmp_path / ".env.fetcher.tiny"
    env_file.write_text(
        "ENVIRONMENT=test\n"
        "TUSHARE_TOKEN=test_token\n"
        "TUSHARE_SDK_PROVIDER=tinyshare\n"
        "TUSHARE_RATE_LIMIT_PER_MIN=6000\n",
        encoding="utf-8",
    )
    config = Config.from_env(env_file=str(env_file))
    fetcher = TuShareFetcher(config=config, max_retries=1)

    daily_rows = fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})
    daily_basic_rows = fetcher.fetch_with_retry("daily_basic", {"trade_date": "20260215"})
    trade_cal_rows = fetcher.fetch_with_retry(
        "trade_cal", {"start_date": "20260215", "end_date": "20260215"}
    )
    limit_rows = fetcher.fetch_with_retry("limit_list", {"trade_date": "20260215"})
    index_daily_rows = fetcher.fetch_with_retry("index_daily", {"trade_date": "20260215"})
    index_member_rows = fetcher.fetch_with_retry(
        "index_member",
        {"start_date": "20260215", "end_date": "20260215"},
    )
    index_classify_rows = fetcher.fetch_with_retry("index_classify", {"src": "SW2021"})
    stock_basic_rows = fetcher.fetch_with_retry("stock_basic", {"list_status": "L"})

    assert daily_rows[0]["stock_code"] == "000333"
    assert daily_basic_rows[0]["stock_code"] == "000333"
    assert trade_cal_rows[0]["trade_date"] == "20260215"
    assert limit_rows[0]["stock_code"] == "000001"
    assert index_daily_rows[0]["trade_date"] == "20260215"
    assert index_member_rows[0]["stock_code"] == "000333"
    assert index_classify_rows[0]["industry_name"] == "农林牧渔"
    assert stock_basic_rows[0]["stock_code"] == "000333"


def test_fetcher_applies_primary_http_url_when_configured(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """配置了 HTTP_URL 时，TuShare SDK 应指向指定网关地址。"""
    class FakeGatewayProApi:
        def __init__(self) -> None:
            self._DataApi__http_url = ""
            self._DataApi__token = ""

        def daily(self, **_: Any) -> list[dict[str, Any]]:
            return [
                {
                    "ts_code": "000001.SZ",
                    "trade_date": "20260215",
                    "gateway_url": self._DataApi__http_url,
                }
            ]

    fake_tushare = types.SimpleNamespace(pro_api=lambda _token: FakeGatewayProApi())
    monkeypatch.setitem(__import__("sys").modules, "tushare", fake_tushare)

    env_file = tmp_path / ".env.fetcher.gateway"
    env_file.write_text(
        "ENVIRONMENT=test\n"
        "TUSHARE_TOKEN=test_token\n"
        "TUSHARE_SDK_PROVIDER=tushare\n"
        "TUSHARE_HTTP_URL=http://106.54.191.157:5000\n"
        "TUSHARE_RATE_LIMIT_PER_MIN=6000\n",
        encoding="utf-8",
    )
    config = Config.from_env(env_file=str(env_file))
    fetcher = TuShareFetcher(config=config, max_retries=1)

    rows = fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})

    assert rows[0]["stock_code"] == "000001"
    assert rows[0]["gateway_url"] == "http://106.54.191.157:5000"


def test_fetcher_falls_back_to_official_channel_when_primary_fails(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """主通道失败时应自动降级到备用通道，并返回备用数据。"""
    counters = {"primary_daily_calls": 0, "fallback_daily_calls": 0}

    class FakePrimaryProApi:
        def daily(self, **_: Any) -> list[dict[str, Any]]:
            counters["primary_daily_calls"] += 1
            raise RuntimeError("primary_temporarily_unavailable")

    class FakeFallbackProApi:
        def daily(self, **_: Any) -> list[dict[str, Any]]:
            counters["fallback_daily_calls"] += 1
            return [{"ts_code": "000001.SZ", "trade_date": "20260215"}]

    fake_tinyshare = types.SimpleNamespace(pro_api=lambda _token: FakePrimaryProApi())
    fake_tushare = types.SimpleNamespace(pro_api=lambda _token: FakeFallbackProApi())
    monkeypatch.setitem(__import__("sys").modules, "tinyshare", fake_tinyshare)
    monkeypatch.setitem(__import__("sys").modules, "tushare", fake_tushare)

    env_file = tmp_path / ".env.fetcher.dual"
    env_file.write_text(
        "ENVIRONMENT=test\n"
        "TUSHARE_PRIMARY_TOKEN=trial_token\n"
        "TUSHARE_PRIMARY_SDK_PROVIDER=tinyshare\n"
        "TUSHARE_FALLBACK_TOKEN=official_token\n"
        "TUSHARE_FALLBACK_SDK_PROVIDER=tushare\n"
        "TUSHARE_RATE_LIMIT_PER_MIN=6000\n",
        encoding="utf-8",
    )
    config = Config.from_env(env_file=str(env_file))
    fetcher = TuShareFetcher(config=config, max_retries=1)

    rows = fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})

    assert rows[0]["stock_code"] == "000001"
    assert counters["primary_daily_calls"] == 1
    assert counters["fallback_daily_calls"] == 1


class FakeClock:
    """模拟时钟，用于测试频率限制逻辑而无需真实等待。"""
    def __init__(self) -> None:
        self.current = 0.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.current += seconds


def test_fetcher_applies_primary_channel_rate_limit_when_configured(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """主通道配置独立频率限制时，调用间隔应符合其专属限速。"""
    class FakeProApi:
        def daily(self, **_: Any) -> list[dict[str, Any]]:
            return [{"ts_code": "000001.SZ", "trade_date": "20260215"}]

    fake_tushare = types.SimpleNamespace(pro_api=lambda _token: FakeProApi())
    monkeypatch.setitem(__import__("sys").modules, "tushare", fake_tushare)
    monkeypatch.setenv("TUSHARE_RATE_LIMIT_PER_MIN", "6000")
    monkeypatch.setenv("TUSHARE_PRIMARY_RATE_LIMIT_PER_MIN", "30")

    env_file = tmp_path / ".env.fetcher.primary.rate"
    env_file.write_text(
        "ENVIRONMENT=test\n"
        "TUSHARE_PRIMARY_TOKEN=official_token\n"
        "TUSHARE_PRIMARY_SDK_PROVIDER=tushare\n"
        "TUSHARE_RATE_LIMIT_PER_MIN=6000\n"
        "TUSHARE_PRIMARY_RATE_LIMIT_PER_MIN=30\n",
        encoding="utf-8",
    )
    config = Config.from_env(env_file=str(env_file))
    clock = FakeClock()
    fetcher = TuShareFetcher(
        config=config,
        max_retries=1,
        now_fn=clock.now,
        sleep_fn=clock.sleep,
    )

    fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})
    fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})

    assert len(clock.sleeps) == 1
    assert clock.sleeps[0] == pytest.approx(2.0, abs=1e-6)


def test_fetcher_applies_fallback_channel_rate_limit_when_primary_unlimited(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """备用通道配置独立频率限制时，降级后的调用应按备用通道限速等待。"""
    class FakePrimaryProApi:
        def daily(self, **_: Any) -> list[dict[str, Any]]:
            raise RuntimeError("primary_temporarily_unavailable")

    class FakeFallbackProApi:
        def daily(self, **_: Any) -> list[dict[str, Any]]:
            return [{"ts_code": "000001.SZ", "trade_date": "20260215"}]

    fake_tinyshare = types.SimpleNamespace(pro_api=lambda _token: FakePrimaryProApi())
    fake_tushare = types.SimpleNamespace(pro_api=lambda _token: FakeFallbackProApi())
    monkeypatch.setitem(__import__("sys").modules, "tinyshare", fake_tinyshare)
    monkeypatch.setitem(__import__("sys").modules, "tushare", fake_tushare)
    monkeypatch.setenv("TUSHARE_RATE_LIMIT_PER_MIN", "0")
    monkeypatch.setenv("TUSHARE_PRIMARY_RATE_LIMIT_PER_MIN", "0")
    monkeypatch.setenv("TUSHARE_FALLBACK_RATE_LIMIT_PER_MIN", "30")

    env_file = tmp_path / ".env.fetcher.fallback.rate"
    env_file.write_text(
        "ENVIRONMENT=test\n"
        "TUSHARE_PRIMARY_TOKEN=trial_token\n"
        "TUSHARE_PRIMARY_SDK_PROVIDER=tinyshare\n"
        "TUSHARE_FALLBACK_TOKEN=official_token\n"
        "TUSHARE_FALLBACK_SDK_PROVIDER=tushare\n"
        "TUSHARE_RATE_LIMIT_PER_MIN=0\n"
        "TUSHARE_FALLBACK_RATE_LIMIT_PER_MIN=30\n",
        encoding="utf-8",
    )
    config = Config.from_env(env_file=str(env_file))
    clock = FakeClock()
    fetcher = TuShareFetcher(
        config=config,
        max_retries=1,
        now_fn=clock.now,
        sleep_fn=clock.sleep,
    )

    fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})
    fetcher.fetch_with_retry("daily", {"trade_date": "20260215"})

    assert len(clock.sleeps) == 1
    assert clock.sleeps[0] == pytest.approx(2.0, abs=1e-6)
