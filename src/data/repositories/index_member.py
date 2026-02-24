"""raw_index_member 仓储：申万行业指数成分股映射。"""

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


class IndexMemberRepository(BaseRepository):
    """申万行业指数成分股仓储（raw_index_member）。

    按月快照，尝试多种参数组合回退拉取（SW2021 → 无 src → trade_date）。
    """

    table_name = "raw_index_member"

    def fetch(
        self,
        *,
        trade_date: str,
        fetcher: TuShareFetcher,
        snapshot_trade_date: str | None = None,
        **_: Any,
    ) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        candidates = (
            {"start_date": trade_date, "end_date": trade_date, "src": "SW2021"},
            {"start_date": trade_date, "end_date": trade_date},
            {"trade_date": trade_date},
        )
        for params in candidates:
            try:
                rows = fetcher.fetch_with_retry("index_member", params)
                return _attach_snapshot_trade_date(
                    rows,
                    snapshot_trade_date=snapshot_trade_date or trade_date,
                )
            except Exception as exc:  # pragma: no cover - compatibility fallback
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        return []

