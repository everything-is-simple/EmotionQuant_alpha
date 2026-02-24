"""L1 基础实体模型。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StockBasic:
    """股票基本信息（对应 raw_stock_basic 表）。

    - ts_code: TuShare 格式代码，如 '000001.SZ'
    - name: 股票名称
    - industry: 所属行业
    - list_date: 上市日期（YYYYMMDD）
    """
    ts_code: str
    name: str
    industry: str = ""
    list_date: str = ""


@dataclass(frozen=True)
class TradeCalendar:
    """交易日历（对应 raw_trade_cal 表）。

    - trade_date: 日期（YYYYMMDD）
    - is_open: 是否为交易日（1=开市，0=休市）
    - pretrade_date: 前一交易日
    """
    trade_date: str
    is_open: int
    pretrade_date: str = ""
