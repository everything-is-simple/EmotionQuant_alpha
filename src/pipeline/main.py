from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Sequence

from src import __version__
from src.algorithms.mss.pipeline import run_mss_scoring
from src.algorithms.mss.probe import run_mss_probe
from src.config.config import Config
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.recommend import run_recommendation

# DESIGN_TRACE:
# - Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md (§3 入口兼容规则, §5 各圈执行合同)
DESIGN_TRACE = {
    "s0_s2_roadmap": "Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md",
}


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
    mss_parser = subparsers.add_parser("mss", help="Run MSS minimal scoring for a trade date.")
    mss_parser.add_argument("--date", required=True, help="Trade date in YYYYMMDD.")
    probe_parser = subparsers.add_parser("mss-probe", help="Run MSS-only probe on date range.")
    probe_parser.add_argument("--start", required=True, help="Start trade date in YYYYMMDD.")
    probe_parser.add_argument("--end", required=True, help="End trade date in YYYYMMDD.")
    recommend_parser = subparsers.add_parser("recommend", help="Run recommendation pipeline.")
    recommend_parser.add_argument("--date", required=True, help="Trade date in YYYYMMDD.")
    recommend_parser.add_argument(
        "--mode",
        required=True,
        help="Pipeline mode, e.g. mss_irs_pas or integrated.",
    )
    recommend_parser.add_argument(
        "--with-validation",
        action="store_true",
        help="Enable validation gate generation.",
    )
    recommend_parser.add_argument(
        "--with-validation-bridge",
        action="store_true",
        help="Enable S2c bridge checks between validation gate and selected weight plan.",
    )
    recommend_parser.add_argument(
        "--evidence-lane",
        choices=("release", "debug"),
        default="debug",
        help="Artifact lane for S2c evidence (release/debug).",
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


def _run_mss(ctx: PipelineContext, args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "event": "mss_start",
                "command": ctx.command,
                "trade_date": args.date,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )

    result = run_mss_scoring(
        trade_date=args.date,
        config=ctx.config,
    )
    print(
        json.dumps(
            {
                "event": "s1a_mss",
                "trade_date": args.date,
                "mss_panorama_count": result.mss_panorama_count,
                "artifacts_dir": str(result.artifacts_dir),
                "sample_path": str(result.sample_path),
                "factor_trace_path": str(result.factor_trace_path),
                "error_manifest_path": str(result.error_manifest_path),
                "status": "failed" if result.has_error else "ok",
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 1 if result.has_error else 0


def _run_mss_probe(ctx: PipelineContext, args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "event": "mss_probe_start",
                "command": ctx.command,
                "start_date": args.start,
                "end_date": args.end,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    try:
        result = run_mss_probe(
            start_date=args.start,
            end_date=args.end,
            config=ctx.config,
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    print(
        json.dumps(
            {
                "event": "s1b_mss_probe",
                "start_date": args.start,
                "end_date": args.end,
                "artifacts_dir": str(result.artifacts_dir),
                "probe_report_path": str(result.probe_report_path),
                "consumption_case_path": str(result.consumption_case_path),
                "error_manifest_path": str(result.error_manifest_path),
                "top_bottom_spread_5d": result.top_bottom_spread_5d,
                "conclusion": result.conclusion,
                "status": "failed" if result.has_error else "ok",
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 1 if result.has_error else 0


def _run_recommend(ctx: PipelineContext, args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "event": "recommend_start",
                "command": ctx.command,
                "trade_date": args.date,
                "mode": args.mode,
                "with_validation": bool(args.with_validation),
                "with_validation_bridge": bool(args.with_validation_bridge),
                "evidence_lane": args.evidence_lane,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    try:
        result = run_recommendation(
            trade_date=args.date,
            mode=args.mode,
            with_validation=bool(args.with_validation),
            with_validation_bridge=bool(args.with_validation_bridge),
            evidence_lane=args.evidence_lane,
            config=ctx.config,
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    if args.mode == "integrated":
        payload = {
            "event": "s2b_recommend",
            "trade_date": args.date,
            "mode": args.mode,
            "with_validation_bridge": bool(args.with_validation_bridge),
            "evidence_lane": result.evidence_lane,
            "final_gate": result.final_gate,
            "integrated_count": result.integrated_count,
            "quality_gate_status": result.quality_gate_status,
            "go_nogo": result.go_nogo,
            "artifacts_dir": str(result.artifacts_dir),
            "integrated_sample_path": str(result.integrated_sample_path),
            "quality_gate_report_path": str(result.quality_gate_report_path),
            "go_nogo_decision_path": str(result.go_nogo_decision_path),
            "error_manifest_path": str(result.error_manifest_path),
            "status": "failed" if result.has_error else "ok",
        }
    else:
        payload = {
            "event": "s2a_recommend",
            "trade_date": args.date,
            "mode": args.mode,
            "evidence_lane": result.evidence_lane,
            "irs_count": result.irs_count,
            "pas_count": result.pas_count,
            "validation_count": result.validation_count,
            "final_gate": result.final_gate,
            "artifacts_dir": str(result.artifacts_dir),
            "irs_sample_path": str(result.irs_sample_path),
            "pas_sample_path": str(result.pas_sample_path),
            "validation_sample_path": str(result.validation_sample_path),
            "error_manifest_path": str(result.error_manifest_path),
            "status": "failed" if result.has_error else "ok",
        }
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return 1 if result.has_error else 0


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
    if command == "mss":
        return _run_mss(ctx, args)
    if command == "mss-probe":
        return _run_mss_probe(ctx, args)
    if command == "recommend":
        return _run_recommend(ctx, args)

    parser.error(f"unsupported command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
