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


class IndexDailyRepository(BaseRepository):
    """Repository for raw_index_daily."""

    table_name = "raw_index_daily"

    def fetch(
        self,
        *,
        trade_date: str,
        fetcher: TuShareFetcher,
        snapshot_trade_date: str | None = None,
        **_: Any,
    ) -> list[dict[str, Any]]:
        try:
            rows = fetcher.fetch_with_retry("index_daily", {"trade_date": trade_date})
        except Exception as exc:
            message = str(exc).lower()
            if "ts_code" not in message:
                raise
            rows = []
            # TuShare index_daily may require ts_code; fallback to core benchmark set.
            for ts_code in (
                "000001.SH",
                "399001.SZ",
                "399006.SZ",
                "000300.SH",
                "000905.SH",
                "000852.SH",
            ):
                rows.extend(
                    fetcher.fetch_with_retry(
                        "index_daily",
                        {"ts_code": ts_code, "trade_date": trade_date},
                    )
                )
        return _attach_snapshot_trade_date(
            rows,
            snapshot_trade_date=snapshot_trade_date or trade_date,
        )
