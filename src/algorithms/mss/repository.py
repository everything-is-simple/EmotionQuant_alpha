"""MSS Repository 接口抽象（TD-DA-001 试点）。

将数据访问逻辑从编排中解耦，便于测试替换（如内存桩）与后续全模块推广。

DESIGN_TRACE:
- docs/design/core-algorithms/mss/mss-data-models.md
- Governance/SpiralRoadmap/execution-cards/DEBT-CARD-B-CONTRACT.md (§2 TD-DA-001)
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import duckdb
import pandas as pd

from src.algorithms.mss.engine import MssInputSnapshot, MssPanorama
from src.db.helpers import (
    column_exists,
    ensure_columns,
    table_exists,
)

DESIGN_TRACE = {
    "mss_data_models": "docs/design/core-algorithms/mss/mss-data-models.md",
    "debt_card_b": "Governance/SpiralRoadmap/execution-cards/DEBT-CARD-B-CONTRACT.md",
}


@runtime_checkable
class MssRepository(Protocol):
    """MSS 数据访问接口协议。"""

    def load_snapshot(self, trade_date: str) -> MssInputSnapshot:
        """从 L2 market_snapshot 加载指定日期快照。"""
        ...

    def load_temperature_history(
        self,
        trade_date: str,
        *,
        limit: int = 252,
    ) -> list[float]:
        """加载 trade_date 之前的历史温度序列（升序）。"""
        ...

    def save_panorama(self, panorama: MssPanorama, trade_date: str) -> int:
        """将 MssPanorama 写入 mss_panorama 表，返回写入行数。"""
        ...


class DuckDbMssRepository:
    """基于 DuckDB 的 MSS 数据访问实现。"""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def load_snapshot(self, trade_date: str) -> MssInputSnapshot:
        with duckdb.connect(str(self._database_path), read_only=True) as conn:
            if not table_exists(conn, "market_snapshot"):
                raise ValueError("market_snapshot_table_missing")
            frame = conn.execute(
                "SELECT * FROM market_snapshot WHERE trade_date = ? "
                "ORDER BY created_at DESC LIMIT 1",
                [trade_date],
            ).df()
            if frame.empty:
                raise ValueError("market_snapshot_not_found")
            return MssInputSnapshot.from_record(frame.iloc[0].to_dict())

    def load_temperature_history(
        self,
        trade_date: str,
        *,
        limit: int = 252,
    ) -> list[float]:
        with duckdb.connect(str(self._database_path), read_only=True) as conn:
            if not table_exists(conn, "mss_panorama"):
                return []
            history_column = (
                "mss_temperature"
                if column_exists(conn, "mss_panorama", "mss_temperature")
                else (
                    "mss_score"
                    if column_exists(conn, "mss_panorama", "mss_score")
                    else ""
                )
            )
            if not history_column:
                return []
            rows = conn.execute(
                f"SELECT {history_column} FROM mss_panorama "
                f"WHERE trade_date < ? ORDER BY trade_date DESC LIMIT ?",
                [trade_date, limit],
            ).fetchall()
            return [
                float(row[0])
                for row in reversed(rows)
                if row and row[0] is not None
            ]

    def save_panorama(self, panorama: MssPanorama, trade_date: str) -> int:
        frame = pd.DataFrame.from_records([panorama.to_storage_record()])
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(self._database_path)) as conn:
            table_columns = ensure_columns(conn, "mss_panorama", frame)
            aligned = frame.copy()
            for col in table_columns:
                if col not in aligned.columns:
                    aligned[col] = pd.NA
            aligned = aligned[table_columns]
            conn.register("incoming_df", aligned)
            conn.execute(
                "DELETE FROM mss_panorama WHERE trade_date = ?",
                [trade_date],
            )
            conn.execute("INSERT INTO mss_panorama SELECT * FROM incoming_df")
            conn.unregister("incoming_df")
        return int(len(frame))
