"""批量生成缺失的 L2/L3 数据。

用法:
  python scripts/batch_generate_l2l3.py --phase 1   # L2 base (industry_snapshot/market_snapshot) for 2025
  python scripts/batch_generate_l2l3.py --phase 2   # MSS for 2025
  python scripts/batch_generate_l2l3.py --phase 3   # IRS for all missing dates
  python scripts/batch_generate_l2l3.py --phase 4   # PAS for all missing dates
  python scripts/batch_generate_l2l3.py --phase 5   # Integration (recommend) for all missing dates
  python scripts/batch_generate_l2l3.py --phase all  # Run all phases sequentially

注意: PAS (phase 4) 最耗时，约 9.3s/天 × ~1250天 ≈ 3.2小时
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

# 确保 src 在 import path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb

from src.config.config import Config


def _get_config() -> Config:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    return Config.from_env(env_file=str(env_file) if env_file.exists() else None)


def _get_db_path(config: Config) -> Path:
    return Path(config.duckdb_dir) / "emotionquant.duckdb"


def _get_open_trade_dates(db_path: Path, start: str = "20200102", end: str = "20260219") -> list[str]:
    with duckdb.connect(str(db_path), read_only=True) as conn:
        rows = conn.execute(
            "SELECT trade_date FROM raw_trade_cal "
            "WHERE CAST(is_open AS INTEGER) = 1 AND trade_date >= ? AND trade_date <= ? "
            "ORDER BY trade_date",
            [start, end],
        ).fetchall()
    return [r[0] for r in rows]


def _get_existing_dates(db_path: Path, table_name: str) -> set[str]:
    with duckdb.connect(str(db_path), read_only=True) as conn:
        rows = conn.execute(f"SELECT DISTINCT trade_date FROM {table_name}").fetchall()
    return {r[0] for r in rows}


def _missing_dates(db_path: Path, table_name: str, all_dates: list[str]) -> list[str]:
    existing = _get_existing_dates(db_path, table_name)
    return [d for d in all_dates if d not in existing]


def _run_phase(
    phase: int,
    dates: list[str],
    label: str,
    run_fn,
    *,
    skip_on_error: bool = True,
) -> tuple[int, int, list[str]]:
    total = len(dates)
    success = 0
    failed_dates: list[str] = []
    print(f"\n{'='*60}")
    print(f"Phase {phase}: {label}")
    print(f"Total dates to process: {total}")
    print(f"{'='*60}")

    t0 = time.time()
    for i, trade_date in enumerate(dates):
        try:
            run_fn(trade_date)
            success += 1
        except Exception as exc:
            failed_dates.append(trade_date)
            print(f"  [{i+1}/{total}] {trade_date} FAILED: {exc}")
            if not skip_on_error:
                raise
            continue
        elapsed = time.time() - t0
        avg = elapsed / (i + 1)
        remaining = avg * (total - i - 1)
        if (i + 1) % 10 == 0 or (i + 1) == total:
            print(
                f"  [{i+1}/{total}] {trade_date} OK  "
                f"({elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining, {avg:.1f}s/day)"
            )

    elapsed = time.time() - t0
    print(f"\nPhase {phase} done: {success}/{total} success, {len(failed_dates)} failed, {elapsed:.1f}s total")
    if failed_dates:
        print(f"  Failed dates: {failed_dates[:20]}{'...' if len(failed_dates) > 20 else ''}")
    return (success, len(failed_dates), failed_dates)


def phase1_l2_base(config: Config, db_path: Path, all_dates: list[str]) -> None:
    """Phase 1: Generate industry_snapshot + market_snapshot for missing dates."""
    from src.data.l2_pipeline import run_l2_snapshot

    missing = _missing_dates(db_path, "industry_snapshot", all_dates)
    # Also check market_snapshot
    missing_ms = _missing_dates(db_path, "market_snapshot", all_dates)
    combined = sorted(set(missing) | set(missing_ms))

    if not combined:
        print("Phase 1: No missing dates for L2 base. Skipping.")
        return

    def run_fn(trade_date: str) -> None:
        run_l2_snapshot(
            trade_date=trade_date,
            source="tushare",
            config=config,
            strict_sw31=False,
        )

    _run_phase(1, combined, "L2 base (industry_snapshot + market_snapshot)", run_fn)


def phase2_mss(config: Config, db_path: Path, all_dates: list[str]) -> None:
    """Phase 2: Generate mss_panorama for missing dates."""
    from src.algorithms.mss.pipeline import run_mss_scoring

    missing = _missing_dates(db_path, "mss_panorama", all_dates)

    if not missing:
        print("Phase 2: No missing dates for MSS. Skipping.")
        return

    def run_fn(trade_date: str) -> None:
        run_mss_scoring(
            trade_date=trade_date,
            config=config,
            threshold_mode="adaptive",
        )

    _run_phase(2, missing, "MSS (mss_panorama)", run_fn)


def phase3_irs(config: Config, db_path: Path, all_dates: list[str]) -> None:
    """Phase 3: Generate irs_industry_daily for missing dates."""
    from src.algorithms.irs.pipeline import run_irs_daily

    missing = _missing_dates(db_path, "irs_industry_daily", all_dates)

    if not missing:
        print("Phase 3: No missing dates for IRS. Skipping.")
        return

    def run_fn(trade_date: str) -> None:
        run_irs_daily(
            trade_date=trade_date,
            config=config,
            require_sw31=False,
        )

    _run_phase(3, missing, "IRS (irs_industry_daily)", run_fn)


def phase4_pas(config: Config, db_path: Path, all_dates: list[str]) -> None:
    """Phase 4: Generate stock_pas_daily for missing dates (~9.3s/day)."""
    from src.algorithms.pas.pipeline import run_pas_daily

    missing = _missing_dates(db_path, "stock_pas_daily", all_dates)

    if not missing:
        print("Phase 4: No missing dates for PAS. Skipping.")
        return

    def run_fn(trade_date: str) -> None:
        run_pas_daily(
            trade_date=trade_date,
            config=config,
        )

    _run_phase(4, missing, "PAS (stock_pas_daily) ~9.3s/day", run_fn)


def phase5_integration(config: Config, db_path: Path, all_dates: list[str]) -> None:
    """Phase 5: Generate integrated_recommendation for missing dates."""
    from src.integration.pipeline import run_integrated_daily
    from src.pipeline.recommend import _has_mss_for_trade_date

    missing = _missing_dates(db_path, "integrated_recommendation", all_dates)

    if not missing:
        print("Phase 5: No missing dates for Integration. Skipping.")
        return

    # 只处理有 MSS 数据的日期（否则 integration 会失败）
    eligible = [d for d in missing if _has_mss_for_trade_date(db_path, d)]
    skipped = len(missing) - len(eligible)
    if skipped > 0:
        print(f"Phase 5: {skipped} dates skipped (no MSS data)")

    if not eligible:
        print("Phase 5: No eligible dates for Integration (all missing MSS). Skipping.")
        return

    def run_fn(trade_date: str) -> None:
        # 检查当日 IRS 和 PAS 是否有数据
        with duckdb.connect(str(db_path), read_only=True) as conn:
            irs_count = conn.execute(
                "SELECT COUNT(*) FROM irs_industry_daily WHERE trade_date = ?", [trade_date]
            ).fetchone()[0]
            pas_count = conn.execute(
                "SELECT COUNT(*) FROM stock_pas_daily WHERE trade_date = ?", [trade_date]
            ).fetchone()[0]
            mss_row = conn.execute(
                "SELECT mss_score FROM mss_panorama WHERE trade_date = ? LIMIT 1", [trade_date]
            ).fetchone()

        if irs_count == 0 or pas_count == 0:
            raise ValueError(f"missing IRS({irs_count}) or PAS({pas_count}) for {trade_date}")

        run_integrated_daily(
            trade_date=trade_date,
            config=config,
            irs_count=irs_count,
            pas_count=pas_count,
            mss_exists=mss_row is not None,
        )

    _run_phase(5, eligible, "Integration (integrated_recommendation)", run_fn)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch generate missing L2/L3 data")
    parser.add_argument(
        "--phase",
        required=True,
        help="Phase to run: 1/2/3/4/5/all",
    )
    parser.add_argument(
        "--start",
        default="20200102",
        help="Start date (default: 20200102)",
    )
    parser.add_argument(
        "--end",
        default="20260219",
        help="End date (default: 20260219)",
    )
    args = parser.parse_args()

    config = _get_config()
    db_path = _get_db_path(config)
    all_dates = _get_open_trade_dates(db_path, args.start, args.end)
    print(f"Total open trade dates [{args.start} ~ {args.end}]: {len(all_dates)}")

    phases = {
        "1": lambda: phase1_l2_base(config, db_path, all_dates),
        "2": lambda: phase2_mss(config, db_path, all_dates),
        "3": lambda: phase3_irs(config, db_path, all_dates),
        "4": lambda: phase4_pas(config, db_path, all_dates),
        "5": lambda: phase5_integration(config, db_path, all_dates),
    }

    if args.phase == "all":
        for p in ("1", "2", "3", "4", "5"):
            phases[p]()
    elif args.phase in phases:
        phases[args.phase]()
    else:
        print(f"Unknown phase: {args.phase}. Choose from: 1, 2, 3, 4, 5, all")
        sys.exit(1)


if __name__ == "__main__":
    main()
