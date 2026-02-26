"""GUI 格式化工具。

与 docs/design/core-infrastructure/gui/gui-algorithm.md v3.2.0 §2/§4 对齐。
实现温度分级、周期标签、趋势图标、盈亏颜色（A 股红涨绿跌）等只读展示转换。
"""

from __future__ import annotations

from src.gui.models import CycleBadgeData, TemperatureCardData

# DESIGN_TRACE:
# - docs/design/core-infrastructure/gui/gui-algorithm.md (§2 温度颜色分级, §4 过滤阈值可视化)
# - docs/design/core-infrastructure/gui/gui-data-models.md (§3.2 CycleBadge, §5.2 pnl_color)
DESIGN_TRACE = {
    "gui_algorithm": "docs/design/core-infrastructure/gui/gui-algorithm.md",
    "gui_data_models": "docs/design/core-infrastructure/gui/gui-data-models.md",
}


# ---------------------------------------------------------------------------
# 温度 → 颜色 / 标签
# ---------------------------------------------------------------------------

def format_temperature(temperature: float, trend: str = "") -> TemperatureCardData:
    """温度分级：>80 red/过热, 45-80 orange/中性, 30-44 cyan/冷却, <30 blue/冰点。"""
    if temperature > 80:
        color, label = "red", "过热"
    elif temperature >= 45:
        color, label = "orange", "中性"
    elif temperature >= 30:
        color, label = "cyan", "冷却"
    else:
        color, label = "blue", "冰点"
    return TemperatureCardData(value=temperature, color=color, label=label, trend=trend)


def temperature_color(temperature: float) -> str:
    """仅返回颜色字符串。"""
    if temperature > 80:
        return "red"
    if temperature >= 45:
        return "orange"
    if temperature >= 30:
        return "cyan"
    return "blue"


# ---------------------------------------------------------------------------
# 周期 → 中文标签 / 颜色
# ---------------------------------------------------------------------------

CYCLE_MAP: dict[str, tuple[str, str]] = {
    "emergence": ("萌芽期", "blue"),
    "fermentation": ("发酵期", "cyan"),
    "acceleration": ("加速期", "green"),
    "divergence": ("分歧期", "yellow"),
    "climax": ("高潮期", "orange"),
    "diffusion": ("扩散期", "purple"),
    "recession": ("退潮期", "gray"),
    "unknown": ("未知", "slate"),
}


def format_cycle(cycle: str) -> CycleBadgeData:
    """周期英文 → 中文标签 + 颜色。"""
    label, color = CYCLE_MAP.get(cycle, ("未知", "slate"))
    return CycleBadgeData(cycle=cycle, label=label, color=color)


def cycle_label(cycle: str) -> str:
    """仅返回中文标签。"""
    return CYCLE_MAP.get(cycle, ("未知", "slate"))[0]


# ---------------------------------------------------------------------------
# 趋势 → 图标 / 颜色
# ---------------------------------------------------------------------------

def format_trend(trend: str) -> tuple[str, str]:
    """趋势 → (图标, 颜色)，A 股红涨绿跌。"""
    if trend == "up":
        return ("↑", "red")
    if trend == "down":
        return ("↓", "green")
    return ("→", "gray")


def trend_icon(trend: str) -> str:
    """仅返回图标。"""
    return format_trend(trend)[0]


# ---------------------------------------------------------------------------
# 盈亏颜色 — A 股红涨绿跌
# ---------------------------------------------------------------------------

def pnl_color(value: float) -> str:
    """盈亏颜色：>0 red（盈利），<0 green（亏损），=0 gray（持平）。"""
    if value > 0:
        return "red"
    if value < 0:
        return "green"
    return "gray"


# ---------------------------------------------------------------------------
# 方向标签 / 颜色
# ---------------------------------------------------------------------------

def direction_label(direction: str) -> str:
    """buy → 买入, sell → 卖出。"""
    return {"buy": "买入", "sell": "卖出"}.get(direction, direction)


def direction_color(direction: str) -> str:
    """A 股：买入红色, 卖出绿色。"""
    return {"buy": "red", "sell": "green"}.get(direction, "gray")


# ---------------------------------------------------------------------------
# 百分比格式化
# ---------------------------------------------------------------------------

def format_percent(value: float, *, with_sign: bool = False) -> str:
    """小数 → 百分比字符串。0.152 → '15.2%'，with_sign=True → '+15.2%'。"""
    pct = value * 100.0
    if with_sign:
        return f"{pct:+.1f}%"
    return f"{pct:.1f}%"


# ---------------------------------------------------------------------------
# 轮动状态 → 颜色
# ---------------------------------------------------------------------------

def rotation_status_color(status: str) -> str:
    """IN → green, HOLD → orange, OUT → gray。"""
    return {"IN": "green", "HOLD": "orange", "OUT": "gray"}.get(status, "gray")


# ---------------------------------------------------------------------------
# 机会等级 → 颜色
# ---------------------------------------------------------------------------

def opportunity_level_color(grade: str) -> str:
    """S → gold, A → green, B → blue, C → gray, D → red。"""
    return {"S": "gold", "A": "green", "B": "blue", "C": "gray", "D": "red"}.get(grade, "gray")


# ---------------------------------------------------------------------------
# 推荐等级颜色
# ---------------------------------------------------------------------------

def recommendation_color(level: str) -> str:
    """STRONG_BUY/BUY → red, HOLD → orange, SELL/AVOID → gray。"""
    if level in ("STRONG_BUY", "BUY"):
        return "red"
    if level == "HOLD":
        return "orange"
    return "gray"


# ---------------------------------------------------------------------------
# 集成模式 → 中文徽标
# ---------------------------------------------------------------------------

INTEGRATION_MODE_BADGE: dict[str, str] = {
    "top_down": "传统模式",
    "bottom_up": "实验模式",
    "dual_verify": "双重验证",
    "complementary": "互补模式",
}


def integration_mode_badge(mode: str) -> str:
    """集成模式英文 → 中文徽标。"""
    return INTEGRATION_MODE_BADGE.get(mode, mode)


# ---------------------------------------------------------------------------
# 过滤阈值徽标
# ---------------------------------------------------------------------------

def build_filter_preset_badges(page_name: str, config: object) -> list[str]:
    """构建页面头部阈值徽标列表。"""
    from src.gui.models import FilterConfig

    if not isinstance(config, FilterConfig):
        return []
    if page_name == "dashboard":
        return [f"final_score >= {config.dashboard_min_score}"]
    if page_name == "integrated":
        return [
            f"final_score >= {config.integrated_min_score}",
            f"position_size >= {config.integrated_min_position:.2f}",
        ]
    if page_name == "pas":
        return [
            f"opportunity_score >= {config.pas_min_score}",
            f"opportunity_grade >= {config.pas_min_level}",
        ]
    if page_name == "irs":
        return [
            f"rank <= {config.irs_max_rank}",
            f"rotation_status in {config.irs_rotation_status}",
        ]
    return []


# ---------------------------------------------------------------------------
# 状态标签
# ---------------------------------------------------------------------------

STATUS_LABEL: dict[str, str] = {
    "filled": "已成交",
    "partial": "部分成交",
    "cancelled": "已取消",
}


def status_label(status: str) -> str:
    """交易状态 → 中文。"""
    return STATUS_LABEL.get(status, status)
