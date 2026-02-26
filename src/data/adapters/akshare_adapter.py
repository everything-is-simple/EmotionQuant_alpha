"""AKShare 数据源适配器骨架。

定位：TuShare 双通道之后的第一兜底数据源。
当前仅实现接口骨架与 ``daily`` API 最小适配，不纳入主链。

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

# AKShare API 到内部标准接口的映射
_AKSHARE_API_MAP: dict[str, str] = {
    "daily": "stock_zh_a_hist",
    "trade_cal": "tool_trade_date_hist_sina",
    "index_daily": "stock_zh_index_daily",
    "stock_basic": "stock_info_a_code_name",
}

# AKShare 字段到内部标准字段的映射
_FIELD_MAP: dict[str, str] = {
    "日期": "trade_date",
    "股票代码": "stock_code",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "vol",
    "成交额": "amount",
    "涨跌幅": "pct_chg",
}


class AKShareAdapterError(RuntimeError):
    """AKShare 适配器异常。"""


class AKShareAdapter:
    """AKShare 数据源适配器（FetchClient 协议兼容）。

    实现 ``call(api_name, params) -> list[dict]`` 接口，
    可直接作为 TuShareFetcher 的备用通道注入。

    当前仅实现 ``daily`` 接口的最小适配。
    """

    _SUPPORTED_APIS = frozenset(_AKSHARE_API_MAP.keys())

    def __init__(self) -> None:
        self._ak: Any | None = None

    def _ensure_akshare(self) -> Any:
        """延迟加载 akshare 包。"""
        if self._ak is not None:
            return self._ak
        try:
            self._ak = importlib.import_module("akshare")
        except ImportError as exc:
            raise AKShareAdapterError(
                "akshare package is not installed; "
                "install via: pip install akshare"
            ) from exc
        return self._ak

    def call(self, api_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """统一入口：遵循 FetchClient 协议。"""
        if api_name not in self._SUPPORTED_APIS:
            raise AKShareAdapterError(
                f"unsupported api_name: {api_name}; "
                f"supported: {sorted(self._SUPPORTED_APIS)}"
            )
        handler = getattr(self, f"_handle_{api_name}", None)
        if handler is None:
            raise AKShareAdapterError(f"handler not implemented: {api_name}")
        return handler(params)

    # ------------------------------------------------------------------
    # daily: 最小实现（冒烟验证用）
    # ------------------------------------------------------------------
    def _handle_daily(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """获取 A 股日线行情。

        AKShare 的 ``stock_zh_a_hist`` 需要 symbol + period + start_date + end_date。
        这里做一层薄包装以兼容 TuShare 的 trade_date 参数风格。
        """
        ak = self._ensure_akshare()
        trade_date = str(params.get("trade_date", "")).strip()
        if not trade_date or len(trade_date) != 8:
            raise AKShareAdapterError("daily requires trade_date (YYYYMMDD)")

        # 转换日期格式：YYYYMMDD -> YYYY-MM-DD（AKShare 需要）
        formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"

        # AKShare stock_zh_a_hist 需要按单只股票查询
        # 骨架阶段仅支持单股查询或预设股票列表
        symbol = str(params.get("symbol", params.get("ts_code", "000001"))).strip()
        if "." in symbol:
            symbol = symbol.split(".")[0]

        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=formatted_date.replace("-", ""),
                end_date=formatted_date.replace("-", ""),
                adjust="qfq",
            )
        except Exception as exc:
            raise AKShareAdapterError(
                f"akshare daily fetch failed for {symbol}: {exc}"
            ) from exc

        if df is None or df.empty:
            return []

        rows: list[dict[str, Any]] = []
        for record in df.to_dict("records"):
            row: dict[str, Any] = {}
            for ak_field, std_field in _FIELD_MAP.items():
                if ak_field in record:
                    row[std_field] = record[ak_field]
            # 补全标准字段
            row.setdefault("trade_date", trade_date)
            row.setdefault("stock_code", symbol[:6])
            row["ts_code"] = f"{symbol[:6]}.SZ"
            rows.append(row)
        return rows

    # ------------------------------------------------------------------
    # 其他接口骨架（仅声明，不做全量实现）
    # ------------------------------------------------------------------
    def _handle_trade_cal(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """交易日历骨架（待后续实现）。"""
        raise AKShareAdapterError("trade_cal: not yet implemented in adapter skeleton")

    def _handle_index_daily(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """指数日线骨架（待后续实现）。"""
        raise AKShareAdapterError("index_daily: not yet implemented in adapter skeleton")

    def _handle_stock_basic(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """股票基本信息骨架（待后续实现）。"""
        raise AKShareAdapterError("stock_basic: not yet implemented in adapter skeleton")
