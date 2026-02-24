"""raw_daily_basic 仓储：股票每日指标（换手率 / PE / PB / 总市值）。"""

from __future__ import annotations

from typing import Any

from src.data.fetcher import TuShareFetcher

from .base import BaseRepository


def _attach_snapshot_trade_date(
    rows: list[dict[str, Any]],
    *,
    snapshot_trade_date: str,
) -> list[dict[str, Any]]:
    if not snapshot_trade_date:
        return rows
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if not str(item.get("trade_date", "")).strip():
            item["trade_date"] = snapshot_trade_date
        normalized.append(item)
    return normalized


class DailyBasicRepository(BaseRepository):
    """股票每日指标仓储（raw_daily_basic），按 trade_date 拉取。"""

    table_name = "raw_daily_basic"

    def fetch(
        self,
        *,
        trade_date: str,
        fetcher: TuShareFetcher,
        snapshot_trade_date: str | None = None,
        **_: Any,
    ) -> list[dict[str, Any]]:
        rows = fetcher.fetch_with_retry("daily_basic", {"trade_date": trade_date})
        return _attach_snapshot_trade_date(
            rows,
            snapshot_trade_date=snapshot_trade_date or trade_date,
        )

