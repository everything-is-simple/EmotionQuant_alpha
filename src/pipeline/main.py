from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Sequence

from src.backtest.pipeline import run_backtest
from src.analysis.pipeline import run_analysis
from src import __version__
from src.algorithms.irs.pipeline import run_irs_daily
from src.algorithms.mss.pipeline import run_mss_scoring
from src.algorithms.mss.probe import run_mss_probe
from src.config.config import Config
from src.data.fetch_batch_pipeline import (
    FetchBatchProgressEvent,
    read_fetch_status,
    run_fetch_batch,
    run_fetch_retry,
)
from src.data.l1_pipeline import run_l1_collection
from src.data.l2_pipeline import run_l2_snapshot
from src.pipeline.recommend import run_recommendation
from src.trading.pipeline import run_paper_trade

# DESIGN_TRACE:
# - Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md (§3 入口兼容规则, §5 各圈执行合同)
# - Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md (§5 S3a)
# - Governance/SpiralRoadmap/S3A-EXECUTION-CARD.md (§2 run, §3 test, §4 artifact)
# - docs/design/core-infrastructure/backtest/backtest-algorithm.md (§1-§4)
# - docs/design/core-infrastructure/analysis/analysis-algorithm.md (§1-§4)
# - docs/design/core-infrastructure/trading/trading-algorithm.md (§2-§5)
DESIGN_TRACE = {
    "s0_s2_roadmap": "Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md",
    "s3a_s4b_roadmap": "Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md",
    "s3a_execution_card": "Governance/SpiralRoadmap/S3A-EXECUTION-CARD.md",
    "backtest_algorithm_design": "docs/design/core-infrastructure/backtest/backtest-algorithm.md",
    "analysis_algorithm_design": "docs/design/core-infrastructure/analysis/analysis-algorithm.md",
    "trading_algorithm_design": "docs/design/core-infrastructure/trading/trading-algorithm.md",
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
        "--strict-sw31",
        dest="strict_sw31",
        action="store_true",
        default=True,
        help="Require SW31 coverage when running --to-l2 (default enabled).",
    )
    run_parser.add_argument(
        "--allow-all-fallback",
        dest="strict_sw31",
        action="store_false",
        help="Disable SW31 strict gate for debugging only.",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not execute downstream tasks; only validate entry and config injection.",
    )
    mss_parser = subparsers.add_parser("mss", help="Run MSS minimal scoring for a trade date.")
    mss_parser.add_argument("--date", required=True, help="Trade date in YYYYMMDD.")
    irs_parser = subparsers.add_parser("irs", help="Run IRS scoring for a trade date.")
    irs_parser.add_argument("--date", required=True, help="Trade date in YYYYMMDD.")
    irs_parser.add_argument(
        "--require-sw31",
        action="store_true",
        help="Enable SW31 full coverage gate (S3c strict mode).",
    )
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
        "--integration-mode",
        choices=("top_down", "bottom_up", "dual_verify", "complementary"),
        default="top_down",
        help="Integration mode for --mode integrated (default top_down).",
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
    recommend_parser.add_argument(
        "--repair",
        choices=("s2r",),
        default=None,
        help="Run S2r repair workflow for integrated mode.",
    )
    fetch_batch_parser = subparsers.add_parser(
        "fetch-batch",
        help="Run S3a fetch batches with resumable progress.",
    )
    fetch_batch_parser.add_argument("--start", required=True, help="Start trade date in YYYYMMDD.")
    fetch_batch_parser.add_argument("--end", required=True, help="End trade date in YYYYMMDD.")
    fetch_batch_parser.add_argument(
        "--batch-size",
        type=int,
        default=365,
        help="Batch size by calendar days, default 365.",
    )
    fetch_batch_parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Parallel workers for fetch, default 3.",
    )
    fetch_batch_parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable realtime progress bar output to stderr.",
    )
    backtest_parser = subparsers.add_parser("backtest", help="Run S3 backtest baseline pipeline.")
    backtest_parser.add_argument(
        "--engine",
        default="qlib",
        help="Backtest engine: qlib/local_vectorized/backtrader_compat.",
    )
    backtest_parser.add_argument("--start", required=True, help="Start trade date in YYYYMMDD.")
    backtest_parser.add_argument("--end", required=True, help="End trade date in YYYYMMDD.")
    trade_parser = subparsers.add_parser("trade", help="Run S4 paper trading pipeline.")
    trade_parser.add_argument(
        "--mode",
        required=True,
        help="Trading mode. Current supported: paper.",
    )
    trade_parser.add_argument("--date", required=True, help="Trade date in YYYYMMDD.")
    analysis_parser = subparsers.add_parser("analysis", help="Run S3b analysis pipeline.")
    analysis_parser.add_argument("--start", help="Start trade date in YYYYMMDD.")
    analysis_parser.add_argument("--end", help="End trade date in YYYYMMDD.")
    analysis_parser.add_argument("--date", help="Trade date in YYYYMMDD.")
    analysis_parser.add_argument(
        "--ab-benchmark",
        action="store_true",
        help="Generate A/B/C benchmark report in S3b.",
    )
    analysis_parser.add_argument(
        "--deviation",
        choices=("live-backtest",),
        help="Generate live-backtest deviation report.",
    )
    analysis_parser.add_argument(
        "--attribution-summary",
        action="store_true",
        help="Generate signal attribution summary output.",
    )
    subparsers.add_parser("fetch-status", help="Show latest S3a fetch status.")
    subparsers.add_parser("fetch-retry", help="Retry failed S3a fetch batches.")

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
        "flat_threshold": config.flat_threshold,
        "min_coverage_ratio": config.min_coverage_ratio,
        "stale_hard_limit_days": config.stale_hard_limit_days,
        "enable_intraday_incremental": config.enable_intraday_incremental,
        "tushare_primary_sdk_provider": str(
            config.tushare_primary_sdk_provider or config.tushare_sdk_provider
        ),
        "tushare_primary_http_url": str(
            config.tushare_primary_http_url or config.tushare_http_url
        ),
        "tushare_has_primary_token": bool(
            str(config.tushare_primary_token or config.tushare_token).strip()
        ),
        "tushare_fallback_sdk_provider": str(config.tushare_fallback_sdk_provider),
        "tushare_fallback_http_url": str(config.tushare_fallback_http_url),
        "tushare_has_fallback_token": bool(str(config.tushare_fallback_token).strip()),
        "tushare_rate_limit_per_min": config.tushare_rate_limit_per_min,
        "tushare_primary_rate_limit_per_min": config.tushare_primary_rate_limit_per_min,
        "tushare_fallback_rate_limit_per_min": config.tushare_fallback_rate_limit_per_min,
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
                "strict_sw31": bool(args.strict_sw31),
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
            strict_sw31=bool(args.strict_sw31),
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


def _run_irs(ctx: PipelineContext, args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "event": "irs_start",
                "command": ctx.command,
                "trade_date": args.date,
                "require_sw31": bool(args.require_sw31),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    try:
        result = run_irs_daily(
            trade_date=args.date,
            config=ctx.config,
            require_sw31=bool(args.require_sw31),
        )
    except ValueError as exc:
        print(str(exc))
        return 2

    print(
        json.dumps(
            {
                "event": "s3c_irs",
                "trade_date": args.date,
                "require_sw31": bool(args.require_sw31),
                "irs_industry_count": result.count,
                "factor_intermediate_sample_path": str(result.factor_intermediate_sample_path),
                "coverage_report_path": str(result.coverage_report_path),
                "status": "ok",
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


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
                "integration_mode": args.integration_mode,
                "with_validation": bool(args.with_validation),
                "with_validation_bridge": bool(args.with_validation_bridge),
                "evidence_lane": args.evidence_lane,
                "repair": str(args.repair or ""),
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
            repair=str(args.repair or ""),
            integration_mode=str(args.integration_mode or "top_down"),
            evidence_lane=args.evidence_lane,
            config=ctx.config,
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    if args.mode == "integrated":
        event_name = "s2r_recommend" if str(args.repair or "") == "s2r" else "s2b_recommend"
        payload = {
            "event": event_name,
            "trade_date": args.date,
            "mode": args.mode,
            "integration_mode": result.integration_mode,
            "repair": str(args.repair or ""),
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
        if result.s2r_patch_note_path is not None:
            payload["s2r_patch_note_path"] = str(result.s2r_patch_note_path)
        if result.s2r_delta_report_path is not None:
            payload["s2r_delta_report_path"] = str(result.s2r_delta_report_path)
    else:
        payload = {
            "event": "s2a_recommend",
            "trade_date": args.date,
            "mode": args.mode,
            "integration_mode": result.integration_mode,
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


def _run_fetch_batch(ctx: PipelineContext, args: argparse.Namespace) -> int:
    def _render_progress(event: FetchBatchProgressEvent) -> None:
        total = max(1, int(event.total_batches))
        processed = min(int(event.processed_batches), total)
        ratio = processed / total
        width = 24
        filled = int(ratio * width)
        bar = f"{'#' * filled}{'-' * (width - filled)}"
        head = (
            f"\r[fetch-batch] [{bar}] {ratio * 100:6.2f}% "
            f"{processed}/{total} completed={event.completed_batches} failed={event.failed_batches}"
        )
        if event.current_batch_id is None:
            tail = f" status={event.current_status}"
        else:
            tail = (
                f" batch={event.current_batch_id} "
                f"{event.current_start_date}-{event.current_end_date} {event.current_status}"
            )
        print(f"{head}{tail}", end="", file=sys.stderr, flush=True)
        if event.current_batch_id is None and event.current_status != "started":
            print("", file=sys.stderr, flush=True)

    progress_callback = None if bool(args.no_progress) else _render_progress
    try:
        result = run_fetch_batch(
            start_date=args.start,
            end_date=args.end,
            batch_size=int(args.batch_size),
            workers=int(args.workers),
            config=ctx.config,
            progress_callback=progress_callback,
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    print(
        json.dumps(
            {
                "event": "s3a_fetch_batch",
                "start_date": result.start_date,
                "end_date": result.end_date,
                "batch_size": result.batch_size,
                "workers": result.workers,
                "total_batches": result.total_batches,
                "completed_batches": result.completed_batches,
                "failed_batches": result.failed_batches,
                "last_success_batch_id": result.last_success_batch_id,
                "status": result.status,
                "artifacts_dir": str(result.artifacts_dir),
                "progress_path": str(result.progress_path),
                "throughput_benchmark_path": str(result.throughput_benchmark_path),
                "retry_report_path": str(result.retry_report_path),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 1 if result.has_error else 0


def _run_fetch_status(ctx: PipelineContext) -> int:
    result = read_fetch_status(config=ctx.config)
    print(
        json.dumps(
            {
                "event": "s3a_fetch_status",
                "start_date": result.start_date,
                "end_date": result.end_date,
                "batch_size": result.batch_size,
                "workers": result.workers,
                "total_batches": result.total_batches,
                "completed_batches": result.completed_batches,
                "failed_batches": result.failed_batches,
                "last_success_batch_id": result.last_success_batch_id,
                "status": result.status,
                "artifacts_dir": str(result.artifacts_dir),
                "progress_path": str(result.progress_path),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


def _run_fetch_retry(ctx: PipelineContext) -> int:
    try:
        result = run_fetch_retry(config=ctx.config)
    except ValueError as exc:
        print(str(exc))
        return 2
    print(
        json.dumps(
            {
                "event": "s3a_fetch_retry",
                "retried_batches": result.retried_batches,
                "total_batches": result.total_batches,
                "completed_batches": result.completed_batches,
                "failed_batches": result.failed_batches,
                "status": result.status,
                "artifacts_dir": str(result.artifacts_dir),
                "progress_path": str(result.progress_path),
                "retry_report_path": str(result.retry_report_path),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 1 if result.has_error else 0


def _run_backtest(ctx: PipelineContext, args: argparse.Namespace) -> int:
    try:
        result = run_backtest(
            start_date=args.start,
            end_date=args.end,
            engine=args.engine,
            config=ctx.config,
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    print(
        json.dumps(
            {
                "event": "s3_backtest",
                "backtest_id": result.backtest_id,
                "engine": result.engine,
                "start_date": result.start_date,
                "end_date": result.end_date,
                "consumed_signal_rows": result.consumed_signal_rows,
                "total_trades": result.total_trades,
                "quality_status": result.quality_status,
                "go_nogo": result.go_nogo,
                "bridge_check_status": result.bridge_check_status,
                "artifacts_dir": str(result.artifacts_dir),
                "backtest_results_path": str(result.backtest_results_path),
                "backtest_trade_records_path": str(result.backtest_trade_records_path),
                "ab_metric_summary_path": str(result.ab_metric_summary_path),
                "gate_report_path": str(result.gate_report_path),
                "consumption_path": str(result.consumption_path),
                "error_manifest_path": str(result.error_manifest_path),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 1 if result.has_error else 0


def _run_trade(ctx: PipelineContext, args: argparse.Namespace) -> int:
    try:
        result = run_paper_trade(
            trade_date=args.date,
            mode=args.mode,
            config=ctx.config,
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    print(
        json.dumps(
            {
                "event": "s4_trade",
                "trade_date": result.trade_date,
                "mode": result.mode,
                "total_orders": result.total_orders,
                "filled_orders": result.filled_orders,
                "risk_event_count": result.risk_event_count,
                "quality_status": result.quality_status,
                "go_nogo": result.go_nogo,
                "artifacts_dir": str(result.artifacts_dir),
                "trade_records_path": str(result.trade_records_path),
                "positions_path": str(result.positions_path),
                "risk_events_path": str(result.risk_events_path),
                "paper_trade_replay_path": str(result.paper_trade_replay_path),
                "consumption_path": str(result.consumption_path),
                "gate_report_path": str(result.gate_report_path),
                "error_manifest_path": str(result.error_manifest_path),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 1 if result.has_error else 0


def _run_analysis(ctx: PipelineContext, args: argparse.Namespace) -> int:
    try:
        result = run_analysis(
            config=ctx.config,
            start_date=str(args.start or "").strip(),
            end_date=str(args.end or "").strip(),
            trade_date=str(args.date or "").strip(),
            run_ab_benchmark=bool(args.ab_benchmark),
            deviation_mode=str(args.deviation or "").strip(),
            run_attribution_summary=bool(args.attribution_summary),
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    print(
        json.dumps(
            {
                "event": "s3b_analysis",
                "trade_date": result.trade_date,
                "start_date": result.start_date,
                "end_date": result.end_date,
                "quality_status": result.quality_status,
                "go_nogo": result.go_nogo,
                "artifacts_dir": str(result.artifacts_dir),
                "ab_benchmark_report_path": str(result.ab_benchmark_report_path),
                "live_backtest_deviation_report_path": str(result.live_backtest_deviation_report_path),
                "attribution_summary_path": str(result.attribution_summary_path),
                "consumption_path": str(result.consumption_path),
                "gate_report_path": str(result.gate_report_path),
                "error_manifest_path": str(result.error_manifest_path),
                "status": "failed" if result.has_error else "ok",
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
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
    if command == "irs":
        return _run_irs(ctx, args)
    if command == "mss-probe":
        return _run_mss_probe(ctx, args)
    if command == "recommend":
        return _run_recommend(ctx, args)
    if command == "fetch-batch":
        return _run_fetch_batch(ctx, args)
    if command == "fetch-status":
        return _run_fetch_status(ctx)
    if command == "fetch-retry":
        return _run_fetch_retry(ctx)
    if command == "backtest":
        return _run_backtest(ctx, args)
    if command == "trade":
        return _run_trade(ctx, args)
    if command == "analysis":
        return _run_analysis(ctx, args)

    parser.error(f"unsupported command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
