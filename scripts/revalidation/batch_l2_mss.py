"""
批量生成 L2 快照 + MSS 评分（螺旋1 Canary 重验用）

用法:
    python scripts/revalidation/batch_l2_mss.py --start 20200102 --end 20241231

逻辑:
    1. 从 raw_trade_cal 读取窗口内所有开市日
    2. 跳过已有 mss_panorama 记录的日期
    3. 对每个缺失日期串行执行: L2 -> MSS
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
from src.data.l2_pipeline import run_l2_snapshot
from src.algorithms.mss.pipeline import run_mss_scoring


def get_open_trade_dates(db_path: str, start: str, end: str) -> list[str]:
    """从交易日历获取窗口内所有开市日"""
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


def get_existing_mss_dates(db_path: str, start: str, end: str) -> set[str]:
    """获取已有 MSS 记录的日期集合"""
    with duckdb.connect(db_path, read_only=True) as conn:
        rows = conn.execute(
            "SELECT DISTINCT CAST(trade_date AS VARCHAR) AS d FROM mss_panorama "
            "WHERE CAST(trade_date AS VARCHAR) >= ? "
            "AND CAST(trade_date AS VARCHAR) <= ? ",
            [start, end],
        ).fetchall()
    return {r[0] for r in rows}


def get_existing_l2_dates(db_path: str, start: str, end: str) -> set[str]:
    """获取已有 L2 market_snapshot 的日期集合"""
    with duckdb.connect(db_path, read_only=True) as conn:
        rows = conn.execute(
            "SELECT DISTINCT CAST(trade_date AS VARCHAR) AS d FROM market_snapshot "
            "WHERE CAST(trade_date AS VARCHAR) >= ? "
            "AND CAST(trade_date AS VARCHAR) <= ? ",
            [start, end],
        ).fetchall()
    return {r[0] for r in rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="批量生成 L2+MSS")
    parser.add_argument("--start", required=True, help="起始日 YYYYMMDD")
    parser.add_argument("--end", required=True, help="截止日 YYYYMMDD")
    parser.add_argument("--env-file", default=".env", help="环境文件")
    parser.add_argument("--skip-l2", action="store_true", help="跳过 L2 生成（仅补 MSS）")
    parser.add_argument("--dry-run", action="store_true", help="只列出待处理日期")
    args = parser.parse_args()

    config = Config.from_env(env_file=args.env_file)
    db_path = str(Path(config.duckdb_dir) / "emotionquant.duckdb")

    # 获取待处理日期
    all_dates = get_open_trade_dates(db_path, args.start, args.end)
    existing_mss = get_existing_mss_dates(db_path, args.start, args.end)
    existing_l2 = get_existing_l2_dates(db_path, args.start, args.end)

    need_l2 = [d for d in all_dates if d not in existing_l2] if not args.skip_l2 else []
    need_mss = [d for d in all_dates if d not in existing_mss]

    # 合并：需要处理的日期 = 需要 L2 或 MSS 的日期
    need_any = sorted(set(need_l2) | set(need_mss))

    print(json.dumps({
        "event": "batch_plan",
        "total_open_days": len(all_dates),
        "existing_l2": len(existing_l2),
        "existing_mss": len(existing_mss),
        "need_l2": len(need_l2),
        "need_mss": len(need_mss),
        "need_any": len(need_any),
        "start": args.start,
        "end": args.end,
    }))

    if args.dry_run:
        print(f"Dry run: {len(need_any)} dates to process")
        return 0

    # 批量执行
    t0 = time.time()
    success = 0
    failed = 0
    failed_dates: list[str] = []

    for i, trade_date in enumerate(need_any, 1):
        t_start = time.time()
        try:
            # L2
            if trade_date not in existing_l2 and not args.skip_l2:
                run_l2_snapshot(
                    trade_date=trade_date,
                    source="tushare",
                    config=config,
                    strict_sw31=True,
                )

            # MSS
            if trade_date not in existing_mss:
                run_mss_scoring(
                    trade_date=trade_date,
                    config=config,
                    threshold_mode="adaptive",
                )

            elapsed = time.time() - t_start
            success += 1

            # 进度输出（每 10 个或第一个）
            if i == 1 or i % 10 == 0 or i == len(need_any):
                total_elapsed = time.time() - t0
                rate = success / total_elapsed if total_elapsed > 0 else 0
                eta = (len(need_any) - i) / rate if rate > 0 else 0
                print(
                    f"[{i}/{len(need_any)}] {trade_date} ok "
                    f"({elapsed:.1f}s) "
                    f"rate={rate:.2f}/s "
                    f"ETA={eta/60:.0f}min",
                    flush=True,
                )

        except Exception as exc:
            failed += 1
            failed_dates.append(trade_date)
            elapsed = time.time() - t_start
            print(f"[{i}/{len(need_any)}] {trade_date} FAILED ({elapsed:.1f}s): {exc}", flush=True)

    total_time = time.time() - t0
    print(json.dumps({
        "event": "batch_complete",
        "total_processed": success + failed,
        "success": success,
        "failed": failed,
        "failed_dates": failed_dates[:20],
        "total_seconds": round(total_time, 1),
        "avg_seconds_per_date": round(total_time / max(1, success + failed), 2),
    }))

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
