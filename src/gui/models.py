"""GUI 数据模型（只读展示层）。

与 docs/design/core-infrastructure/gui/gui-data-models.md v3.2.0 对齐。
所有 dataclass 仅承载展示数据，不执行任何算法计算。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

# DESIGN_TRACE:
# - docs/design/core-infrastructure/gui/gui-data-models.md (v3.2.0)
# - Governance/SpiralRoadmap/execution-cards/S5-EXECUTION-CARD.md (§3 模块级补齐任务)
DESIGN_TRACE = {
    "gui_data_models": "docs/design/core-infrastructure/gui/gui-data-models.md",
    "s5_execution_card": "Governance/SpiralRoadmap/execution-cards/S5-EXECUTION-CARD.md",
}


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------

class FreshnessLevel(Enum):
    """缓存新鲜度等级。"""

    FRESH = "fresh"
    STALE_SOON = "stale_soon"
    STALE = "stale"


class TemperatureLevel(Enum):
    """温度等级。"""

    HIGH = "high"       # > 80
    MEDIUM = "medium"   # 45-80
    COOL = "cool"       # 30-44
    LOW = "low"         # < 30


class RecommendationLevel(Enum):
    """推荐等级。"""

    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    AVOID = "AVOID"


class OpportunityLevel(Enum):
    """机会等级。"""

    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class RotationStatus(Enum):
    """轮动状态。"""

    IN = "IN"
    OUT = "OUT"
    HOLD = "HOLD"


# ---------------------------------------------------------------------------
# 组件数据
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FreshnessMeta:
    """缓存新鲜度元信息。"""

    data_asof: str
    cache_created_at: str
    cache_age_sec: int
    freshness_level: str  # fresh / stale_soon / stale


@dataclass
class FilterConfig:
    """默认过滤配置（可持久化 + 回显）。"""

    dashboard_min_score: float = 60.0
    irs_max_rank: int = 10
    irs_rotation_status: List[str] = field(default_factory=lambda: ["IN"])
    pas_min_score: float = 60.0
    pas_min_level: str = "B"
    integrated_min_score: float = 70.0
    integrated_min_position: float = 0.05
    source: str = "env_default"


@dataclass(frozen=True)
class PaginationInfo:
    """分页信息。"""

    current_page: int
    page_size: int
    total_items: int
    total_pages: int
    has_prev: bool
    has_next: bool


@dataclass(frozen=True)
class TemperatureCardData:
    """温度卡片数据。"""

    value: float
    color: str   # red / orange / cyan / blue
    label: str   # 过热 / 中性 / 冷却 / 冰点
    trend: str


@dataclass(frozen=True)
class CycleBadgeData:
    """周期标签数据。"""

    cycle: str
    label: str   # 中文
    color: str


# ---------------------------------------------------------------------------
# 推荐 / 行业 / 个股
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RecommendationItem:
    """集成推荐展示项。"""

    rank: int
    stock_code: str
    stock_name: str
    industry_name: str
    final_score: float
    recommendation: str
    recommendation_color: str
    integration_mode: str
    integration_mode_badge: str
    position_size: float
    direction: str
    entry: float
    stop: float
    target: float
    irs_score: float
    pas_score: float


@dataclass(frozen=True)
class IndustryRankItem:
    """行业排名展示项。"""

    rank: int
    industry_code: str
    industry_name: str
    industry_score: float
    rotation_status: str
    status_color: str
    allocation_advice: str


@dataclass(frozen=True)
class StockPasDisplay:
    """个股 PAS 展示数据。"""

    stock_code: str
    stock_name: str
    industry_name: str
    opportunity_score: float
    opportunity_grade: str
    level_color: str
    direction: str
    direction_icon: str
    neutrality: float
    neutrality_percent: int
    risk_reward_ratio: float
    suggested_entry: float
    suggested_stop: float
    suggested_target: float


# ---------------------------------------------------------------------------
# MSS
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MssPanoramaDisplay:
    """MSS 展示数据。"""

    trade_date: str
    temperature: float
    temperature_color: str
    cycle: str
    cycle_label: str
    trend: str
    trend_icon: str
    position_advice: str


@dataclass(frozen=True)
class TemperatureChartData:
    """温度曲线图表数据。"""

    x_axis: List[str]
    y_axis: List[float]


@dataclass(frozen=True)
class MssPageData:
    """MSS 页面数据。"""

    current: Optional[MssPanoramaDisplay]
    history: List[MssPanoramaDisplay]
    chart_data: TemperatureChartData


# ---------------------------------------------------------------------------
# IRS
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IndustryChartData:
    """行业排名柱状图数据。"""

    x_axis: List[str]
    y_axis: List[float]
    colors: List[str]


@dataclass(frozen=True)
class IrsPageData:
    """IRS 页面数据。"""

    trade_date: str
    industries: List[IndustryRankItem]
    chart_data: IndustryChartData


# ---------------------------------------------------------------------------
# PAS
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PasPageData:
    """PAS 页面数据。"""

    trade_date: str
    stocks: List[StockPasDisplay]
    pagination: PaginationInfo


# ---------------------------------------------------------------------------
# Integrated
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntegratedPageData:
    """集成推荐页面数据。"""

    trade_date: str
    recommendations: List[RecommendationItem]
    pagination: PaginationInfo
    data_asof: str
    freshness: FreshnessMeta
    active_filter_badges: List[str]


# ---------------------------------------------------------------------------
# Trading
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PositionDisplay:
    """持仓展示数据。"""

    stock_code: str
    stock_name: str
    shares: int
    cost_price: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    pnl_color: str  # red (盈利) / green (亏损) / gray (持平) — A 股红涨绿跌
    is_frozen: bool
    frozen_label: str
    stop_price: float
    target_price: float


@dataclass(frozen=True)
class TradeRecordDisplay:
    """交易记录展示数据。"""

    trade_id: str
    trade_date: str
    stock_code: str
    stock_name: str
    direction: str
    direction_label: str
    direction_color: str  # red (买入) / green (卖出) — A 股红涨绿跌
    price: float
    shares: int
    amount: float
    total_fee: float
    status: str
    status_label: str


@dataclass(frozen=True)
class TradingPageData:
    """交易页面数据。"""

    trade_date: str
    positions: List[PositionDisplay]
    total_market_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    trades: List[TradeRecordDisplay]
    pagination: PaginationInfo


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PerformanceMetricsDisplay:
    """绩效指标展示数据。"""

    total_return: float
    total_return_pct: str
    annual_return: float
    annual_return_pct: str
    max_drawdown: float
    max_drawdown_pct: str
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate: float
    win_rate_pct: str
    profit_factor: float


@dataclass(frozen=True)
class BacktestSummaryDisplay:
    """回测结果摘要展示。"""

    backtest_name: str
    start_date: str
    end_date: str
    total_return_pct: str
    annual_return_pct: str
    max_drawdown_pct: str
    sharpe_ratio: float
    total_trades: int
    win_rate_pct: str


@dataclass(frozen=True)
class AnalysisPageData:
    """分析页面数据。"""

    report_date: str
    metrics: PerformanceMetricsDisplay
    daily_report: str
    backtest_summary: BacktestSummaryDisplay


# ---------------------------------------------------------------------------
# Dashboard (总览)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DashboardData:
    """总览仪表盘数据。"""

    temperature: float
    temperature_color: str
    cycle: str
    trend: str
    position_advice: str
    trade_date: str
    data_asof: str
    freshness: FreshnessMeta
    active_filter_badges: List[str]
    top_recommendations: List[RecommendationItem]
    integration_mode_badge: str
    top_industries: List[IndustryRankItem]
