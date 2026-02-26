"""BaoStock 数据源适配器骨架。

定位：TuShare 双通道 + AKShare 之后的第二兜底数据源。
当前仅实现接口骨架，不纳入主链。

DESIGN_TRACE:
- docs/reference/data-source-fallback-plan.md (§5 实施计划)
- docs/design/core-infrastructure/data-layer/data-layer-api.md (§2 数据采集 API)
- Governance/SpiralRoadmap/execution-cards/DEBT-CARD-C-BACKLOG.md (TD-S3A-015)
"""

from __future__ import annotations

import importlib
from typing import Any

DESIGN_TRACE = {
    "data_source_fallback_plan": "docs/reference/data-source-fallback-plan.md",
    "data_layer_api": "docs/design/core-infrastructure/data-layer/data-layer-api.md",
    "debt_card_c": "Governance/SpiralRoadmap/execution-cards/DEBT-CARD-C-BACKLOG.md",
}

# BaoStock 行业分类到申万一级行业的映射骨架
BAOSTOCK_TO_SW_INDUSTRY: dict[str, str] = {
    "A01": "801010",  # 农林牧渔
    "B06": "801020",  # 采掘
    "C13": "801030",  # 化工
    # ... 后续按需补全
}


class BaoStockAdapterError(RuntimeError):
    """BaoStock 适配器异常。"""


class BaoStockAdapter:
    """BaoStock 数据源适配器（FetchClient 协议兼容）。

    实现 ``call(api_name, params) -> list[dict]`` 接口，
    可直接作为 TuShareFetcher 的备用通道注入。

    当前仅实现接口声明，全量适配待后续圈实现。
    """

    _SUPPORTED_APIS = frozenset({"daily", "trade_cal", "stock_basic"})

    def __init__(self) -> None:
        self._bs: Any | None = None

    def _ensure_baostock(self) -> Any:
        """延迟加载 baostock 包。"""
        if self._bs is not None:
            return self._bs
        try:
            self._bs = importlib.import_module("baostock")
        except ImportError as exc:
            raise BaoStockAdapterError(
                "baostock package is not installed; "
                "install via: pip install baostock"
            ) from exc
        return self._bs

    def call(self, api_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """统一入口：遵循 FetchClient 协议。"""
        if api_name not in self._SUPPORTED_APIS:
            raise BaoStockAdapterError(
                f"unsupported api_name: {api_name}; "
                f"supported: {sorted(self._SUPPORTED_APIS)}"
            )
        handler = getattr(self, f"_handle_{api_name}", None)
        if handler is None:
            raise BaoStockAdapterError(f"handler not implemented: {api_name}")
        return handler(params)

    def _handle_daily(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """日线行情骨架（待后续实现）。"""
        raise BaoStockAdapterError("daily: not yet implemented in adapter skeleton")

    def _handle_trade_cal(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """交易日历骨架（待后续实现）。"""
        raise BaoStockAdapterError("trade_cal: not yet implemented in adapter skeleton")

    def _handle_stock_basic(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """股票基本信息骨架（待后续实现）。"""
        raise BaoStockAdapterError("stock_basic: not yet implemented in adapter skeleton")
