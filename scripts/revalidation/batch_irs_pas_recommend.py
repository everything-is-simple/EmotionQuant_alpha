"""
批量生成 IRS + PAS + Integrated Recommendation（螺旋1 Canary 重验用）

用法（串行）:
    python scripts/revalidation/batch_irs_pas_recommend.py --start 20200102 --end 20241231

用法（分片并行 — 开 4 个终端各跑一片，避免 DuckDB 写锁冲突）:
    # 终端1: python scripts/revalidation/batch_irs_pas_recommend.py --start 20200102 --end 20211231
    # 终端2: python scripts/revalidation/batch_irs_pas_recommend.py --start 20220101 --end 20221231
    # 终端3: python scripts/revalidation/batch_irs_pas_recommend.py --start 20230101 --end 20231231
    # 终端4: python scripts/revalidation/batch_irs_pas_recommend.py --start 20240101 --end 20241231

注意: DuckDB 单文件同一时刻只允许一个写连接。多进程并发写同一个 .duckdb
      文件会抛 IOException / lock 错误。因此本脚本保持串行，用日期分片
      在多终端跑来加速。

逻辑:
    1. 从 raw_trade_cal 读取窗口内所有开市日
    2. 跳过已有 integrated_recommendation 记录的日期
    3. 串行执行: IRS -> PAS -> Validation -> Integration(top_down)
    4. 输出进度与汇总
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# 确保 src 包可导入
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import duckdb

from src.config.config import Config
from src.algorithms.irs.pipeline import run_irs_daily
from src.algorithms.pas.pipeline import run_pas_daily
from src.algorithms.validation.pipeline import run_validation_gate
from src.integration.pipeline import run_integrated_daily


def get_open_trade_dates(db_path: str, start: str, end: str) -> list[str]:
    with duckdb.connect(db_path, read_only=True) as conn:
        rows = conn.execute(
            "SELECT CAST(cal_date AS VARCHAR) AS d FROM raw_trade_cal "
            "WHERE is_open = 1 "
            "AND CAST(cal_date AS VARCHAR) >= ? "
            "AND CAST(cal_date AS VARCHAR) <= ? "
            "ORDER BY d",
            [start, end],
        ).fetchall()
    return [r[0] for r in rows]


def get_existing_dates(db_path: str, table: str, start: str, end: str) -> set[str]:
    with duckdb.connect(db_path, read_only=True) as conn:
        try:
            rows = conn.execute(
                f"SELECT DISTINCT CAST(trade_date AS VARCHAR) AS d FROM {table} "
                "WHERE CAST(trade_date AS VARCHAR) >= ? "
                "AND CAST(trade_date AS VARCHAR) <= ? ",
                [start, end],
            ).fetchall()
        except Exception:
            return set()
    return {r[0] for r in rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="批量生成 IRS+PAS+Recommend（串行，分片友好）")
    parser.add_argument("--start", required=True, help="起始日 YYYYMMDD")
    parser.add_argument("--end", required=True, help="截止日 YYYYMMDD")
    parser.add_argument("--env-file", default=".env", help="环境文件")
    parser.add_argument("--force", action="store_true", help="强制重算所有日期")
    parser.add_argument("--dry-run", action="store_true", help="只列出待处理日期")
    args = parser.parse_args()

    config = Config.from_env(env_file=args.env_file)
    db_path = str(Path(config.duckdb_dir) / "emotionquant.duckdb")

    all_dates = get_open_trade_dates(db_path, args.start, args.end)
    existing_mss = get_existing_dates(db_path, "mss_panorama", args.start, args.end)
    dates_with_mss = [d for d in all_dates if d in existing_mss]

    if args.force:
        need_process = dates_with_mss
    else:
        existing_integrated = get_existing_dates(
            db_path, "integrated_recommendation", args.start, args.end
        )
        need_process = [d for d in dates_with_mss if d not in existing_integrated]

    print(json.dumps({
        "event": "batch_plan",
        "total_open_days": len(all_dates),
        "dates_with_mss": len(dates_with_mss),
        "already_integrated": len(dates_with_mss) - len(need_process),
        "need_process": len(need_process),
        "start": args.start,
        "end": args.end,
    }), flush=True)

    if args.dry_run:
        print(f"Dry run: {len(need_process)} dates to process")
        return 0

    if not need_process:
        print("Nothing to process.")
        return 0

    t0 = time.time()
    success = 0
    failed = 0
    failed_dates: list[str] = []

    for i, trade_date in enumerate(need_process, 1):
        t_start = time.time()
        try:
            # IRS
            run_irs_daily(trade_date=trade_date, config=config)

            # PAS
            run_pas_daily(trade_date=trade_date, config=config)

            # Validation
            with duckdb.connect(db_path, read_only=True) as conn:
                irs_count = int(conn.execute(
                    "SELECT COUNT(*) FROM irs_industry_daily WHERE trade_date = ?",
                    [trade_date],
                ).fetchone()[0])
                pas_count = int(conn.execute(
                    "SELECT COUNT(*) FROM stock_pas_daily WHERE trade_date = ?",
                    [trade_date],
                ).fetchone()[0])
                mss_count = int(conn.execute(
                    "SELECT COUNT(*) FROM mss_panorama WHERE trade_date = ?",
                    [trade_date],
                ).fetchone()[0])

            run_validation_gate(
                trade_date=trade_date,
                config=config,
                irs_count=irs_count,
                pas_count=pas_count,
                mss_exists=mss_count > 0,
                threshold_mode="fixed",
                wfa_mode="single-window",
            )

            # Integration
            run_integrated_daily(
                trade_date=trade_date,
                config=config,
                integration_mode="top_down",
            )

            elapsed = time.time() - t_start
            success += 1

            if i == 1 or i % 10 == 0 or i == len(need_process):
                total_elapsed = time.time() - t0
                rate = success / total_elapsed if total_elapsed > 0 else 0
                eta = (len(need_process) - i) / rate if rate > 0 else 0
                print(
                    f"[{i}/{len(need_process)}] {trade_date} ok "
                    f"({elapsed:.1f}s) rate={rate:.2f}/s ETA={eta / 60:.0f}min",
                    flush=True,
                )

        except Exception as exc:
            failed += 1
            failed_dates.append(trade_date)
            elapsed = time.time() - t_start
            print(
                f"[{i}/{len(need_process)}] {trade_date} FAILED ({elapsed:.1f}s): {exc}",
                flush=True,
            )

    total_time = time.time() - t0
    print(json.dumps({
        "event": "batch_complete",
        "total_processed": success + failed,
        "success": success,
        "failed": failed,
        "failed_dates": failed_dates[:20],
        "total_seconds": round(total_time, 1),
        "avg_seconds_per_date": round(total_time / max(1, success + failed), 2),
    }), flush=True)

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
