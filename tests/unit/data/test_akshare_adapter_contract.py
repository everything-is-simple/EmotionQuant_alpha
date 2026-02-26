"""AKShare 适配器契约测试。

验证：
- FetchClient 协议兼容性（call 接口签名）
- daily API 字段映射与标准化
- 未支持 API 的错误处理
- akshare 未安装时的优雅降级
"""
from __future__ import annotations

import types
from typing import Any

import pandas as pd
import pytest

from src.data.adapters.akshare_adapter import AKShareAdapter, AKShareAdapterError


class FakeAKShareModule:
    """模拟 akshare 模块，返回固定数据用于冒烟测试。"""

    @staticmethod
    def stock_zh_a_hist(
        *,
        symbol: str,
        period: str = "daily",
        start_date: str = "",
        end_date: str = "",
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "日期": start_date,
                    "股票代码": symbol,
                    "开盘": 10.00,
                    "收盘": 10.20,
                    "最高": 10.30,
                    "最低": 9.95,
                    "成交量": 500000,
                    "成交额": 5100000.0,
                    "涨跌幅": 2.0,
                }
            ]
        )


def test_akshare_adapter_daily_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """AKShare daily 接口冒烟测试：字段映射 + 标准化输出。"""
    fake_module = FakeAKShareModule()
    monkeypatch.setitem(
        __import__("sys").modules, "akshare", types.SimpleNamespace(**{
            "stock_zh_a_hist": fake_module.stock_zh_a_hist,
        })
    )

    adapter = AKShareAdapter()
    rows = adapter.call("daily", {
        "trade_date": "20260213",
        "symbol": "000001",
    })

    assert len(rows) == 1
    row = rows[0]
    # 标准字段存在
    assert row["stock_code"] == "000001"
    assert row["ts_code"] == "000001.SZ"
    assert row["trade_date"] == "20260213"
    assert "open" in row
    assert "close" in row
    assert "high" in row
    assert "low" in row
    assert "vol" in row
    assert "amount" in row


def test_akshare_adapter_protocol_compliance() -> None:
    """AKShare 适配器实现 FetchClient 协议（具有 call 方法）。"""
    adapter = AKShareAdapter()
    assert callable(getattr(adapter, "call", None))


def test_akshare_adapter_unsupported_api_raises() -> None:
    """不支持的 API 应抛出 AKShareAdapterError。"""
    adapter = AKShareAdapter()
    with pytest.raises(AKShareAdapterError, match="unsupported"):
        adapter.call("nonexistent_api", {})


def test_akshare_adapter_daily_missing_trade_date() -> None:
    """daily 缺少 trade_date 参数应抛出错误。"""
    adapter = AKShareAdapter()
    # 强制跳过 akshare 包检查
    adapter._ak = types.SimpleNamespace()
    with pytest.raises(AKShareAdapterError, match="trade_date"):
        adapter.call("daily", {})


def test_akshare_adapter_import_error_when_package_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """akshare 未安装时应抛出明确的 AKShareAdapterError。"""
    # 确保 akshare 不在 sys.modules 中
    import sys
    monkeypatch.delitem(sys.modules, "akshare", raising=False)
    monkeypatch.setattr(
        "importlib.import_module",
        lambda name: (_ for _ in ()).throw(ImportError(f"No module named {name!r}")),
    )
    adapter = AKShareAdapter()
    with pytest.raises(AKShareAdapterError, match="not installed"):
        adapter.call("daily", {"trade_date": "20260213"})


def test_akshare_adapter_ts_code_format_strip() -> None:
    """ts_code 带后缀（如 000001.SZ）时应自动去除后缀。"""
    # 仅测试参数处理逻辑，不实际调用 akshare
    adapter = AKShareAdapter()

    fake_calls: list[dict[str, Any]] = []

    def fake_stock_zh_a_hist(*, symbol: str, **kwargs: Any) -> pd.DataFrame:
        fake_calls.append({"symbol": symbol, **kwargs})
        return pd.DataFrame(
            [{"日期": "20260213", "股票代码": symbol, "开盘": 10.0, "收盘": 10.2,
              "最高": 10.3, "最低": 9.9, "成交量": 100000, "成交额": 1020000.0}]
        )

    adapter._ak = types.SimpleNamespace(stock_zh_a_hist=fake_stock_zh_a_hist)
    rows = adapter.call("daily", {"trade_date": "20260213", "ts_code": "000001.SZ"})

    assert len(rows) == 1
    assert fake_calls[0]["symbol"] == "000001"
    assert rows[0]["stock_code"] == "000001"
