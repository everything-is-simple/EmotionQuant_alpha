"""pnl_color 契约测试（A 股红涨绿跌）。

验证：
- 盈利（>0）→ red
- 亏损（<0）→ green
- 持平（=0）→ gray
- direction_color: buy → red, sell → green
- format_trend: up → (↑, red), down → (↓, green), sideways → (→, gray)
"""

from __future__ import annotations

from src.gui.formatter import (
    direction_color,
    direction_label,
    format_trend,
    pnl_color,
    recommendation_color,
    rotation_status_color,
    opportunity_level_color,
)


# ---------------------------------------------------------------------------
# pnl_color: A 股红涨绿跌
# ---------------------------------------------------------------------------

def test_pnl_color_profit() -> None:
    """盈利 → red。"""
    assert pnl_color(100.0) == "red"
    assert pnl_color(0.01) == "red"


def test_pnl_color_loss() -> None:
    """亏损 → green。"""
    assert pnl_color(-100.0) == "green"
    assert pnl_color(-0.01) == "green"


def test_pnl_color_flat() -> None:
    """持平 → gray。"""
    assert pnl_color(0.0) == "gray"


# ---------------------------------------------------------------------------
# direction_color / direction_label
# ---------------------------------------------------------------------------

def test_direction_color_buy() -> None:
    """买入 → red（A 股红涨绿跌）。"""
    assert direction_color("buy") == "red"


def test_direction_color_sell() -> None:
    """卖出 → green。"""
    assert direction_color("sell") == "green"


def test_direction_label_chinese() -> None:
    """buy → 买入, sell → 卖出。"""
    assert direction_label("buy") == "买入"
    assert direction_label("sell") == "卖出"


# ---------------------------------------------------------------------------
# format_trend
# ---------------------------------------------------------------------------

def test_format_trend_up() -> None:
    """up → (↑, red)。"""
    icon, color = format_trend("up")
    assert icon == "↑"
    assert color == "red"


def test_format_trend_down() -> None:
    """down → (↓, green)。"""
    icon, color = format_trend("down")
    assert icon == "↓"
    assert color == "green"


def test_format_trend_sideways() -> None:
    """sideways → (→, gray)。"""
    icon, color = format_trend("sideways")
    assert icon == "→"
    assert color == "gray"


# ---------------------------------------------------------------------------
# recommendation_color
# ---------------------------------------------------------------------------

def test_recommendation_color_strong_buy() -> None:
    assert recommendation_color("STRONG_BUY") == "red"


def test_recommendation_color_buy() -> None:
    assert recommendation_color("BUY") == "red"


def test_recommendation_color_hold() -> None:
    assert recommendation_color("HOLD") == "orange"


def test_recommendation_color_sell() -> None:
    assert recommendation_color("SELL") == "gray"


def test_recommendation_color_avoid() -> None:
    assert recommendation_color("AVOID") == "gray"


# ---------------------------------------------------------------------------
# rotation_status_color / opportunity_level_color
# ---------------------------------------------------------------------------

def test_rotation_status_color() -> None:
    assert rotation_status_color("IN") == "green"
    assert rotation_status_color("HOLD") == "orange"
    assert rotation_status_color("OUT") == "gray"


def test_opportunity_level_color() -> None:
    assert opportunity_level_color("S") == "gold"
    assert opportunity_level_color("A") == "green"
    assert opportunity_level_color("B") == "blue"
    assert opportunity_level_color("C") == "gray"
    assert opportunity_level_color("D") == "red"
