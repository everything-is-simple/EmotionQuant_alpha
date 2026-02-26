"""FilterConfig 契约测试。

验证：
- FilterConfig 默认值与 gui-data-models.md §4.2 一致。
- build_filter_preset_badges 按页面名生成正确的阈值徽标。
- FilterConfig 可修改（非 frozen），支持 user override。
"""

from __future__ import annotations

from src.gui.formatter import build_filter_preset_badges
from src.gui.models import FilterConfig


def test_filter_config_default_values() -> None:
    """默认值与设计文档 §4.2 一致。"""
    fc = FilterConfig()
    assert fc.dashboard_min_score == 60.0
    assert fc.irs_max_rank == 10
    assert fc.irs_rotation_status == ["IN"]
    assert fc.pas_min_score == 60.0
    assert fc.pas_min_level == "B"
    assert fc.integrated_min_score == 70.0
    assert fc.integrated_min_position == 0.05
    assert fc.source == "env_default"


def test_filter_config_mutable() -> None:
    """FilterConfig 可修改（用户覆盖）。"""
    fc = FilterConfig()
    fc.integrated_min_score = 80.0
    fc.source = "user_override"
    assert fc.integrated_min_score == 80.0
    assert fc.source == "user_override"


def test_badges_dashboard() -> None:
    """Dashboard 页面生成正确的阈值徽标。"""
    fc = FilterConfig()
    badges = build_filter_preset_badges("dashboard", fc)
    assert badges == ["final_score >= 60.0"]


def test_badges_integrated() -> None:
    """Integrated 页面生成 score + position 两个徽标。"""
    fc = FilterConfig()
    badges = build_filter_preset_badges("integrated", fc)
    assert len(badges) == 2
    assert "final_score >= 70.0" in badges[0]
    assert "position_size >= 0.05" in badges[1]


def test_badges_pas() -> None:
    """PAS 页面生成 score + grade 两个徽标。"""
    fc = FilterConfig()
    badges = build_filter_preset_badges("pas", fc)
    assert len(badges) == 2
    assert "opportunity_score" in badges[0]
    assert "opportunity_grade" in badges[1]


def test_badges_irs() -> None:
    """IRS 页面生成 rank + rotation_status 两个徽标。"""
    fc = FilterConfig()
    badges = build_filter_preset_badges("irs", fc)
    assert len(badges) == 2
    assert "rank" in badges[0]
    assert "rotation_status" in badges[1]


def test_badges_unknown_page() -> None:
    """未知页面返回空列表。"""
    fc = FilterConfig()
    badges = build_filter_preset_badges("unknown", fc)
    assert badges == []


def test_badges_non_filter_config() -> None:
    """非 FilterConfig 对象返回空列表。"""
    badges = build_filter_preset_badges("dashboard", {"not": "a filter"})
    assert badges == []
