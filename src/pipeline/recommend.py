from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.algorithms.irs.pipeline import run_irs_daily
from src.algorithms.pas.pipeline import run_pas_daily
from src.algorithms.validation.pipeline import run_validation_gate
from src.config.config import Config


@dataclass(frozen=True)
class RecommendRunResult:
    trade_date: str
    mode: str
    artifacts_dir: Path
    irs_count: int
    pas_count: int
    validation_count: int
    final_gate: str
    has_error: bool
    error_manifest_path: Path
    irs_sample_path: Path
    pas_sample_path: Path
    validation_sample_path: Path


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


def _has_mss_for_trade_date(database_path: Path, trade_date: str) -> bool:
    if not database_path.exists():
        return False
    with duckdb.connect(str(database_path), read_only=True) as connection:
        if not _table_exists(connection, "mss_panorama"):
            return False
        row = connection.execute(
            "SELECT COUNT(*) FROM mss_panorama WHERE trade_date = ?",
            [trade_date],
        ).fetchone()
    return bool(row and int(row[0]) > 0)


def run_recommendation(
    *,
    trade_date: str,
    mode: str,
    with_validation: bool,
    config: Config,
) -> RecommendRunResult:
    if mode != "mss_irs_pas":
        raise ValueError(f"unsupported mode for current stage: {mode}")
    if not with_validation:
        raise ValueError("S2a requires --with-validation")

    artifacts_dir = Path("artifacts") / "spiral-s2a" / trade_date
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    parquet_root = Path(config.parquet_path) / "l3"
    errors: list[dict[str, str]] = []
    irs_count = 0
    pas_count = 0
    validation_count = 0
    final_gate = "FAIL"

    def add_error(level: str, step: str, message: str) -> None:
        errors.append(
            {
                "error_level": level,
                "step": step,
                "trade_date": trade_date,
                "message": message,
            }
        )

    try:
        irs_result = run_irs_daily(trade_date=trade_date, config=config)
        pas_result = run_pas_daily(trade_date=trade_date, config=config)
        irs_count = irs_result.count
        pas_count = pas_result.count

        mss_exists = _has_mss_for_trade_date(database_path, trade_date)
        validation_result = run_validation_gate(
            trade_date=trade_date,
            config=config,
            irs_count=irs_count,
            pas_count=pas_count,
            mss_exists=mss_exists,
        )
        validation_count = validation_result.count
        final_gate = validation_result.final_gate

        artifacts_dir.mkdir(parents=True, exist_ok=True)
        irs_sample_path = artifacts_dir / "irs_industry_daily_sample.parquet"
        pas_sample_path = artifacts_dir / "stock_pas_daily_sample.parquet"
        validation_sample_path = artifacts_dir / "validation_gate_decision_sample.parquet"
        irs_result.frame.to_parquet(irs_sample_path, index=False)
        pas_result.frame.to_parquet(pas_sample_path, index=False)
        validation_result.frame.to_parquet(validation_sample_path, index=False)

        parquet_root.mkdir(parents=True, exist_ok=True)
        irs_result.frame.to_parquet(parquet_root / "irs_industry_daily.parquet", index=False)
        pas_result.frame.to_parquet(parquet_root / "stock_pas_daily.parquet", index=False)
        validation_result.frame.to_parquet(
            parquet_root / "validation_gate_decision.parquet",
            index=False,
        )

        if irs_count <= 0:
            add_error("P0", "gate", "irs_industry_daily_empty")
        if pas_count <= 0:
            add_error("P0", "gate", "stock_pas_daily_empty")
        if validation_count <= 0:
            add_error("P0", "gate", "validation_gate_decision_empty")
        if not mss_exists:
            add_error("P1", "gate", "mss_panorama_missing_for_trade_date")
        if final_gate == "FAIL":
            prescription = str(
                validation_result.frame.iloc[0].get("validation_prescription", "")
            ).strip()
            if not prescription:
                add_error("P0", "gate", "validation_prescription_missing_on_fail")
    except Exception as exc:  # pragma: no cover - exercised via contract tests
        if not errors:
            add_error("P0", "run_recommendation", str(exc))
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        irs_sample_path = artifacts_dir / "irs_industry_daily_sample.parquet"
        pas_sample_path = artifacts_dir / "stock_pas_daily_sample.parquet"
        validation_sample_path = artifacts_dir / "validation_gate_decision_sample.parquet"
        pd.DataFrame.from_records([]).to_parquet(irs_sample_path, index=False)
        pd.DataFrame.from_records([]).to_parquet(pas_sample_path, index=False)
        pd.DataFrame.from_records([]).to_parquet(validation_sample_path, index=False)
    else:
        irs_sample_path = artifacts_dir / "irs_industry_daily_sample.parquet"
        pas_sample_path = artifacts_dir / "stock_pas_daily_sample.parquet"
        validation_sample_path = artifacts_dir / "validation_gate_decision_sample.parquet"

    error_manifest_payload = {
        "trade_date": trade_date,
        "mode": mode,
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

    return RecommendRunResult(
        trade_date=trade_date,
        mode=mode,
        artifacts_dir=artifacts_dir,
        irs_count=irs_count,
        pas_count=pas_count,
        validation_count=validation_count,
        final_gate=final_gate,
        has_error=bool(errors),
        error_manifest_path=manifest_path,
        irs_sample_path=irs_sample_path,
        pas_sample_path=pas_sample_path,
        validation_sample_path=validation_sample_path,
    )
