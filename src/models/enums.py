"""业务枚举统一定义（TD-DA-002）。

所有枚举均继承 ``str``，保证与现有字符串比较 / 序列化 / DataFrame 存储
完全向后兼容（``MssCycle.EMERGENCE == "emergence"`` 为 True）。

命名规范见 docs/naming-conventions.md §5。
"""

from __future__ import annotations

from enum import Enum


# ---------------------------------------------------------------------------
# 情绪周期（MSS）
# ---------------------------------------------------------------------------
class MssCycle(str, Enum):
    """情绪周期 8 态（含兜底）。"""
    EMERGENCE = "emergence"
    FERMENTATION = "fermentation"
    ACCELERATION = "acceleration"
    DIVERGENCE = "divergence"
    CLIMAX = "climax"
    DIFFUSION = "diffusion"
    RECESSION = "recession"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# 趋势方向
# ---------------------------------------------------------------------------
class Trend(str, Enum):
    """趋势方向：不使用 ``flat``。"""
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


# ---------------------------------------------------------------------------
# PAS 方向
# ---------------------------------------------------------------------------
class PasDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


# ---------------------------------------------------------------------------
# IRS 轮动状态
# ---------------------------------------------------------------------------
class RotationStatus(str, Enum):
    IN = "IN"
    OUT = "OUT"
    HOLD = "HOLD"


# ---------------------------------------------------------------------------
# IRS 轮动详情（中文枚举，与 irs-data-models.md §3.3 对齐）
# ---------------------------------------------------------------------------
class RotationDetail(str, Enum):
    STRONG_LEAD = "强势领涨"
    ACCELERATION = "轮动加速"
    TREND_REVERSAL = "趋势反转"
    HOTSPOT_SPREAD = "热点扩散"
    HIGH_CONSOLIDATION = "高位整固"
    STYLE_SWITCH = "风格转换"


# ---------------------------------------------------------------------------
# 推荐等级
# ---------------------------------------------------------------------------
class RecommendationGrade(str, Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    AVOID = "AVOID"


# ---------------------------------------------------------------------------
# Validation Gate 决策
# ---------------------------------------------------------------------------
class GateDecision(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
