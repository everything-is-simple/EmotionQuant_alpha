"""从 DuckDB 导出全量 L1/L2 历史数据到按日期分区的 Parquet 文件。

用法:
  python scripts/export_duckdb_to_parquet.py               # 导出所有层
  python scripts/export_duckdb_to_parquet.py --layer l1     # 仅导出 L1
  python scripts/export_duckdb_to_parquet.py --layer l2     # 仅导出 L2
  python scripts/export_duckdb_to_parquet.py --dry-run      # 仅统计不写入

存储结构（对齐 data-layer-algorithm.md §2.3）：
  {parquet_path}/l1/{table_name}/{trade_date}.parquet
  {parquet_path}/l2/{table_name}/{trade_date}.parquet
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb
import pandas as pd

from src.config.config import Config


L1_TABLES = [
    "raw_daily",
    "raw_daily_basic",
    "raw_limit_list",
    "raw_index_daily",
    "raw_trade_cal",
    "raw_stock_basic",
    "raw_index_member",
    "raw_index_classify",
]

L2_TABLES = [
    "market_snapshot",
    "industry_snapshot",
]


def _get_config() -> Config:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    return Config.from_env(env_file=str(env_file) if env_file.exists() else None)


def _table_exists(conn: duckdb.DuckDBPyConnection, table: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _export_table(
    *,
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    output_dir: Path,
    dry_run: bool,
) -> tuple[int, int]:
    """导出一张表的所有数据到按日期分区的 Parquet 文件。

    Returns: (total_rows, file_count)
    """
    if not _table_exists(conn, table_name):
        print(f"  {table_name}: table not found, skipping")
        return (0, 0)

    # 获取所有不同的 trade_date
    has_trade_date = conn.execute(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name = ? AND column_name = 'trade_date'",
        [table_name],
    ).fetchone()
    has_trade_date = bool(has_trade_date and int(has_trade_date[0]) > 0)

    total_row = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
    total_rows = int(total_row[0]) if total_row else 0

    if total_rows == 0:
        print(f"  {table_name}: empty table, skipping")
        return (0, 0)

    table_dir = output_dir / table_name

    if not has_trade_date:
        if dry_run:
            print(f"  {table_name}: {total_rows} rows → 1 file (dry-run)")
            return (total_rows, 1)
        table_dir.mkdir(parents=True, exist_ok=True)
        df = conn.execute(f"SELECT * FROM {table_name}").df()
        df.to_parquet(table_dir / "latest.parquet", index=False)
        print(f"  {table_name}: {total_rows} rows → 1 file")
        return (total_rows, 1)

    dates = conn.execute(
        f"SELECT DISTINCT CAST(trade_date AS VARCHAR) as td FROM {table_name} ORDER BY td"
    ).fetchall()
    date_list = [str(r[0]).strip() for r in dates if str(r[0]).strip()]

    if dry_run:
        print(f"  {table_name}: {total_rows} rows, {len(date_list)} dates (dry-run)")
        return (total_rows, len(date_list))

    table_dir.mkdir(parents=True, exist_ok=True)

    # 已存在的文件跳过（增量导出）
    existing_files = {p.stem for p in table_dir.glob("*.parquet")}
    new_dates = [d for d in date_list if d not in existing_files]
    skipped = len(date_list) - len(new_dates)

    if not new_dates:
        print(f"  {table_name}: {total_rows} rows, all {len(date_list)} dates already exported")
        return (total_rows, 0)

    t0 = time.time()
    file_count = 0
    # 分批导出，每批 500 个日期，减少内存压力
    batch_size = 500
    for batch_start in range(0, len(new_dates), batch_size):
        batch_dates = new_dates[batch_start : batch_start + batch_size]
        placeholders = ",".join(["?"] * len(batch_dates))
        batch_df = conn.execute(
            f"SELECT * FROM {table_name} WHERE CAST(trade_date AS VARCHAR) IN ({placeholders})",
            batch_dates,
        ).df()

        if batch_df.empty:
            continue

        for trade_date_val, group in batch_df.groupby("trade_date"):
            file_name = str(trade_date_val).strip()
            if not file_name:
                continue
            group.to_parquet(table_dir / f"{file_name}.parquet", index=False)
            file_count += 1

        elapsed = time.time() - t0
        done = batch_start + len(batch_dates)
        if done % 1000 == 0 or done == len(new_dates):
            print(
                f"    {table_name}: {done}/{len(new_dates)} dates exported "
                f"({elapsed:.0f}s elapsed)"
            )

    elapsed = time.time() - t0
    print(
        f"  {table_name}: {total_rows} rows → {file_count} new files "
        f"({skipped} skipped, {elapsed:.1f}s)"
    )
    return (total_rows, file_count)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export DuckDB → per-date Parquet files")
    parser.add_argument("--layer", choices=["l1", "l2", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true", help="Only count, don't write")
    args = parser.parse_args()

    config = _get_config()
    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    parquet_base = Path(config.parquet_path)

    if not db_path.exists():
        print(f"ERROR: DuckDB not found at {db_path}")
        sys.exit(1)

    print(f"DuckDB: {db_path} ({db_path.stat().st_size / 1024**3:.2f} GB)")
    print(f"Parquet output: {parquet_base}")
    if args.dry_run:
        print("MODE: dry-run (no files will be written)")
    print()

    conn = duckdb.connect(str(db_path), read_only=True)

    grand_total_rows = 0
    grand_total_files = 0

    if args.layer in ("l1", "all"):
        print("=== L1 Export ===")
        l1_dir = parquet_base / "l1"
        for table in L1_TABLES:
            rows, files = _export_table(
                conn=conn, table_name=table, output_dir=l1_dir, dry_run=args.dry_run,
            )
            grand_total_rows += rows
            grand_total_files += files
        print()

    if args.layer in ("l2", "all"):
        print("=== L2 Export ===")
        l2_dir = parquet_base / "l2"
        for table in L2_TABLES:
            rows, files = _export_table(
                conn=conn, table_name=table, output_dir=l2_dir, dry_run=args.dry_run,
            )
            grand_total_rows += rows
            grand_total_files += files
        print()

    conn.close()

    print(f"Done: {grand_total_rows:,} total rows, {grand_total_files:,} files written")


if __name__ == "__main__":
    main()
