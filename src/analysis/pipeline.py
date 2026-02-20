from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config

# DESIGN_TRACE:
# - Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md (§5 S3b)
# - Governance/SpiralRoadmap/S3B-EXECUTION-CARD.md (§1 目标, §4 artifact)
# - docs/design/core-infrastructure/analysis/analysis-algorithm.md (§1, §4, §6)
DESIGN_TRACE = {
    "s3a_s4b_roadmap": "Governance/SpiralRoadmap/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md",
    "s3b_execution_card": "Governance/SpiralRoadmap/S3B-EXECUTION-CARD.md",
    "analysis_algorithm_design": "docs/design/core-infrastructure/analysis/analysis-algorithm.md",
}

SUPPORTED_DEVIATION_MODE = {"live-backtest"}


@dataclass(frozen=True)
class AnalysisRunResult:
    trade_date: str
    start_date: str
    end_date: str
    artifacts_dir: Path
    ab_benchmark_report_path: Path
    live_backtest_deviation_report_path: Path
    attribution_summary_path: Path
    consumption_path: Path
    gate_report_path: Path
    error_manifest_path: Path
    quality_status: str
    go_nogo: str
    has_error: bool


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validate_trade_date(value: str) -> None:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"invalid trade date: {value}; expected YYYYMMDD") from exc


def _validate_date_range(start_date: str, end_date: str) -> None:
    _validate_trade_date(start_date)
    _validate_trade_date(end_date)
    start_dt = datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    if end_dt < start_dt:
        raise ValueError(f"end date must be >= start date: start={start_date}, end={end_date}")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _safe_mean(values: pd.Series | list[float]) -> float:
    if isinstance(values, list):
        series = pd.Series(values, dtype="float64")
    else:
        series = pd.to_numeric(values, errors="coerce")
    if series.empty:
        return 0.0
    non_null = series.dropna()
    if non_null.empty:
        return 0.0
    return float(non_null.mean())


def _trim_by_quantile(values: list[float], quantile: float) -> list[float]:
    if not values:
        return []
    if quantile <= 0.0 or quantile >= 0.5:
        return values
    series = pd.Series(values, dtype="float64").dropna()
    if series.empty:
        return []
    lower = float(series.quantile(quantile))
    upper = float(series.quantile(1.0 - quantile))
    trimmed = series[(series >= lower) & (series <= upper)]
    return [float(v) for v in trimmed.tolist()]


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _table_has_column(
    connection: duckdb.DuckDBPyConnection, table_name: str, column_name: str
) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = ? AND column_name = ?",
        [table_name, column_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _persist_trade_date_table(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
    trade_date: str,
) -> None:
    with duckdb.connect(str(database_path)) as connection:
        connection.register("incoming_df", frame)
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM incoming_df WHERE 1=0"
        )
        connection.execute(f"DELETE FROM {table_name} WHERE trade_date = ?", [trade_date])
        connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_df")
        connection.unregister("incoming_df")


def _persist_metric_date_table(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
    metric_date: str,
) -> None:
    with duckdb.connect(str(database_path)) as connection:
        connection.register("incoming_df", frame)
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM incoming_df WHERE 1=0"
        )
        connection.execute(f"DELETE FROM {table_name} WHERE metric_date = ?", [metric_date])
        connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_df")
        connection.unregister("incoming_df")


def run_analysis(
    *,
    config: Config,
    start_date: str = "",
    end_date: str = "",
    trade_date: str = "",
    run_ab_benchmark: bool = False,
    deviation_mode: str = "",
    run_attribution_summary: bool = False,
) -> AnalysisRunResult:
    selected_tasks = [
        run_ab_benchmark,
        bool(deviation_mode),
        run_attribution_summary,
    ]
    if not any(selected_tasks):
        raise ValueError("analysis requires at least one task: --ab-benchmark / --deviation / --attribution-summary")

    if run_ab_benchmark:
        if not start_date or not end_date:
            raise ValueError("analysis --ab-benchmark requires --start and --end")
        _validate_date_range(start_date, end_date)

    if deviation_mode:
        normalized_mode = str(deviation_mode).strip().lower()
        if normalized_mode not in SUPPORTED_DEVIATION_MODE:
            raise ValueError(
                f"unsupported deviation mode: {deviation_mode}; supported={sorted(SUPPORTED_DEVIATION_MODE)}"
            )
        if not trade_date:
            raise ValueError("analysis --deviation requires --date")
        _validate_trade_date(trade_date)

    if run_attribution_summary:
        if not trade_date:
            raise ValueError("analysis --attribution-summary requires --date")
        _validate_trade_date(trade_date)

    anchor_date = trade_date or end_date or start_date
    if not anchor_date:
        anchor_date = datetime.now(timezone.utc).strftime("%Y%m%d")

    artifacts_dir = Path("artifacts") / "spiral-s3b" / anchor_date
    ab_report_path = artifacts_dir / "ab_benchmark_report.md"
    deviation_report_path = artifacts_dir / "live_backtest_deviation_report.md"
    attribution_path = artifacts_dir / "attribution_summary.json"
    consumption_path = artifacts_dir / "consumption.md"
    gate_report_path = artifacts_dir / "gate_report.md"
    error_manifest_path = artifacts_dir / "error_manifest_sample.json"

    errors: list[dict[str, str]] = []
    warnings: list[str] = []

    def add_error(level: str, step: str, message: str) -> None:
        errors.append(
            {
                "error_level": level,
                "step": step,
                "trade_date": trade_date or anchor_date,
                "message": message,
            }
        )

    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not db_path.exists():
        add_error("P0", "database", "duckdb_not_found")

    created_at = _utc_now_text()

    ab_payload: dict[str, Any] = {}
    performance_metrics_frame = _empty_frame(
        [
            "metric_date",
            "total_return",
            "annual_return",
            "max_drawdown",
            "volatility",
            "sharpe_ratio",
            "sortino_ratio",
            "calmar_ratio",
            "win_rate",
            "profit_factor",
            "total_trades",
            "avg_holding_days",
            "created_at",
        ]
    )

    deviation_payload: dict[str, Any] = {}
    deviation_frame = _empty_frame(
        [
            "trade_date",
            "signal_deviation",
            "execution_deviation",
            "cost_deviation",
            "total_deviation",
            "dominant_component",
            "created_at",
        ]
    )

    attribution_payload: dict[str, Any] = {}
    attribution_frame = _empty_frame(
        [
            "trade_date",
            "mss_attribution",
            "irs_attribution",
            "pas_attribution",
            "sample_count",
            "raw_sample_count",
            "trimmed_sample_count",
            "trim_ratio",
            "attribution_method",
            "created_at",
        ]
    )

    if not errors:
        with duckdb.connect(str(db_path), read_only=True) as connection:
            if run_ab_benchmark:
                if not _table_exists(connection, "backtest_results"):
                    add_error("P0", "ab_benchmark", "backtest_results_missing")
                else:
                    result_row = connection.execute(
                        "SELECT backtest_id, total_return, max_drawdown, win_rate, total_trades "
                        "FROM backtest_results "
                        "WHERE start_date >= ? AND end_date <= ? "
                        "ORDER BY end_date DESC, created_at DESC LIMIT 1",
                        [start_date, end_date],
                    ).fetchone()
                    if result_row is None:
                        add_error("P0", "ab_benchmark", "backtest_results_not_found_in_window")
                    else:
                        backtest_id = str(result_row[0])
                        total_return = float(result_row[1] or 0.0)
                        max_drawdown = float(result_row[2] or 0.0)
                        win_rate = float(result_row[3] or 0.0)
                        total_trades = int(result_row[4] or 0)

                        if _table_exists(connection, "integrated_recommendation"):
                            score_frame = connection.execute(
                                "SELECT mss_score, irs_score, pas_score "
                                "FROM integrated_recommendation "
                                "WHERE trade_date >= ? AND trade_date <= ?",
                                [start_date, end_date],
                            ).df()
                        else:
                            score_frame = _empty_frame(["mss_score", "irs_score", "pas_score"])
                            warnings.append("integrated_recommendation_missing_for_ab_proxy")

                        b_proxy = 0.0
                        c_proxy = 0.0
                        if not score_frame.empty:
                            b_proxy = round((_safe_mean(score_frame["mss_score"]) - 50.0) / 500.0, 8)
                            c_proxy = round((_safe_mean(score_frame["pas_score"]) - 50.0) / 600.0, 8)

                        conclusion = "A_dominant" if total_return >= max(b_proxy, c_proxy) else "A_not_dominant"
                        ab_payload = {
                            "backtest_id": backtest_id,
                            "start_date": start_date,
                            "end_date": end_date,
                            "a_sentiment_main_total_return": round(total_return, 8),
                            "b_baseline_mss_proxy_return": b_proxy,
                            "c_control_pas_proxy_return": c_proxy,
                            "conclusion": conclusion,
                        }
                        performance_metrics_frame = pd.DataFrame.from_records(
                            [
                                {
                                    "metric_date": end_date,
                                    "total_return": round(total_return, 8),
                                    "annual_return": 0.0,
                                    "max_drawdown": round(max_drawdown, 8),
                                    "volatility": 0.0,
                                    "sharpe_ratio": 0.0,
                                    "sortino_ratio": 0.0,
                                    "calmar_ratio": 0.0,
                                    "win_rate": round(win_rate, 8),
                                    "profit_factor": 0.0,
                                    "total_trades": total_trades,
                                    "avg_holding_days": 0.0,
                                    "created_at": created_at,
                                }
                            ]
                        )

            if deviation_mode:
                if not _table_exists(connection, "trade_records"):
                    add_error("P0", "deviation", "trade_records_missing")
                elif not _table_exists(connection, "backtest_trade_records"):
                    add_error("P0", "deviation", "backtest_trade_records_missing")
                elif not _table_exists(connection, "integrated_recommendation"):
                    add_error("P0", "deviation", "integrated_recommendation_missing")
                else:
                    live_frame = connection.execute(
                        "SELECT tr.stock_code, tr.price AS filled_price, tr.amount, tr.total_fee, "
                        "ir.entry, ir.final_score "
                        "FROM trade_records tr "
                        "LEFT JOIN integrated_recommendation ir "
                        "ON tr.trade_date = ir.trade_date AND tr.stock_code = ir.stock_code "
                        "WHERE tr.trade_date = ? AND tr.status = 'filled' AND tr.direction = 'buy' "
                        "ORDER BY tr.stock_code",
                        [trade_date],
                    ).df()
                    bt_frame = connection.execute(
                        "SELECT bt.stock_code, bt.filled_price, bt.amount, bt.final_score, ir.entry "
                        "FROM backtest_trade_records bt "
                        "LEFT JOIN integrated_recommendation ir "
                        "ON bt.signal_date = ir.trade_date AND bt.stock_code = ir.stock_code "
                        "WHERE bt.trade_date = ? AND bt.status = 'filled' AND bt.direction = 'buy' "
                        "ORDER BY bt.stock_code",
                        [trade_date],
                    ).df()

                    if live_frame.empty:
                        add_error("P1", "deviation", "live_trade_records_empty_for_trade_date")
                    if bt_frame.empty:
                        add_error("P1", "deviation", "backtest_trade_records_empty_for_trade_date")

                    live_exec = pd.to_numeric(
                        (live_frame["filled_price"] - live_frame["entry"]) / live_frame["entry"],
                        errors="coerce",
                    ) if not live_frame.empty else pd.Series(dtype="float64")
                    bt_exec = pd.to_numeric(
                        (bt_frame["filled_price"] - bt_frame["entry"]) / bt_frame["entry"],
                        errors="coerce",
                    ) if not bt_frame.empty else pd.Series(dtype="float64")

                    live_exec_mean = _safe_mean(live_exec)
                    bt_exec_mean = _safe_mean(bt_exec)
                    execution_deviation = round(live_exec_mean - bt_exec_mean, 8)

                    live_signal_mean = _safe_mean(live_frame["final_score"]) if not live_frame.empty else 0.0
                    bt_signal_mean = _safe_mean(bt_frame["final_score"]) if not bt_frame.empty else 0.0
                    signal_deviation = round((live_signal_mean - bt_signal_mean) / 100.0, 8)

                    live_cost_rate = _safe_mean(
                        pd.to_numeric(live_frame["total_fee"] / live_frame["amount"], errors="coerce")
                    ) if not live_frame.empty else 0.0
                    bt_cost_rate = 0.0
                    cost_deviation = round(live_cost_rate - bt_cost_rate, 8)

                    total_deviation = round(signal_deviation + execution_deviation - cost_deviation, 8)
                    dominant_component = max(
                        {
                            "signal": abs(signal_deviation),
                            "execution": abs(execution_deviation),
                            "cost": abs(cost_deviation),
                        },
                        key=lambda item: {
                            "signal": abs(signal_deviation),
                            "execution": abs(execution_deviation),
                            "cost": abs(cost_deviation),
                        }[item],
                    )

                    deviation_payload = {
                        "trade_date": trade_date,
                        "signal_deviation": signal_deviation,
                        "execution_deviation": execution_deviation,
                        "cost_deviation": cost_deviation,
                        "total_deviation": total_deviation,
                        "dominant_component": dominant_component,
                    }
                    deviation_frame = pd.DataFrame.from_records(
                        [
                            deviation_payload | {"created_at": created_at},
                        ]
                    )
                    if live_frame.empty or bt_frame.empty:
                        warnings.append("deviation_based_on_partial_samples")

            if run_attribution_summary:
                if not _table_exists(connection, "trade_records"):
                    add_error("P0", "attribution", "trade_records_missing")
                elif not _table_exists(connection, "integrated_recommendation"):
                    add_error("P0", "attribution", "integrated_recommendation_missing")
                else:
                    joined = connection.execute(
                        "SELECT tr.stock_code, tr.price AS filled_price, tr.amount, tr.total_fee, "
                        "ir.entry, ir.mss_score, ir.irs_score, ir.pas_score "
                        "FROM trade_records tr "
                        "LEFT JOIN integrated_recommendation ir "
                        "ON tr.trade_date = ir.trade_date AND tr.stock_code = ir.stock_code "
                        "WHERE tr.trade_date = ? AND tr.status = 'filled' AND tr.direction = 'buy' "
                        "ORDER BY tr.stock_code",
                        [trade_date],
                    ).df()
                    if joined.empty:
                        add_error("P1", "attribution", "no_filled_trade_for_attribution")
                    else:
                        exec_dev_series = pd.to_numeric(
                            (joined["filled_price"] - joined["entry"]) / joined["entry"],
                            errors="coerce",
                        ).fillna(0.0)

                        mss_contrib = [
                            float(pd.to_numeric([row[0]], errors="coerce")[0] or 0.0) * float(exec_dev)
                            for row, exec_dev in zip(joined[["mss_score"]].itertuples(index=False), exec_dev_series.tolist())
                        ]
                        irs_contrib = [
                            float(pd.to_numeric([row[0]], errors="coerce")[0] or 0.0) * float(exec_dev)
                            for row, exec_dev in zip(joined[["irs_score"]].itertuples(index=False), exec_dev_series.tolist())
                        ]
                        pas_contrib = [
                            float(pd.to_numeric([row[0]], errors="coerce")[0] or 0.0) * float(exec_dev)
                            for row, exec_dev in zip(joined[["pas_score"]].itertuples(index=False), exec_dev_series.tolist())
                        ]

                        raw_sample_count = len(mss_contrib)
                        if raw_sample_count < 20:
                            trimmed_mss = mss_contrib
                            trimmed_irs = irs_contrib
                            trimmed_pas = pas_contrib
                            method = "mean_fallback_small_sample"
                            warnings.append("attribution_small_sample_fallback")
                        else:
                            trimmed_mss = _trim_by_quantile(mss_contrib, 0.05)
                            trimmed_irs = _trim_by_quantile(irs_contrib, 0.05)
                            trimmed_pas = _trim_by_quantile(pas_contrib, 0.05)
                            method = "trimmed_mean_q0.05"

                        sample_count = len(trimmed_mss)
                        trim_ratio = 1.0 - (sample_count / max(raw_sample_count, 1))
                        attribution_payload = {
                            "trade_date": trade_date,
                            "mss_attribution": round(_safe_mean(trimmed_mss), 8),
                            "irs_attribution": round(_safe_mean(trimmed_irs), 8),
                            "pas_attribution": round(_safe_mean(trimmed_pas), 8),
                            "sample_count": sample_count,
                            "raw_sample_count": raw_sample_count,
                            "trimmed_sample_count": sample_count,
                            "trim_ratio": round(trim_ratio, 8),
                            "attribution_method": method,
                        }
                        attribution_frame = pd.DataFrame.from_records(
                            [attribution_payload | {"created_at": created_at}]
                        )

    quality_status = "PASS"
    go_nogo = "GO"
    if errors:
        quality_status = "FAIL"
        go_nogo = "NO_GO"
    elif warnings:
        quality_status = "WARN"

    artifacts_dir.mkdir(parents=True, exist_ok=True)

    if run_ab_benchmark:
        _write_markdown(
            ab_report_path,
            [
                "# S3b A/B/C Benchmark Report",
                "",
                f"- start_date: {start_date}",
                f"- end_date: {end_date}",
                f"- backtest_id: {ab_payload.get('backtest_id', '')}",
                f"- A_sentiment_main_total_return: {ab_payload.get('a_sentiment_main_total_return', 0.0)}",
                f"- B_baseline_mss_proxy_return: {ab_payload.get('b_baseline_mss_proxy_return', 0.0)}",
                f"- C_control_pas_proxy_return: {ab_payload.get('c_control_pas_proxy_return', 0.0)}",
                f"- conclusion: {ab_payload.get('conclusion', 'unknown')}",
                "",
            ],
        )

    if deviation_mode:
        _write_markdown(
            deviation_report_path,
            [
                "# S3b Live Backtest Deviation Report",
                "",
                f"- trade_date: {trade_date}",
                f"- signal_deviation: {deviation_payload.get('signal_deviation', 0.0)}",
                f"- execution_deviation: {deviation_payload.get('execution_deviation', 0.0)}",
                f"- cost_deviation: {deviation_payload.get('cost_deviation', 0.0)}",
                f"- total_deviation: {deviation_payload.get('total_deviation', 0.0)}",
                f"- dominant_component: {deviation_payload.get('dominant_component', 'unknown')}",
                "",
            ],
        )

    if run_attribution_summary:
        _write_json(
            attribution_path,
            attribution_payload
            | {
                "created_at": created_at,
            },
        )

    _write_markdown(
        consumption_path,
        [
            "# S3b Consumption Record",
            "",
            f"- run_ab_benchmark: {run_ab_benchmark}",
            f"- run_deviation_mode: {deviation_mode or 'none'}",
            f"- run_attribution_summary: {run_attribution_summary}",
            f"- database_path: {db_path}",
            f"- consumption_conclusion: {'ready_for_s4b' if go_nogo == 'GO' else 'blocked'}",
            "",
        ],
    )

    _write_markdown(
        gate_report_path,
        [
            "# S3b Gate Report",
            "",
            f"- quality_status: {quality_status}",
            f"- go_nogo: {go_nogo}",
            f"- warning_count: {len(warnings)}",
            f"- error_count: {len(errors)}",
            f"- warnings: {warnings}",
            "",
        ],
    )

    _write_json(
        error_manifest_path,
        {
            "trade_date": trade_date or anchor_date,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "warnings": warnings,
            "errors": errors,
        },
    )
    if errors:
        error_manifest_path = artifacts_dir / "error_manifest.json"
        _write_json(
            error_manifest_path,
            {
                "trade_date": trade_date or anchor_date,
                "error_count": len(errors),
                "warning_count": len(warnings),
                "warnings": warnings,
                "errors": errors,
            },
        )

    if db_path.exists() and not performance_metrics_frame.empty:
        _persist_metric_date_table(
            database_path=db_path,
            table_name="performance_metrics",
            frame=performance_metrics_frame,
            metric_date=end_date,
        )
    if db_path.exists() and not deviation_frame.empty:
        _persist_trade_date_table(
            database_path=db_path,
            table_name="live_backtest_deviation",
            frame=deviation_frame,
            trade_date=trade_date,
        )
    if db_path.exists() and not attribution_frame.empty:
        _persist_trade_date_table(
            database_path=db_path,
            table_name="signal_attribution",
            frame=attribution_frame,
            trade_date=trade_date,
        )

    return AnalysisRunResult(
        trade_date=trade_date or anchor_date,
        start_date=start_date,
        end_date=end_date,
        artifacts_dir=artifacts_dir,
        ab_benchmark_report_path=ab_report_path,
        live_backtest_deviation_report_path=deviation_report_path,
        attribution_summary_path=attribution_path,
        consumption_path=consumption_path,
        gate_report_path=gate_report_path,
        error_manifest_path=error_manifest_path,
        quality_status=quality_status,
        go_nogo=go_nogo,
        has_error=bool(errors),
    )
