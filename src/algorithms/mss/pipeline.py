from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.algorithms.mss.engine import (
    MssInputSnapshot,
    MssScoreResult,
    calculate_mss_score,
    resolve_cycle_thresholds,
)
from src.config.config import Config

# DESIGN_TRACE:
# - docs/design/core-algorithms/mss/mss-algorithm.md (§3, §4, §5)
# - Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md (§5 S1a)
# - Governance/SpiralRoadmap/planA/execution-cards/S1A-EXECUTION-CARD.md (§2 run, §3 test, §4 artifact)
# - Governance/SpiralRoadmap/planA/execution-cards/S2C-EXECUTION-CARD.md (§3 MSS)
DESIGN_TRACE = {
    "mss_algorithm": "docs/design/core-algorithms/mss/mss-algorithm.md",
    "s0_s2_roadmap": "Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md",
    "s1a_execution_card": "Governance/SpiralRoadmap/planA/execution-cards/S1A-EXECUTION-CARD.md",
    "s2c_execution_card": "Governance/SpiralRoadmap/planA/execution-cards/S2C-EXECUTION-CARD.md",
}


@dataclass(frozen=True)
class MssRunResult:
    trade_date: str
    artifacts_dir: Path
    mss_panorama_count: int
    threshold_mode: str
    has_error: bool
    error_manifest_path: Path
    factor_trace_path: Path
    sample_path: Path
    factor_intermediate_sample_path: Path
    threshold_snapshot_path: Path
    adaptive_regression_path: Path
    gate_report_path: Path
    consumption_path: Path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _column_exists(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    column_name: str,
) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = ? AND column_name = ?",
        [table_name, column_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _duckdb_type_from_series(series: pd.Series) -> str:
    dtype = str(series.dtype).lower()
    if "bool" in dtype:
        return "BOOLEAN"
    if "int" in dtype:
        return "BIGINT"
    if "float" in dtype:
        return "DOUBLE"
    if "datetime" in dtype:
        return "TIMESTAMP"
    return "VARCHAR"


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _build_factor_intermediate_frame(
    *,
    trade_date: str,
    snapshot: MssInputSnapshot,
    score: MssScoreResult,
) -> pd.DataFrame:
    total_stocks = max(snapshot.total_stocks, 1)
    market_coefficient_raw = _safe_ratio(snapshot.rise_count, total_stocks)
    limit_up_ratio = _safe_ratio(snapshot.limit_up_count, total_stocks)
    new_high_ratio = _safe_ratio(snapshot.new_100d_high_count, total_stocks)
    strong_up_ratio = _safe_ratio(snapshot.strong_up_count, total_stocks)
    profit_effect_raw = 0.4 * limit_up_ratio + 0.3 * new_high_ratio + 0.3 * strong_up_ratio
    broken_rate = _safe_ratio(
        max(snapshot.touched_limit_up - snapshot.limit_up_count, 0),
        max(snapshot.touched_limit_up, 1),
    )
    limit_down_ratio = _safe_ratio(snapshot.limit_down_count, total_stocks)
    strong_down_ratio = _safe_ratio(snapshot.strong_down_count, total_stocks)
    new_low_ratio = _safe_ratio(snapshot.new_100d_low_count, total_stocks)
    loss_effect_raw = (
        0.3 * broken_rate
        + 0.2 * limit_down_ratio
        + 0.3 * strong_down_ratio
        + 0.2 * new_low_ratio
    )
    continuity_limit_ratio = _safe_ratio(
        snapshot.continuous_limit_up_2d + 2 * snapshot.continuous_limit_up_3d_plus,
        max(snapshot.limit_up_count, 1),
    )
    continuity_new_high_ratio = _safe_ratio(
        snapshot.continuous_new_high_2d_plus,
        max(snapshot.new_100d_high_count, 1),
    )
    continuity_factor_raw = (
        0.5 * continuity_limit_ratio + 0.5 * continuity_new_high_ratio
    )
    panic_tail_ratio = _safe_ratio(snapshot.high_open_low_close_count, total_stocks)
    squeeze_tail_ratio = _safe_ratio(snapshot.low_open_high_close_count, total_stocks)
    extreme_factor_raw = panic_tail_ratio + squeeze_tail_ratio
    volatility_factor_raw = (
        0.5 * max(snapshot.pct_chg_std, 0.0)
        + 0.5 * max(0.0, snapshot.amount_volatility) / (max(0.0, snapshot.amount_volatility) + 1_000_000.0)
    )

    return pd.DataFrame.from_records(
        [
            {
                "trade_date": trade_date,
                "market_coefficient_raw": round(market_coefficient_raw, 6),
                "profit_effect_raw": round(profit_effect_raw, 6),
                "loss_effect_raw": round(loss_effect_raw, 6),
                "continuity_factor_raw": round(continuity_factor_raw, 6),
                "extreme_factor_raw": round(extreme_factor_raw, 6),
                "volatility_factor_raw": round(volatility_factor_raw, 6),
                "mss_market_coefficient": score.mss_market_coefficient,
                "mss_profit_effect": score.mss_profit_effect,
                "mss_loss_effect": score.mss_loss_effect,
                "mss_continuity_factor": score.mss_continuity_factor,
                "mss_extreme_factor": score.mss_extreme_factor,
                "mss_volatility_factor": score.mss_volatility_factor,
                "mss_extreme_direction_bias": score.mss_extreme_direction_bias,
                "contract_version": score.contract_version,
                "created_at": score.created_at or pd.Timestamp.utcnow().isoformat(),
            }
        ]
    )


def _write_factor_trace(path: Path, score: MssScoreResult) -> None:
    lines = [
        "# MSS Factor Trace",
        "",
        f"- trade_date: {score.trade_date}",
        f"- mss_score: {score.mss_score}",
        f"- mss_temperature: {score.mss_temperature}",
        f"- mss_cycle: {score.mss_cycle}",
        f"- trend: {score.trend}",
        f"- trend_quality: {score.trend_quality}",
        f"- rank: {score.mss_rank}",
        f"- percentile: {score.mss_percentile}",
        f"- neutrality: {score.neutrality}",
        "",
        "## Factors",
        f"- mss_market_coefficient: {score.mss_market_coefficient}",
        f"- mss_profit_effect: {score.mss_profit_effect}",
        f"- mss_loss_effect: {score.mss_loss_effect}",
        f"- mss_continuity_factor: {score.mss_continuity_factor}",
        f"- mss_extreme_factor: {score.mss_extreme_factor}",
        f"- mss_volatility_factor: {score.mss_volatility_factor}",
        f"- mss_extreme_direction_bias: {score.mss_extreme_direction_bias}",
        "",
        "## Quality",
        f"- data_quality: {score.data_quality}",
        f"- stale_days: {score.stale_days}",
        f"- source_trade_date: {score.source_trade_date}",
        f"- contract_version: {score.contract_version}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _normalize_threshold_mode(value: str) -> str:
    mode = str(value or "adaptive").strip().lower() or "adaptive"
    if mode not in {"fixed", "adaptive"}:
        raise ValueError(f"unsupported threshold_mode: {value}; allowed=['adaptive', 'fixed']")
    return mode


def _write_threshold_snapshot(
    *,
    path: Path,
    trade_date: str,
    threshold_mode: str,
    thresholds: dict[str, float],
    history_samples: int,
) -> None:
    payload = {
        "trade_date": trade_date,
        "threshold_mode": threshold_mode,
        "history_samples": int(history_samples),
        "thresholds": {
            "t30": round(float(thresholds.get("t30", 30.0)), 6),
            "t45": round(float(thresholds.get("t45", 45.0)), 6),
            "t60": round(float(thresholds.get("t60", 60.0)), 6),
            "t75": round(float(thresholds.get("t75", 75.0)), 6),
        },
    }
    _write_json(path, payload)


def _write_adaptive_regression(
    *,
    path: Path,
    trade_date: str,
    threshold_mode: str,
    score: MssScoreResult,
    thresholds: dict[str, float],
    history_samples: int,
) -> None:
    lines = [
        "# MSS Adaptive Regression",
        "",
        f"- trade_date: {trade_date}",
        f"- threshold_mode: {threshold_mode}",
        f"- history_samples: {int(history_samples)}",
        f"- trend: {score.trend}",
        f"- trend_quality: {score.trend_quality}",
        f"- mss_cycle: {score.mss_cycle}",
        f"- mss_temperature: {score.mss_temperature}",
        f"- t30: {round(float(thresholds.get('t30', 30.0)), 6)}",
        f"- t45: {round(float(thresholds.get('t45', 45.0)), 6)}",
        f"- t60: {round(float(thresholds.get('t60', 60.0)), 6)}",
        f"- t75: {round(float(thresholds.get('t75', 75.0)), 6)}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_gate_report(
    *,
    path: Path,
    trade_date: str,
    threshold_mode: str,
    mss_panorama_count: int,
    has_error: bool,
    error_messages: list[str],
) -> None:
    gate = "FAIL" if has_error else "PASS"
    lines = [
        "# MSS Gate Report",
        "",
        f"- trade_date: {trade_date}",
        f"- threshold_mode: {threshold_mode}",
        f"- gate_result: {gate}",
        f"- mss_panorama_count: {int(mss_panorama_count)}",
        "",
        "## Errors",
    ]
    if error_messages:
        lines.extend([f"- {message}" for message in error_messages])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_consumption(
    *,
    path: Path,
    trade_date: str,
    threshold_mode: str,
    score: MssScoreResult | None,
) -> None:
    cycle = score.mss_cycle if score is not None else "unknown"
    trend = score.trend if score is not None else "sideways"
    temperature = score.mss_temperature if score is not None else 0.0
    lines = [
        "# MSS Consumption",
        "",
        "- producer: eq mss",
        "- consumer: S3e validation / integration gate",
        "- consumed_fields: mss_score,mss_temperature,mss_cycle,mss_trend,mss_rank,mss_percentile",
        f"- trade_date: {trade_date}",
        f"- threshold_mode: {threshold_mode}",
        f"- mss_cycle: {cycle}",
        f"- mss_trend: {trend}",
        f"- mss_temperature: {temperature}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _persist_mss_panorama(
    *,
    database_path: Path,
    frame: pd.DataFrame,
    trade_date: str,
) -> int:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database_path)) as connection:
        connection.register("incoming_df", frame)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS mss_panorama AS "
            "SELECT * FROM incoming_df WHERE 1=0"
        )
        existing_columns = [str(item[1]) for item in connection.execute("PRAGMA table_info('mss_panorama')").fetchall()]
        for column_name in frame.columns:
            if column_name in existing_columns:
                continue
            column_type = _duckdb_type_from_series(frame[column_name])
            connection.execute(f"ALTER TABLE mss_panorama ADD COLUMN {column_name} {column_type}")
        existing_columns = [str(item[1]) for item in connection.execute("PRAGMA table_info('mss_panorama')").fetchall()]
        aligned = frame.copy()
        for column_name in existing_columns:
            if column_name not in aligned.columns:
                aligned[column_name] = None
        aligned = aligned[existing_columns]
        connection.unregister("incoming_df")
        connection.register("incoming_df", aligned)
        connection.execute(
            "DELETE FROM mss_panorama WHERE trade_date = ?",
            [trade_date],
        )
        connection.execute("INSERT INTO mss_panorama SELECT * FROM incoming_df")
        connection.unregister("incoming_df")
    return int(len(frame))


def run_mss_scoring(
    *,
    trade_date: str,
    config: Config,
    threshold_mode: str = "adaptive",
    artifacts_dir: Path | None = None,
) -> MssRunResult:
    resolved_threshold_mode = _normalize_threshold_mode(threshold_mode)
    resolved_artifacts_dir = artifacts_dir or (Path("artifacts") / "spiral-s1a" / trade_date)
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    parquet_root = Path(config.parquet_path) / "l3"
    errors: list[dict[str, str]] = []
    mss_panorama_count = 0
    thresholds_snapshot = {"t30": 30.0, "t45": 45.0, "t60": 60.0, "t75": 75.0}
    history_samples = 0

    def add_error(level: str, step: str, message: str) -> None:
        errors.append(
            {
                "error_level": level,
                "step": step,
                "trade_date": trade_date,
                "message": message,
            }
        )

    score: MssScoreResult | None = None
    factor_intermediate_sample_path = resolved_artifacts_dir / "mss_factor_intermediate_sample.parquet"
    threshold_snapshot_path = resolved_artifacts_dir / "mss_regime_thresholds_snapshot.json"
    adaptive_regression_path = resolved_artifacts_dir / "mss_adaptive_regression.md"
    gate_report_path = resolved_artifacts_dir / "gate_report.md"
    consumption_path = resolved_artifacts_dir / "consumption.md"
    try:
        if not database_path.exists():
            add_error("P0", "load_l2", "duckdb_not_found")
            raise RuntimeError("duckdb_not_found")

        with duckdb.connect(str(database_path), read_only=True) as connection:
            if not _table_exists(connection, "market_snapshot"):
                add_error("P0", "load_l2", "market_snapshot_table_missing")
                raise RuntimeError("market_snapshot_table_missing")

            snapshot_frame = connection.execute(
                "SELECT * FROM market_snapshot WHERE trade_date = ? ORDER BY created_at DESC LIMIT 1",
                [trade_date],
            ).df()
            if snapshot_frame.empty:
                add_error("P0", "load_l2", "market_snapshot_not_found")
                raise RuntimeError("market_snapshot_not_found")

            history: list[float] = []
            if _table_exists(connection, "mss_panorama"):
                history_column = (
                    "mss_temperature"
                    if _column_exists(connection, "mss_panorama", "mss_temperature")
                    else ("mss_score" if _column_exists(connection, "mss_panorama", "mss_score") else "")
                )
                if history_column:
                    history_rows = connection.execute(
                        f"SELECT {history_column} FROM mss_panorama WHERE trade_date < ? "
                        "ORDER BY trade_date DESC LIMIT 252",
                        [trade_date],
                    ).fetchall()
                    history = [float(item[0]) for item in reversed(history_rows) if item and item[0] is not None]

        snapshot = MssInputSnapshot.from_record(snapshot_frame.iloc[0].to_dict())
        history_samples = int(len(history))
        thresholds_snapshot = resolve_cycle_thresholds(
            history,
            threshold_mode=resolved_threshold_mode,
        )
        score = calculate_mss_score(
            snapshot,
            temperature_history=history,
            threshold_mode=resolved_threshold_mode,
        )
        result_frame = pd.DataFrame.from_records([score.to_storage_record()])

        mss_panorama_count = _persist_mss_panorama(
            database_path=database_path,
            frame=result_frame,
            trade_date=trade_date,
        )
        if mss_panorama_count <= 0:
            add_error("P0", "gate", "mss_panorama_empty")

        required_fields = {
            "mss_score",
            "mss_temperature",
            "mss_cycle",
            "mss_rank",
            "mss_percentile",
        }
        if not required_fields <= set(result_frame.columns):
            add_error("P0", "gate", "mss_panorama_required_fields_missing")

        resolved_artifacts_dir.mkdir(parents=True, exist_ok=True)
        sample_path = resolved_artifacts_dir / "mss_panorama_sample.parquet"
        result_frame.to_parquet(sample_path, index=False)
        factor_intermediate_frame = _build_factor_intermediate_frame(
            trade_date=trade_date,
            snapshot=snapshot,
            score=score,
        )
        factor_intermediate_frame.to_parquet(factor_intermediate_sample_path, index=False)

        factor_trace_path = resolved_artifacts_dir / "mss_factor_trace.md"
        _write_factor_trace(factor_trace_path, score)
        _write_threshold_snapshot(
            path=threshold_snapshot_path,
            trade_date=trade_date,
            threshold_mode=resolved_threshold_mode,
            thresholds=thresholds_snapshot,
            history_samples=history_samples,
        )
        _write_adaptive_regression(
            path=adaptive_regression_path,
            trade_date=trade_date,
            threshold_mode=resolved_threshold_mode,
            score=score,
            thresholds=thresholds_snapshot,
            history_samples=history_samples,
        )
        _write_consumption(
            path=consumption_path,
            trade_date=trade_date,
            threshold_mode=resolved_threshold_mode,
            score=score,
        )

        parquet_root.mkdir(parents=True, exist_ok=True)
        result_frame.to_parquet(parquet_root / "mss_panorama.parquet", index=False)
        factor_intermediate_frame.to_parquet(
            parquet_root / "mss_factor_intermediate.parquet",
            index=False,
        )
    except Exception as exc:  # pragma: no cover - validated through contract tests
        if not errors:
            add_error("P0", "run_mss_scoring", str(exc))
        resolved_artifacts_dir.mkdir(parents=True, exist_ok=True)
        sample_path = resolved_artifacts_dir / "mss_panorama_sample.parquet"
        factor_trace_path = resolved_artifacts_dir / "mss_factor_trace.md"
        pd.DataFrame.from_records([]).to_parquet(sample_path, index=False)
        pd.DataFrame.from_records([]).to_parquet(
            factor_intermediate_sample_path,
            index=False,
        )
        if score is None:
            factor_trace_path.write_text(
                "# MSS Factor Trace\n\n- status: FAIL\n",
                encoding="utf-8",
            )
        _write_threshold_snapshot(
            path=threshold_snapshot_path,
            trade_date=trade_date,
            threshold_mode=resolved_threshold_mode,
            thresholds=thresholds_snapshot,
            history_samples=history_samples,
        )
        adaptive_regression_path.write_text(
            "# MSS Adaptive Regression\n\n- status: FAIL\n",
            encoding="utf-8",
        )
        _write_consumption(
            path=consumption_path,
            trade_date=trade_date,
            threshold_mode=resolved_threshold_mode,
            score=None,
        )
    else:
        sample_path = resolved_artifacts_dir / "mss_panorama_sample.parquet"
        factor_trace_path = resolved_artifacts_dir / "mss_factor_trace.md"

    error_manifest_payload = {
        "trade_date": trade_date,
        "threshold_mode": resolved_threshold_mode,
        "error_count": len(errors),
        "errors": errors,
    }
    sample_manifest_path = resolved_artifacts_dir / "error_manifest_sample.json"
    _write_json(sample_manifest_path, error_manifest_payload)
    if errors:
        manifest_path = resolved_artifacts_dir / "error_manifest.json"
        _write_json(manifest_path, error_manifest_payload)
    else:
        manifest_path = sample_manifest_path
    _write_gate_report(
        path=gate_report_path,
        trade_date=trade_date,
        threshold_mode=resolved_threshold_mode,
        mss_panorama_count=mss_panorama_count,
        has_error=bool(errors),
        error_messages=[str(item.get("message", "")) for item in errors if str(item.get("message", "")).strip()],
    )

    return MssRunResult(
        trade_date=trade_date,
        artifacts_dir=resolved_artifacts_dir,
        mss_panorama_count=mss_panorama_count,
        threshold_mode=resolved_threshold_mode,
        has_error=bool(errors),
        error_manifest_path=manifest_path,
        factor_trace_path=factor_trace_path,
        sample_path=sample_path,
        factor_intermediate_sample_path=factor_intermediate_sample_path,
        threshold_snapshot_path=threshold_snapshot_path,
        adaptive_regression_path=adaptive_regression_path,
        gate_report_path=gate_report_path,
        consumption_path=consumption_path,
    )
