from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Sequence

from src import __version__
from src.config.config import Config
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot


@dataclass(frozen=True)
class PipelineContext:
    config: Config
    command: str


def _normalize_env_file(env_file: str | None) -> str | None:
    if env_file is None:
        return None
    value = env_file.strip()
    if not value:
        return None
    if value.lower() in {"none", "null"}:
        return None
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eq",
        description="EmotionQuant unified entrypoint (S0a minimal CLI).",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file. Use 'none' to disable file loading.",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print effective config snapshot after env injection.",
    )

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run minimal pipeline stub.")
    run_parser.add_argument("--date", required=True, help="Trade date in YYYYMMDD.")
    run_parser.add_argument("--source", default="tushare", help="Data source.")
    run_parser.add_argument(
        "--l1-only",
        action="store_true",
        help="Run S0b L1 collection and persistence only.",
    )
    run_parser.add_argument(
        "--to-l2",
        action="store_true",
        help="Run S0c L2 snapshot generation from existing L1 tables.",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not execute downstream tasks; only validate entry and config injection.",
    )

    subparsers.add_parser("version", help="Print CLI version.")

    return parser


def _config_snapshot(config: Config) -> dict[str, object]:
    return {
        "environment": config.environment,
        "data_path": config.data_path,
        "duckdb_dir": config.duckdb_dir,
        "parquet_path": config.parquet_path,
        "cache_path": config.cache_path,
        "log_path": config.log_path,
        "tushare_rate_limit_per_min": config.tushare_rate_limit_per_min,
    }


def _run_stub(ctx: PipelineContext, args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "event": "pipeline_start",
                "command": ctx.command,
                "trade_date": args.date,
                "source": args.source,
                "dry_run": bool(args.dry_run),
                "l1_only": bool(args.l1_only),
                "to_l2": bool(args.to_l2),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    if args.dry_run:
        print("dry-run completed: entrypoint and config injection are valid")
        return 0

    if args.l1_only and args.to_l2:
        print("invalid args: --l1-only and --to-l2 cannot be used together")
        return 2

    if args.l1_only:
        result = run_l1_collection(
            trade_date=args.date,
            source=args.source,
            config=ctx.config,
        )
        print(
            json.dumps(
                {
                    "event": "s0b_l1_only",
                    "trade_date": args.date,
                    "raw_counts": result.raw_counts,
                    "trade_cal_contains_trade_date": result.trade_cal_contains_trade_date,
                    "artifacts_dir": str(result.artifacts_dir),
                    "error_manifest_path": str(result.error_manifest_path),
                    "status": "failed" if result.has_error else "ok",
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 1 if result.has_error else 0

    if args.to_l2:
        result = run_l2_snapshot(
            trade_date=args.date,
            source=args.source,
            config=ctx.config,
        )
        print(
            json.dumps(
                {
                    "event": "s0c_to_l2",
                    "trade_date": args.date,
                    "market_snapshot_count": result.market_snapshot_count,
                    "industry_snapshot_count": result.industry_snapshot_count,
                    "artifacts_dir": str(result.artifacts_dir),
                    "canary_report_path": str(result.canary_report_path),
                    "error_manifest_path": str(result.error_manifest_path),
                    "status": "failed" if result.has_error else "ok",
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 1 if result.has_error else 0

    print("pipeline stub completed: downstream modules not implemented yet")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    command = args.command
    if command is None:
        parser.print_help()
        return 0

    if command == "version":
        print(__version__)
        return 0

    env_file = _normalize_env_file(args.env_file)
    config = Config.from_env(env_file=env_file)
    ctx = PipelineContext(config=config, command=command)

    if args.print_config:
        print(json.dumps(_config_snapshot(config), ensure_ascii=True, sort_keys=True))

    if command == "run":
        return _run_stub(ctx, args)

    parser.error(f"unsupported command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
