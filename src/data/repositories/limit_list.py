"""raw_limit_list 仓储：涨跌停列表。"""

from __future__ import annotations

from typing import Any

from src.data.fetcher import TuShareFetcher

from .base import BaseRepository


class LimitListRepository(BaseRepository):
    """涨跌停列表仓储（raw_limit_list），按 trade_date 拉取。"""

    table_name = "raw_limit_list"

    def fetch(
        self,
        *,
        trade_date: str,
        fetcher: TuShareFetcher,
        **_: Any,
    ) -> list[dict[str, Any]]:
        return fetcher.fetch_with_retry("limit_list", {"trade_date": trade_date})
