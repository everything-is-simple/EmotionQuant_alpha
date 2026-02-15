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
from src.integration.pipeline import run_integrated_daily


@dataclass(frozen=True)
class RecommendRunResult:
    trade_date: str
    mode: str
    artifacts_dir: Path
    irs_count: int
    pas_count: int
    validation_count: int
    final_gate: str
    integrated_count: int
    quality_gate_status: str
    go_nogo: str
    has_error: bool
    error_manifest_path: Path
    irs_sample_path: Path
    pas_sample_path: Path
    validation_sample_path: Path
    integrated_sample_path: Path
    quality_gate_report_path: Path
    go_nogo_decision_path: Path


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


def _write_quality_gate_report(
    *,
    path: Path,
    trade_date: str,
    status: str,
    validation_gate: str,
    integrated_count: int,
    rr_filtered_count: int,
    message: str,
) -> None:
    lines = [
        "# S2b Quality Gate Report",
        "",
        f"- trade_date: {trade_date}",
        f"- status: {status}",
        f"- validation_gate: {validation_gate}",
        f"- integrated_count: {integrated_count}",
        f"- rr_filtered_count: {rr_filtered_count}",
        f"- message: {message}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_go_nogo_decision(
    *,
    path: Path,
    trade_date: str,
    go_nogo: str,
    status: str,
    reason: str,
) -> None:
    lines = [
        "# S2 Go/No-Go Decision",
        "",
        f"- trade_date: {trade_date}",
        f"- decision: {go_nogo}",
        f"- quality_gate_status: {status}",
        f"- reason: {reason}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _run_s2a(
    *,
    trade_date: str,
    with_validation: bool,
    config: Config,
) -> RecommendRunResult:
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

    irs_sample_path = artifacts_dir / "irs_industry_daily_sample.parquet"
    pas_sample_path = artifacts_dir / "stock_pas_daily_sample.parquet"
    validation_sample_path = artifacts_dir / "validation_gate_decision_sample.parquet"
    integrated_sample_path = artifacts_dir / "integrated_recommendation_sample.parquet"
    quality_gate_report_path = artifacts_dir / "quality_gate_report.md"
    go_nogo_decision_path = artifacts_dir / "s2_go_nogo_decision.md"

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
        pd.DataFrame.from_records([]).to_parquet(irs_sample_path, index=False)
        pd.DataFrame.from_records([]).to_parquet(pas_sample_path, index=False)
        pd.DataFrame.from_records([]).to_parquet(validation_sample_path, index=False)

    error_manifest_payload = {
        "trade_date": trade_date,
        "mode": "mss_irs_pas",
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
        mode="mss_irs_pas",
        artifacts_dir=artifacts_dir,
        irs_count=irs_count,
        pas_count=pas_count,
        validation_count=validation_count,
        final_gate=final_gate,
        integrated_count=0,
        quality_gate_status="",
        go_nogo="",
        has_error=bool(errors),
        error_manifest_path=manifest_path,
        irs_sample_path=irs_sample_path,
        pas_sample_path=pas_sample_path,
        validation_sample_path=validation_sample_path,
        integrated_sample_path=integrated_sample_path,
        quality_gate_report_path=quality_gate_report_path,
        go_nogo_decision_path=go_nogo_decision_path,
    )


def _run_s2b(
    *,
    trade_date: str,
    with_validation: bool,
    config: Config,
) -> RecommendRunResult:
    artifacts_dir = Path("artifacts") / "spiral-s2b" / trade_date
    parquet_root = Path(config.parquet_path) / "l3"
    errors: list[dict[str, str]] = []
    irs_count = 0
    pas_count = 0
    validation_count = 0
    final_gate = "FAIL"
    integrated_count = 0
    quality_gate_status = "FAIL"
    go_nogo = "NO_GO"

    irs_sample_path = artifacts_dir / "irs_industry_daily_sample.parquet"
    pas_sample_path = artifacts_dir / "stock_pas_daily_sample.parquet"
    validation_sample_path = artifacts_dir / "validation_gate_decision_sample.parquet"
    integrated_sample_path = artifacts_dir / "integrated_recommendation_sample.parquet"
    quality_gate_report_path = artifacts_dir / "quality_gate_report.md"
    go_nogo_decision_path = artifacts_dir / "s2_go_nogo_decision.md"

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
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        if with_validation:
            # S2b 默认消费 S2a 结果；若显式开启，则先重算 S2a 上游输入。
            upstream = _run_s2a(
                trade_date=trade_date,
                with_validation=True,
                config=config,
            )
            irs_count = upstream.irs_count
            pas_count = upstream.pas_count
            validation_count = upstream.validation_count
            final_gate = upstream.final_gate
            if upstream.has_error:
                add_error("P0", "upstream_s2a", "upstream_s2a_failed")

        integration_result = run_integrated_daily(
            trade_date=trade_date,
            config=config,
        )
        integrated_count = integration_result.count
        final_gate = integration_result.validation_gate
        quality_gate_status = integration_result.quality_status
        go_nogo = integration_result.go_nogo

        integration_result.frame.to_parquet(integrated_sample_path, index=False)
        _write_quality_gate_report(
            path=quality_gate_report_path,
            trade_date=trade_date,
            status=integration_result.quality_status,
            validation_gate=integration_result.validation_gate,
            integrated_count=integration_result.count,
            rr_filtered_count=integration_result.rr_filtered_count,
            message=integration_result.quality_message,
        )
        _write_go_nogo_decision(
            path=go_nogo_decision_path,
            trade_date=trade_date,
            go_nogo=integration_result.go_nogo,
            status=integration_result.quality_status,
            reason=integration_result.quality_message,
        )

        parquet_root.mkdir(parents=True, exist_ok=True)
        integration_result.frame.to_parquet(
            parquet_root / "integrated_recommendation.parquet",
            index=False,
        )
        integration_result.quality_frame.to_parquet(
            parquet_root / "quality_gate_report.parquet",
            index=False,
        )

        if integration_result.count <= 0:
            add_error("P0", "gate", "integrated_recommendation_empty")
        if integration_result.quality_status == "FAIL":
            add_error("P0", "gate", "quality_gate_report_fail")
        if integration_result.quality_status not in {"PASS", "WARN"}:
            add_error("P0", "gate", "quality_gate_report_status_invalid")
    except Exception as exc:  # pragma: no cover - exercised via contract tests
        if not errors:
            add_error("P0", "run_recommendation", str(exc))
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame.from_records([]).to_parquet(integrated_sample_path, index=False)
        _write_quality_gate_report(
            path=quality_gate_report_path,
            trade_date=trade_date,
            status="FAIL",
            validation_gate=final_gate,
            integrated_count=0,
            rr_filtered_count=0,
            message="exception_in_s2b_pipeline",
        )
        _write_go_nogo_decision(
            path=go_nogo_decision_path,
            trade_date=trade_date,
            go_nogo="NO_GO",
            status="FAIL",
            reason="exception_in_s2b_pipeline",
        )

    error_manifest_payload = {
        "trade_date": trade_date,
        "mode": "integrated",
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
        mode="integrated",
        artifacts_dir=artifacts_dir,
        irs_count=irs_count,
        pas_count=pas_count,
        validation_count=validation_count,
        final_gate=final_gate,
        integrated_count=integrated_count,
        quality_gate_status=quality_gate_status,
        go_nogo=go_nogo,
        has_error=bool(errors),
        error_manifest_path=manifest_path,
        irs_sample_path=irs_sample_path,
        pas_sample_path=pas_sample_path,
        validation_sample_path=validation_sample_path,
        integrated_sample_path=integrated_sample_path,
        quality_gate_report_path=quality_gate_report_path,
        go_nogo_decision_path=go_nogo_decision_path,
    )


def run_recommendation(
    *,
    trade_date: str,
    mode: str,
    with_validation: bool,
    config: Config,
) -> RecommendRunResult:
    if mode == "mss_irs_pas":
        return _run_s2a(
            trade_date=trade_date,
            with_validation=with_validation,
            config=config,
        )
    if mode == "integrated":
        return _run_s2b(
            trade_date=trade_date,
            with_validation=with_validation,
            config=config,
        )
    raise ValueError(f"unsupported mode for current stage: {mode}")
