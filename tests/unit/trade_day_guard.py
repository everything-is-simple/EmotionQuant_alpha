from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


CANARY_START_DATE = "20260102"
CANARY_END_DATE = "20260213"
CANARY_FILENAME = "a_share_open_trade_days_20260102_20260213.json"


def _canary_path() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "canary" / CANARY_FILENAME


@lru_cache(maxsize=1)
def load_canary_open_trade_days() -> tuple[str, ...]:
    path = _canary_path()
    payload = json.loads(path.read_text(encoding="utf-8"))
    days = [str(item) for item in payload.get("open_trade_days", []) if str(item).strip()]
    return tuple(sorted(days))


def latest_open_trade_days(count: int) -> list[str]:
    if count <= 0:
        raise ValueError(f"count must be > 0, got {count}")
    days = load_canary_open_trade_days()
    if len(days) < count:
        raise ValueError(
            f"insufficient canary trade days: require={count}, available={len(days)}"
        )
    return list(days[-count:])


def assert_all_valid_trade_days(trade_dates: list[str], *, context: str) -> None:
    valid_days = set(load_canary_open_trade_days())
    invalid = [str(item) for item in trade_dates if str(item) not in valid_days]
    if invalid:
        invalid_text = ",".join(invalid)
        raise AssertionError(
            f"invalid_trade_date_in_{context}:{invalid_text}; "
            f"canary_window={CANARY_START_DATE}-{CANARY_END_DATE}"
        )
