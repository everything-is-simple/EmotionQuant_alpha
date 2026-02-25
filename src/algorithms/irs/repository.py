"""IRS Repository 接口抽象（TD-DA-001 跟进）。

将数据访问逻辑从编排中解耦，便于测试替换（如内存桩）与后续推广。

DESIGN_TRACE:
- docs/design/core-algorithms/irs/irs-data-models.md
- Governance/SpiralRoadmap/execution-cards/DEBT-CARD-B-CONTRACT.md (§2 TD-DA-001)
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import duckdb
import pandas as pd

from src.db.helpers import (
    persist_by_trade_date,
    table_exists,
)

DESIGN_TRACE = {
    "irs_data_models": "docs/design/core-algorithms/irs/irs-data-models.md",
    "debt_card_b": "Governance/SpiralRoadmap/execution-cards/DEBT-CARD-B-CONTRACT.md",
}


@runtime_checkable
class IrsRepository(Protocol):
    """IRS 数据访问接口协议。"""

    def load_industry_snapshot(self, trade_date: str) -> pd.DataFrame:
        """从 L2 industry_snapshot 加载指定日期所有行业快照。"""
        ...

    def load_industry_history(self, trade_date: str) -> pd.DataFrame:
        """加载 trade_date 及之前的行业快照历史（用于因子计算）。"""
        ...

    def load_irs_history(self, trade_date: str) -> pd.DataFrame:
        """加载 trade_date 之前的 IRS 评分历史（用于轮动状态计算）。"""
        ...

    def save_daily(self, frame: pd.DataFrame, trade_date: str) -> int:
        """将评分结果写入 irs_industry_daily 表，返回写入行数。"""
        ...

    def save_factor_intermediate(self, frame: pd.DataFrame, trade_date: str) -> int:
        """将因子中间表写入 irs_factor_intermediate 表，返回写入行数。"""
        ...


class DuckDbIrsRepository:
    """基于 DuckDB 的 IRS 数据访问实现。"""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def load_industry_snapshot(self, trade_date: str) -> pd.DataFrame:
        with duckdb.connect(str(self._database_path), read_only=True) as conn:
            if not table_exists(conn, "industry_snapshot"):
                raise ValueError("industry_snapshot_table_missing")
            return conn.execute(
                "SELECT * FROM industry_snapshot WHERE trade_date = ?",
                [trade_date],
            ).df()

    def load_industry_history(self, trade_date: str) -> pd.DataFrame:
        with duckdb.connect(str(self._database_path), read_only=True) as conn:
            if not table_exists(conn, "industry_snapshot"):
                return pd.DataFrame()
            return conn.execute(
                "SELECT * FROM industry_snapshot WHERE trade_date <= ? "
                "ORDER BY trade_date, industry_code",
                [trade_date],
            ).df()

    def load_irs_history(self, trade_date: str) -> pd.DataFrame:
        with duckdb.connect(str(self._database_path), read_only=True) as conn:
            if not table_exists(conn, "irs_industry_daily"):
                return pd.DataFrame()
            return conn.execute(
                "SELECT trade_date, industry_code, industry_score, irs_score "
                "FROM irs_industry_daily WHERE trade_date < ? ORDER BY trade_date",
                [trade_date],
            ).df()

    def save_daily(self, frame: pd.DataFrame, trade_date: str) -> int:
        return persist_by_trade_date(
            database_path=self._database_path,
            table_name="irs_industry_daily",
            frame=frame,
            trade_date=trade_date,
        )

    def save_factor_intermediate(self, frame: pd.DataFrame, trade_date: str) -> int:
        return persist_by_trade_date(
            database_path=self._database_path,
            table_name="irs_factor_intermediate",
            frame=frame,
            trade_date=trade_date,
        )
