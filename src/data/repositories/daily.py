from __future__ import annotations

from typing import Any

from src.data.fetcher import TuShareFetcher

from .base import BaseRepository


class DailyRepository(BaseRepository):
    """Repository for raw_daily."""

    table_name = "raw_daily"

    def fetch(
        self,
        *,
        trade_date: str,
        fetcher: TuShareFetcher,
        **_: Any,
    ) -> list[dict[str, Any]]:
        return fetcher.fetch_with_retry("daily", {"trade_date": trade_date})
