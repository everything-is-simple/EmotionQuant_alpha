"""数据层单元测试公共 fixture。

提供环境隔离能力，确保每个测试用例在干净的环境变量状态下运行，
避免本机 .env 配置污染测试结果。
"""
from __future__ import annotations

import pytest


# 需要在每个测试前清除的环境变量列表
# 涵盖：数据路径、DuckDB/Parquet 路径、TuShare 多通道配置、质量门控阈值等
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
def isolate_data_unit_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """自动清除与数据层相关的环境变量，实现测试环境隔离。"""
    for key in _ISOLATED_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
