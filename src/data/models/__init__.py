"""数据模型定义，与 docs/design/core-infrastructure/data-layer/data-layer-data-models.md 对齐。

包含：
- StockBasic: 股票基本信息（ts_code / 名称 / 行业 / 上市日期）
- TradeCalendar: 交易日历（交易日 / 是否开市 / 前一交易日）
- MarketSnapshot: 市场快照（L2 层，涨跌家数 / 涨停 / 波动率等）
- IndustrySnapshot: 行业快照（L2 层，申万一级行业维度聚合）
"""

from src.data.models.entities import StockBasic, TradeCalendar
from src.data.models.snapshots import IndustrySnapshot, MarketSnapshot

__all__ = [
    "StockBasic",
    "TradeCalendar",
    "MarketSnapshot",
    "IndustrySnapshot",
]
