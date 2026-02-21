from __future__ import annotations

import pytest


_ISOLATED_ENV_KEYS = (
    "DATA_PATH",
    "DUCKDB_DIR",
    "PARQUET_PATH",
    "CACHE_PATH",
    "LOG_PATH",
    "ENVIRONMENT",
    "TUSHARE_TOKEN",
    "TUSHARE_SDK_PROVIDER",
    "TUSHARE_HTTP_URL",
    "TUSHARE_PRIMARY_TOKEN",
    "TUSHARE_PRIMARY_SDK_PROVIDER",
    "TUSHARE_PRIMARY_HTTP_URL",
    "TUSHARE_FALLBACK_TOKEN",
    "TUSHARE_FALLBACK_SDK_PROVIDER",
    "TUSHARE_FALLBACK_HTTP_URL",
    "TUSHARE_RATE_LIMIT_PER_MIN",
    "TUSHARE_PRIMARY_RATE_LIMIT_PER_MIN",
    "TUSHARE_FALLBACK_RATE_LIMIT_PER_MIN",
    "FLAT_THRESHOLD",
    "MIN_COVERAGE_RATIO",
    "STALE_HARD_LIMIT_DAYS",
    "ENABLE_INTRADAY_INCREMENTAL",
)


@pytest.fixture(autouse=True)
def isolate_unit_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ISOLATED_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
