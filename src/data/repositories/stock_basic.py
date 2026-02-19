from __future__ import annotations

from typing import Any

from src.data.fetcher import TuShareFetcher

from .base import BaseRepository


class StockBasicRepository(BaseRepository):
    """Repository for raw_stock_basic."""

    table_name = "raw_stock_basic"

    def fetch(
        self,
        *,
        trade_date: str,
        fetcher: TuShareFetcher,
        snapshot_trade_date: str | None = None,
        **_: Any,
    ) -> list[dict[str, Any]]:
        normalized_rows: list[dict[str, Any]] = []
        seen_codes: set[str] = set()
        snapshot = snapshot_trade_date or trade_date
        status_candidates = ("L", "D", "P")
        has_success = False

        for list_status in status_candidates:
            try:
                rows = fetcher.fetch_with_retry("stock_basic", {"list_status": list_status})
            except Exception:  # pragma: no cover - compatibility fallback
                continue
            has_success = True
            for row in rows:
                item = dict(row)
                if not str(item.get("trade_date", "")).strip():
                    item["trade_date"] = snapshot
                if not str(item.get("list_status", "")).strip():
                    item["list_status"] = list_status
                code = str(item.get("ts_code", "")).strip() or str(item.get("stock_code", "")).strip()
                if code and code in seen_codes:
                    continue
                if code:
                    seen_codes.add(code)
                normalized_rows.append(item)

        if has_success:
            return normalized_rows

        rows = fetcher.fetch_with_retry("stock_basic", {})
        fallback_rows: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            if not str(item.get("trade_date", "")).strip():
                item["trade_date"] = snapshot
            fallback_rows.append(item)
        return fallback_rows
