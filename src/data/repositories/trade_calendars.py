from __future__ import annotations

from typing import Any

from src.data.fetcher import TuShareFetcher

from .base import BaseRepository


class TradeCalendarsRepository(BaseRepository):
    """Repository for raw_trade_cal."""

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
