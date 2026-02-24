"""数据模型契约对齐测试。

验证各 dataclass 模型包含上下游约定的必要字段，
确保模型定义与 MSS/IRS 算法输入契约保持一致。
"""
from __future__ import annotations

from dataclasses import fields

from src.data.models.entities import StockBasic, TradeCalendar
from src.data.models.snapshots import IndustrySnapshot, MarketSnapshot


def _field_names(model_cls: type) -> set[str]:
    """提取 dataclass 类的所有字段名。"""
    return {f.name for f in fields(model_cls)}


def test_entities_include_data_layer_core_fields() -> None:
    """实体模型必须包含数据层核心字段（股票基本信息、交易日历）。"""
    assert {"ts_code", "name", "industry", "list_date"} <= _field_names(StockBasic)
    assert {"trade_date", "is_open", "pretrade_date"} <= _field_names(TradeCalendar)


def test_market_snapshot_includes_mss_input_fields() -> None:
    """MarketSnapshot 必须包含 MSS（市场情绪信号）算法所需的全部输入字段。"""
    required = {
        "trade_date",
        "total_stocks",
        "rise_count",
        "fall_count",
        "flat_count",
        "strong_up_count",
        "strong_down_count",
        "limit_up_count",
        "limit_down_count",
        "touched_limit_up",
        "new_100d_high_count",
        "new_100d_low_count",
        "continuous_limit_up_2d",
        "continuous_limit_up_3d_plus",
        "continuous_new_high_2d_plus",
        "high_open_low_close_count",
        "low_open_high_close_count",
        "pct_chg_std",
        "amount_volatility",
        "yesterday_limit_up_today_avg_pct",
        "data_quality",
        "stale_days",
        "source_trade_date",
        "created_at",
    }
    assert required <= _field_names(MarketSnapshot)


def test_industry_snapshot_includes_irs_input_fields() -> None:
    """IndustrySnapshot 必须包含 IRS（行业轮动信号）算法所需的全部输入字段。"""
    required = {
        "trade_date",
        "industry_code",
        "industry_name",
        "stock_count",
        "rise_count",
        "fall_count",
        "flat_count",
        "industry_close",
        "industry_pct_chg",
        "industry_amount",
        "industry_turnover",
        "industry_pe_ttm",
        "industry_pb",
        "limit_up_count",
        "limit_down_count",
        "new_100d_high_count",
        "new_100d_low_count",
        "top5_codes",
        "top5_pct_chg",
        "top5_limit_up",
        "yesterday_limit_up_today_avg_pct",
        "data_quality",
        "stale_days",
        "source_trade_date",
        "created_at",
    }
    assert required <= _field_names(IndustrySnapshot)
