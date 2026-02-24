"""快照模型序列化与契约校验测试。

验证 MarketSnapshot / IndustrySnapshot 的 to_storage_record() 输出格式，
以及数据质量契约（normal 状态下 stale_days 必须为 0）的强制校验。
"""
from __future__ import annotations

import json
import pytest

from src.data.models.snapshots import IndustrySnapshot, MarketSnapshot


def test_market_snapshot_serializes_created_at() -> None:
    """MarketSnapshot 序列化后应包含 created_at 时间戳和默认质量字段。"""
    snapshot = MarketSnapshot(trade_date="20260207")
    record = snapshot.to_storage_record()
    assert record["trade_date"] == "20260207"
    assert record["data_quality"] == "normal"
    assert record["stale_days"] == 0
    assert record["source_trade_date"] == "20260207"
    assert isinstance(record["created_at"], str)


def test_industry_snapshot_serializes_top5_fields_as_json() -> None:
    """IndustrySnapshot 的 top5 字段（行业前5股票/涨幅）应序列化为 JSON 字符串。"""
    snapshot = IndustrySnapshot(
        trade_date="20260207",
        industry_code="801750",
        top5_codes=["000001", "000002"],
        top5_pct_chg=[1.2, 3.4],
    )
    record = snapshot.to_storage_record()
    assert record["top5_codes"] == json.dumps(["000001", "000002"], ensure_ascii=False)
    assert record["top5_pct_chg"] == json.dumps([1.2, 3.4], ensure_ascii=False)
    assert record["data_quality"] == "normal"
    assert record["stale_days"] == 0
    assert record["source_trade_date"] == "20260207"


def test_snapshot_rejects_invalid_quality_contract() -> None:
    """normal 质量状态下 stale_days != 0 应触发 ValueError（契约强制校验）。"""
    with pytest.raises(ValueError, match="normal data must have stale_days == 0"):
        MarketSnapshot(
            trade_date="20260207",
            data_quality="normal",
            stale_days=1,
            source_trade_date="20260206",
        )
