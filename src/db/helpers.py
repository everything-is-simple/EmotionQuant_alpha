"""DuckDB 公共辅助函数：消除跨模块重复定义（TD-DA-004）。

提取自 IRS/PAS/Validation/MSS/Integration/Analysis/Backtest/Trading/GUI 等模块中
完全相同的 _table_exists / _column_exists / _duckdb_type / _ensure_columns / _persist
实现，统一维护于此。
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


def table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    """检查 DuckDB 中是否存在指定表。"""
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def column_exists(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    column_name: str,
) -> bool:
    """检查 DuckDB 指定表中是否存在指定列。"""
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = ? AND column_name = ?",
        [table_name, column_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def duckdb_type(series: pd.Series) -> str:
    """根据 pandas Series dtype 推断对应的 DuckDB 列类型。"""
    if pd.api.types.is_bool_dtype(series):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(series):
        return "BIGINT"
    if pd.api.types.is_float_dtype(series):
        return "DOUBLE"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "TIMESTAMP"
    return "VARCHAR"


def ensure_columns(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    frame: pd.DataFrame,
) -> list[str]:
    """确保表存在且包含 frame 中的所有列，返回最终列列表。

    若表不存在则根据 frame schema 创建空表；若表已存在但缺少列则 ALTER ADD。
    """
    if not table_exists(connection, table_name):
        connection.register("schema_df", frame)
        connection.execute(
            f"CREATE TABLE {table_name} AS SELECT * FROM schema_df WHERE 1=0"
        )
        connection.unregister("schema_df")
    else:
        existing = {
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        }
        for column in frame.columns:
            if column in existing:
                continue
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column} {duckdb_type(frame[column])}"
            )

    return [
        str(row[1]) for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    ]


def persist_by_trade_date(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
    trade_date: str,
) -> int:
    """按 trade_date 幂等写入：ensure_columns → 对齐列 → 删旧 → 插新。

    适用于 IRS / PAS / Validation 等标准流水线的 _persist 模式。
    """
    with duckdb.connect(str(database_path)) as connection:
        table_columns = ensure_columns(connection, table_name, frame)
        aligned = frame.copy()
        for column in table_columns:
            if column not in aligned.columns:
                aligned[column] = pd.NA
        aligned = aligned[table_columns]
        connection.register("incoming_df", aligned)
        connection.execute(f"DELETE FROM {table_name} WHERE trade_date = ?", [trade_date])
        connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_df")
        connection.unregister("incoming_df")
    return int(len(aligned))
