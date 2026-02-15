from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.algorithms.mss.engine import MssInputSnapshot, MssScoreResult, calculate_mss_score
from src.config.config import Config


@dataclass(frozen=True)
class MssRunResult:
    trade_date: str
    artifacts_dir: Path
    mss_panorama_count: int
    has_error: bool
    error_manifest_path: Path
    factor_trace_path: Path
    sample_path: Path


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


def _write_factor_trace(path: Path, score: MssScoreResult) -> None:
    lines = [
        "# MSS Factor Trace",
        "",
        f"- trade_date: {score.trade_date}",
        f"- mss_score: {score.mss_score}",
        f"- mss_temperature: {score.mss_temperature}",
        f"- mss_cycle: {score.mss_cycle}",
        f"- trend: {score.trend}",
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
) -> MssRunResult:
    artifacts_dir = Path("artifacts") / "spiral-s1a" / trade_date
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    parquet_root = Path(config.parquet_path) / "l3"
    errors: list[dict[str, str]] = []
    mss_panorama_count = 0

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
                history_rows = connection.execute(
                    "SELECT mss_temperature FROM mss_panorama WHERE trade_date < ? "
                    "ORDER BY trade_date DESC LIMIT 20",
                    [trade_date],
                ).fetchall()
                history = [float(item[0]) for item in reversed(history_rows)]

        snapshot = MssInputSnapshot.from_record(snapshot_frame.iloc[0].to_dict())
        score = calculate_mss_score(snapshot, temperature_history=history)
        result_frame = pd.DataFrame.from_records([score.to_storage_record()])

        mss_panorama_count = _persist_mss_panorama(
            database_path=database_path,
            frame=result_frame,
            trade_date=trade_date,
        )
        if mss_panorama_count <= 0:
            add_error("P0", "gate", "mss_panorama_empty")

        required_fields = {"mss_score", "mss_temperature", "mss_cycle"}
        if not required_fields <= set(result_frame.columns):
            add_error("P0", "gate", "mss_panorama_required_fields_missing")

        artifacts_dir.mkdir(parents=True, exist_ok=True)
        sample_path = artifacts_dir / "mss_panorama_sample.parquet"
        result_frame.to_parquet(sample_path, index=False)

        factor_trace_path = artifacts_dir / "mss_factor_trace.md"
        _write_factor_trace(factor_trace_path, score)

        parquet_root.mkdir(parents=True, exist_ok=True)
        result_frame.to_parquet(parquet_root / "mss_panorama.parquet", index=False)
    except Exception as exc:  # pragma: no cover - validated through contract tests
        if not errors:
            add_error("P0", "run_mss_scoring", str(exc))
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        sample_path = artifacts_dir / "mss_panorama_sample.parquet"
        factor_trace_path = artifacts_dir / "mss_factor_trace.md"
        pd.DataFrame.from_records([]).to_parquet(sample_path, index=False)
        if score is None:
            factor_trace_path.write_text(
                "# MSS Factor Trace\n\n- status: FAIL\n",
                encoding="utf-8",
            )
    else:
        sample_path = artifacts_dir / "mss_panorama_sample.parquet"
        factor_trace_path = artifacts_dir / "mss_factor_trace.md"

    error_manifest_payload = {
        "trade_date": trade_date,
        "error_count": len(errors),
        "errors": errors,
    }
    sample_manifest_path = artifacts_dir / "error_manifest_sample.json"
    _write_json(sample_manifest_path, error_manifest_payload)
    if errors:
        manifest_path = artifacts_dir / "error_manifest.json"
        _write_json(manifest_path, error_manifest_payload)
    else:
        manifest_path = sample_manifest_path

    return MssRunResult(
        trade_date=trade_date,
        artifacts_dir=artifacts_dir,
        mss_panorama_count=mss_panorama_count,
        has_error=bool(errors),
        error_manifest_path=manifest_path,
        factor_trace_path=factor_trace_path,
        sample_path=sample_path,
    )
