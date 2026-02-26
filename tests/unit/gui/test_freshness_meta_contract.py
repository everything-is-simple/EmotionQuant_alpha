"""FreshnessMeta 契约测试。

验证：
- FreshnessMeta dataclass 包含 data_asof / cache_created_at / cache_age_sec / freshness_level。
- _build_freshness 按 TTL 阈值正确分级：fresh / stale_soon / stale。
- FreshnessLevel 枚举包含三级。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src.gui.data_service import _build_freshness
from src.gui.models import FreshnessLevel, FreshnessMeta


def test_freshness_meta_fields() -> None:
    """FreshnessMeta 必须包含 4 个字段。"""
    meta = FreshnessMeta(
        data_asof="2026-01-01T00:00:00+00:00",
        cache_created_at="2026-01-01T00:00:01+00:00",
        cache_age_sec=1,
        freshness_level="fresh",
    )
    assert meta.data_asof == "2026-01-01T00:00:00+00:00"
    assert meta.cache_created_at == "2026-01-01T00:00:01+00:00"
    assert meta.cache_age_sec == 1
    assert meta.freshness_level == "fresh"


def test_freshness_level_enum_values() -> None:
    """FreshnessLevel 枚举包含 fresh / stale_soon / stale。"""
    assert FreshnessLevel.FRESH.value == "fresh"
    assert FreshnessLevel.STALE_SOON.value == "stale_soon"
    assert FreshnessLevel.STALE.value == "stale"


def test_build_freshness_fresh() -> None:
    """数据年龄 <= 50% TTL 时为 fresh。"""
    now = datetime(2026, 2, 26, 12, 0, 0, tzinfo=timezone.utc)
    # data_asof = 2 小时前 → age=7200s，l3_daily TTL=86400s，50%=43200s → fresh
    data_asof = (now - timedelta(hours=2)).isoformat()
    with patch("src.gui.data_service._utc_now", return_value=now):
        meta = _build_freshness(data_asof, "l3_daily")
    assert meta.freshness_level == "fresh"
    assert meta.cache_age_sec == 7200


def test_build_freshness_stale_soon() -> None:
    """数据年龄 50%-100% TTL 时为 stale_soon。"""
    now = datetime(2026, 2, 26, 12, 0, 0, tzinfo=timezone.utc)
    # data_asof = 18 小时前 → age=64800s，l3_daily TTL=86400s，>43200 <86400 → stale_soon
    data_asof = (now - timedelta(hours=18)).isoformat()
    with patch("src.gui.data_service._utc_now", return_value=now):
        meta = _build_freshness(data_asof, "l3_daily")
    assert meta.freshness_level == "stale_soon"


def test_build_freshness_stale() -> None:
    """数据年龄 > TTL 时为 stale。"""
    now = datetime(2026, 2, 26, 12, 0, 0, tzinfo=timezone.utc)
    # data_asof = 30 小时前 → age=108000s，>86400 → stale
    data_asof = (now - timedelta(hours=30)).isoformat()
    with patch("src.gui.data_service._utc_now", return_value=now):
        meta = _build_freshness(data_asof, "l3_daily")
    assert meta.freshness_level == "stale"


def test_build_freshness_invalid_asof() -> None:
    """无效 data_asof 应归为 stale。"""
    meta = _build_freshness("invalid-timestamp", "l3_daily")
    assert meta.freshness_level == "stale"
    assert meta.cache_age_sec == 999999
