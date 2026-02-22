from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import duckdb

from src.backtest.pipeline import run_backtest
from src.analysis.pipeline import run_analysis
from src import __version__
from src.algorithms.irs.pipeline import run_irs_daily
from src.algorithms.mss.pipeline import run_mss_scoring
from src.algorithms.mss.probe import run_mss_probe
from src.algorithms.pas.pipeline import run_pas_daily
from src.algorithms.validation.pipeline import run_validation_gate
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
# - docs/design/core-algorithms/mss/mss-algorithm.md (§5 周期阈值模式)
# - docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md (§3 阈值, §4 输出)
# - Governance/SpiralRoadmap/S3D-EXECUTION-CARD.md (§2 run, §3 test)
# - Governance/SpiralRoadmap/S3E-EXECUTION-CARD.md (§2 run, §3 test)
DESIGN_TRACE = {
    "s0_s2_roadmap": "Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md",
    "s3a_s4b_roadmap": "Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md",
    "s3a_execution_card": "Governance/SpiralRoadmap/S3A-EXECUTION-CARD.md",
    "backtest_algorithm_design": "docs/design/core-infrastructure/backtest/backtest-algorithm.md",
    "analysis_algorithm_design": "docs/design/core-infrastructure/analysis/analysis-algorithm.md",
    "trading_algorithm_design": "docs/design/core-infrastructure/trading/trading-algorithm.md",
    "mss_algorithm_design": "docs/design/core-algorithms/mss/mss-algorithm.md",
    "validation_algorithm_design": "docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md",
    "s3d_execution_card": "Governance/SpiralRoadmap/S3D-EXECUTION-CARD.md",
    "s3e_execution_card": "Governance/SpiralRoadmap/S3E-EXECUTION-CARD.md",
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
    mss_parser.add_argument(
        "--threshold-mode",
        choices=("fixed", "adaptive"),
        default=None,
        help="MSS cycle threshold mode (S3d). Omit to keep S1a default behavior.",
    )
    irs_parser = subparsers.add_parser("irs", help="Run IRS scoring for a trade date.")
    irs_parser.add_argument("--date", required=True, help="Trade date in YYYYMMDD.")
    irs_parser.add_argument(
        "--require-sw31",
        action="store_true",
        help="Enable SW31 full coverage gate (S3c strict mode).",
    )
    pas_parser = subparsers.add_parser("pas", help="Run PAS scoring for a trade date.")
    pas_parser.add_argument("--date", required=True, help="Trade date in YYYYMMDD.")
    probe_parser = subparsers.add_parser("mss-probe", help="Run MSS-only probe on date range.")
    probe_parser.add_argument("--start", required=True, help="Start trade date in YYYYMMDD.")
    probe_parser.add_argument("--end", required=True, help="End trade date in YYYYMMDD.")
    probe_parser.add_argument(
        "--return-series-source",
        choices=("temperature_delta", "future_returns"),
        default="temperature_delta",
        help="Probe return series source (S3d: future_returns).",
    )
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
    recommend_parser.add_argument(
        "--validation-threshold-mode",
        choices=("fixed", "regime"),
        default=None,
        help="Validation threshold mode when --with-validation is enabled.",
    )
    recommend_parser.add_argument(
        "--validation-wfa",
        choices=("single-window", "dual-window"),
        default=None,
        help="Validation WFA mode when --with-validation is enabled.",
    )
    recommend_parser.add_argument(
        "--validation-export-run-manifest",
        action="store_true",
        help="Export validation run manifest when --with-validation is enabled.",
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
        default=30,
        help="Batch size by calendar days, default 30.",
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
    backtest_parser.add_argument(
        "--repair",
        choices=("s3r",),
        default=None,
        help="Run S3r repair workflow for backtest mode.",
    )
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
    validation_parser = subparsers.add_parser("validation", help="Run S3e validation pipeline.")
    validation_parser.add_argument(
        "--trade-date",
        required=True,
        help="Trade date in YYYYMMDD.",
    )
    validation_parser.add_argument(
        "--threshold-mode",
        choices=("fixed", "regime"),
        default="regime",
        help="Validation threshold mode (S3e default: regime).",
    )
    validation_parser.add_argument(
        "--wfa",
        choices=("single-window", "dual-window"),
        default="dual-window",
        help="Walk-forward mode (S3e default: dual-window).",
    )
    validation_parser.add_argument(
        "--export-run-manifest",
        action="store_true",
        help="Export validation_run_manifest sample artifact.",
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


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _count_trade_date_rows(
    *,
    database_path: Path,
    table_name: str,
    trade_date: str,
) -> int:
    if not database_path.exists():
        return 0
    with duckdb.connect(str(database_path), read_only=True) as connection:
        if not _table_exists(connection, table_name):
            return 0
        row = connection.execute(
            f"SELECT COUNT(*) FROM {table_name} WHERE CAST(trade_date AS VARCHAR) = ?",
            [trade_date],
        ).fetchone()
    return int(row[0]) if row else 0


def _resolve_validation_inputs(config: Config, trade_date: str) -> tuple[int, int, bool]:
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    irs_count = _count_trade_date_rows(
        database_path=database_path,
        table_name="irs_industry_daily",
        trade_date=trade_date,
    )
    pas_count = _count_trade_date_rows(
        database_path=database_path,
        table_name="stock_pas_daily",
        trade_date=trade_date,
    )
    mss_count = _count_trade_date_rows(
        database_path=database_path,
        table_name="mss_panorama",
        trade_date=trade_date,
    )
    return (irs_count, pas_count, mss_count > 0)


def _write_validation_gate_report(
    *,
    path: Path,
    trade_date: str,
    final_gate: str,
    threshold_mode: str,
    wfa_mode: str,
    selected_weight_plan: str,
) -> None:
    go_nogo = "GO" if final_gate in {"PASS", "WARN"} else "NO_GO"
    lines = [
        "# S3e Validation Gate Report",
        "",
        f"- trade_date: {trade_date}",
        f"- final_gate: {final_gate}",
        f"- go_nogo: {go_nogo}",
        f"- threshold_mode: {threshold_mode}",
        f"- wfa_mode: {wfa_mode}",
        f"- selected_weight_plan: {selected_weight_plan or 'none'}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_validation_consumption(
    *,
    path: Path,
    trade_date: str,
    selected_weight_plan: str,
    final_gate: str,
) -> None:
    lines = [
        "# Validation Consumption",
        "",
        "- producer: eq validation",
        "- consumer: S4b risk defense calibration",
        "- consumed_fields: final_gate,selected_weight_plan,threshold_mode,wfa_mode",
        f"- trade_date: {trade_date}",
        f"- selected_weight_plan: {selected_weight_plan or 'none'}",
        f"- final_gate: {final_gate}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_s3c_gate_report(
    *,
    path: Path,
    trade_date: str,
    require_sw31: bool,
    output_industry_count: int,
    output_has_all: bool,
    allocation_missing_count: int,
    gate_status: str,
    go_nogo: str,
    gate_reason: str,
) -> None:
    lines = [
        "# S3c Gate Report",
        "",
        f"- trade_date: {trade_date}",
        f"- require_sw31: {str(require_sw31).lower()}",
        f"- output_industry_count: {output_industry_count}",
        f"- output_has_all: {str(output_has_all).lower()}",
        f"- allocation_missing_count: {allocation_missing_count}",
        f"- gate_status: {gate_status}",
        f"- go_nogo: {go_nogo}",
        f"- gate_reason: {gate_reason}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_s3c_consumption(
    *,
    path: Path,
    trade_date: str,
    gate_status: str,
    coverage_report_path: Path,
    sw_mapping_audit_path: Path,
) -> None:
    lines = [
        "# S3c Consumption",
        "",
        "- producer: eq run --to-l2 --strict-sw31 + eq irs --require-sw31",
        "- consumer: S3d MSS adaptive calibration / S3e validation production calibration",
        "- consumed_fields: industry_snapshot_sw31, sw_mapping_audit, irs_allocation_coverage, gate_status",
        f"- trade_date: {trade_date}",
        f"- gate_status: {gate_status}",
        f"- sw_mapping_audit_path: {sw_mapping_audit_path}",
        f"- coverage_report_path: {coverage_report_path}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


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
    threshold_mode = str(args.threshold_mode or "adaptive").strip().lower() or "adaptive"
    artifacts_dir = None
    event_name = "s1a_mss"
    if args.threshold_mode is not None:
        artifacts_dir = Path("artifacts") / "spiral-s3d" / args.date
        event_name = "s3d_mss"
    print(
        json.dumps(
            {
                "event": "mss_start",
                "command": ctx.command,
                "trade_date": args.date,
                "threshold_mode": threshold_mode,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )

    try:
        result = run_mss_scoring(
            trade_date=args.date,
            config=ctx.config,
            threshold_mode=threshold_mode,
            artifacts_dir=artifacts_dir,
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    print(
        json.dumps(
            {
                "event": event_name,
                "trade_date": args.date,
                "threshold_mode": result.threshold_mode,
                "mss_panorama_count": result.mss_panorama_count,
                "artifacts_dir": str(result.artifacts_dir),
                "sample_path": str(result.sample_path),
                "factor_trace_path": str(result.factor_trace_path),
                "threshold_snapshot_path": str(result.threshold_snapshot_path),
                "adaptive_regression_path": str(result.adaptive_regression_path),
                "gate_report_path": str(result.gate_report_path),
                "consumption_path": str(result.consumption_path),
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

    artifacts_dir = Path(result.coverage_report_path).parent
    output_industry_count = int(result.count)
    output_has_all = False
    allocation_missing_count = 0
    frame = getattr(result, "frame", None)
    if frame is not None and hasattr(frame, "columns"):
        if "industry_code" in frame.columns:
            output_codes = {
                str(code).strip()
                for code in frame["industry_code"].tolist()
                if str(code).strip()
            }
            if output_codes:
                output_industry_count = len(output_codes)
            output_has_all = "ALL" in output_codes
        if "allocation_advice" in frame.columns:
            allocation_missing_count = int(
                (frame["allocation_advice"].astype(str).str.strip() == "").sum()
            )

    gate_pass = (
        (not output_has_all)
        and output_industry_count == 31
        and allocation_missing_count == 0
    ) if bool(args.require_sw31) else output_industry_count > 0
    gate_status = "PASS" if gate_pass else "FAIL"
    go_nogo = "GO" if gate_status in {"PASS", "WARN"} else "NO_GO"
    gate_reason = (
        "ok"
        if gate_pass
        else (
            f"output_industry_count={output_industry_count}, "
            f"output_has_all={str(output_has_all).lower()}, "
            f"allocation_missing_count={allocation_missing_count}"
        )
    )
    gate_report_path = artifacts_dir / "gate_report.md"
    consumption_path = artifacts_dir / "consumption.md"
    sw_mapping_audit_path = artifacts_dir / "sw_mapping_audit.md"
    _write_s3c_gate_report(
        path=gate_report_path,
        trade_date=args.date,
        require_sw31=bool(args.require_sw31),
        output_industry_count=output_industry_count,
        output_has_all=output_has_all,
        allocation_missing_count=allocation_missing_count,
        gate_status=gate_status,
        go_nogo=go_nogo,
        gate_reason=gate_reason,
    )
    _write_s3c_consumption(
        path=consumption_path,
        trade_date=args.date,
        gate_status=gate_status,
        coverage_report_path=Path(result.coverage_report_path),
        sw_mapping_audit_path=sw_mapping_audit_path,
    )

    print(
        json.dumps(
            {
                "event": "s3c_irs",
                "trade_date": args.date,
                "require_sw31": bool(args.require_sw31),
                "irs_industry_count": result.count,
                "factor_intermediate_sample_path": str(result.factor_intermediate_sample_path),
                "coverage_report_path": str(result.coverage_report_path),
                "gate_report_path": str(gate_report_path),
                "consumption_path": str(consumption_path),
                "gate_status": gate_status,
                "go_nogo": go_nogo,
                "status": "ok",
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


def _run_pas(ctx: PipelineContext, args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "event": "pas_start",
                "command": ctx.command,
                "trade_date": args.date,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    try:
        result = run_pas_daily(
            trade_date=args.date,
            config=ctx.config,
        )
    except ValueError as exc:
        print(str(exc))
        return 2

    status = "ok" if int(result.count) > 0 else "failed"
    print(
        json.dumps(
            {
                "event": "s2b_pas",
                "trade_date": args.date,
                "pas_stock_count": int(result.count),
                "factor_intermediate_sample_path": str(result.factor_intermediate_sample_path),
                "status": status,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0 if status == "ok" else 1


def _run_mss_probe(ctx: PipelineContext, args: argparse.Namespace) -> int:
    return_series_source = str(args.return_series_source or "temperature_delta").strip().lower()
    artifacts_dir = None
    event_name = "s1b_mss_probe"
    if return_series_source == "future_returns":
        artifacts_dir = Path("artifacts") / "spiral-s3d" / f"{args.start}_{args.end}"
        event_name = "s3d_mss_probe"
    print(
        json.dumps(
            {
                "event": "mss_probe_start",
                "command": ctx.command,
                "start_date": args.start,
                "end_date": args.end,
                "return_series_source": return_series_source,
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
            return_series_source=return_series_source,
            artifacts_dir=artifacts_dir,
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    print(
        json.dumps(
            {
                "event": event_name,
                "start_date": args.start,
                "end_date": args.end,
                "return_series_source": result.return_series_source,
                "artifacts_dir": str(result.artifacts_dir),
                "probe_report_path": str(result.probe_report_path),
                "consumption_case_path": str(result.consumption_case_path),
                "gate_report_path": str(result.gate_report_path),
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
                "validation_threshold_mode": str(args.validation_threshold_mode or ""),
                "validation_wfa_mode": str(args.validation_wfa or ""),
                "validation_export_run_manifest": bool(args.validation_export_run_manifest),
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
            validation_threshold_mode=str(args.validation_threshold_mode or ""),
            validation_wfa_mode=str(args.validation_wfa or ""),
            validation_export_run_manifest=bool(args.validation_export_run_manifest),
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
            repair=str(args.repair or ""),
            config=ctx.config,
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    event_name = "s3r_backtest" if str(args.repair or "") == "s3r" else "s3_backtest"
    payload = {
        "event": event_name,
        "backtest_id": result.backtest_id,
        "engine": result.engine,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "repair": result.repair,
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
    }
    performance_metrics_report_path = getattr(result, "performance_metrics_report_path", None)
    if performance_metrics_report_path is not None:
        payload["performance_metrics_report_path"] = str(performance_metrics_report_path)
    if result.s3r_patch_note_path is not None:
        payload["s3r_patch_note_path"] = str(result.s3r_patch_note_path)
    if result.s3r_delta_report_path is not None:
        payload["s3r_delta_report_path"] = str(result.s3r_delta_report_path)
    print(
        json.dumps(
            payload,
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


def _run_validation(ctx: PipelineContext, args: argparse.Namespace) -> int:
    trade_date = str(args.trade_date).strip()
    threshold_mode = str(args.threshold_mode or "regime").strip().lower() or "regime"
    wfa_mode = str(args.wfa or "dual-window").strip().lower() or "dual-window"
    artifacts_dir = Path("artifacts") / "spiral-s3e" / trade_date
    try:
        irs_count, pas_count, mss_exists = _resolve_validation_inputs(ctx.config, trade_date)
        result = run_validation_gate(
            trade_date=trade_date,
            config=ctx.config,
            irs_count=irs_count,
            pas_count=pas_count,
            mss_exists=mss_exists,
            artifacts_dir=artifacts_dir,
            threshold_mode=threshold_mode,
            wfa_mode=wfa_mode,
            export_run_manifest=bool(args.export_run_manifest),
        )
    except ValueError as exc:
        print(str(exc))
        return 2

    gate_report_path = artifacts_dir / "gate_report.md"
    consumption_path = artifacts_dir / "consumption.md"
    _write_validation_gate_report(
        path=gate_report_path,
        trade_date=trade_date,
        final_gate=result.final_gate,
        threshold_mode=result.threshold_mode,
        wfa_mode=result.wfa_mode,
        selected_weight_plan=result.selected_weight_plan,
    )
    _write_validation_consumption(
        path=consumption_path,
        trade_date=trade_date,
        selected_weight_plan=result.selected_weight_plan,
        final_gate=result.final_gate,
    )
    go_nogo = "GO" if result.final_gate in {"PASS", "WARN"} else "NO_GO"
    print(
        json.dumps(
            {
                "event": "s3e_validation",
                "trade_date": trade_date,
                "threshold_mode": result.threshold_mode,
                "wfa_mode": result.wfa_mode,
                "final_gate": result.final_gate,
                "go_nogo": go_nogo,
                "selected_weight_plan": result.selected_weight_plan,
                "factor_count": int(len(result.factor_report_frame)),
                "weight_count": int(len(result.weight_report_frame)),
                "artifacts_dir": str(artifacts_dir),
                "factor_report_sample_path": str(result.factor_report_sample_path),
                "weight_report_sample_path": str(result.weight_report_sample_path),
                "weight_plan_sample_path": str(result.weight_plan_sample_path),
                "run_manifest_sample_path": str(result.run_manifest_sample_path),
                "oos_calibration_report_path": str(result.oos_calibration_report_path),
                "gate_report_path": str(gate_report_path),
                "consumption_path": str(consumption_path),
                "status": "failed" if result.has_fail else "ok",
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 1 if result.has_fail else 0


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
    if command == "pas":
        return _run_pas(ctx, args)
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
    if command == "validation":
        return _run_validation(ctx, args)

    parser.error(f"unsupported command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
