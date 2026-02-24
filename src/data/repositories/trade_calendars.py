"""raw_trade_cal 仓储：交易日历。"""

from __future__ import annotations

from typing import Any

from src.data.fetcher import TuShareFetcher

from .base import BaseRepository


class TradeCalendarsRepository(BaseRepository):
    """交易日历仓储（raw_trade_cal），按单日拉取。"""

    table_name = "raw_trade_cal"

    def fetch(
        self,
        *,
        trade_date: str,
        fetcher: TuShareFetcher,
        **_: Any,
    ) -> list[dict[str, Any]]:
        return fetcher.fetch_with_retry(
            "trade_cal",
            {"start_date": trade_date, "end_date": trade_date},
        )
