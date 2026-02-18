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

# DESIGN_TRACE:
# - Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md (§5 S2a/S2b/S2c)
# - Governance/SpiralRoadmap/S2C-EXECUTION-CARD.md (§4 run, §5 test, §8 硬门禁)
DESIGN_TRACE = {
    "s0_s2_roadmap": "Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md",
    "s2c_execution_card": "Governance/SpiralRoadmap/S2C-EXECUTION-CARD.md",
}


@dataclass(frozen=True)
class RecommendRunResult:
    trade_date: str
    mode: str
    evidence_lane: str
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


def _resolve_s2c_artifacts_dir(*, trade_date: str, evidence_lane: str) -> Path:
    if evidence_lane == "release":
        return Path("artifacts") / "spiral-s2c" / trade_date
    if evidence_lane == "debug":
        return Path("artifacts") / "spiral-s2c-debug" / trade_date
    raise ValueError(f"unsupported evidence_lane: {evidence_lane}")


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
    connection: duckdb.DuckDBPyConnection, table_name: str, column_name: str
) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = ? AND column_name = ?",
        [table_name, column_name],
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


def _load_trade_date_table(
    *,
    database_path: Path,
    table_name: str,
    trade_date: str,
) -> tuple[pd.DataFrame, bool]:
    if not database_path.exists():
        return (pd.DataFrame.from_records([]), False)
    with duckdb.connect(str(database_path), read_only=True) as connection:
        if not _table_exists(connection, table_name):
            return (pd.DataFrame.from_records([]), False)
        order_by = (
            " ORDER BY created_at DESC"
            if _column_exists(connection, table_name, "created_at")
            else ""
        )
        frame = connection.execute(
            f"SELECT * FROM {table_name} WHERE trade_date = ?{order_by}",
            [trade_date],
        ).df()
    return (frame, True)


def _materialize_s2c_bridge_samples(
    *,
    database_path: Path,
    parquet_root: Path,
    trade_date: str,
    artifacts_dir: Path,
) -> tuple[int, list[str]]:
    mss_frame, has_mss_table = _load_trade_date_table(
        database_path=database_path,
        table_name="mss_factor_intermediate",
        trade_date=trade_date,
    )
    validation_frame, has_validation_table = _load_trade_date_table(
        database_path=database_path,
        table_name="validation_gate_decision",
        trade_date=trade_date,
    )
    if mss_frame.empty:
        mss_parquet_path = parquet_root / "mss_factor_intermediate.parquet"
        if mss_parquet_path.exists():
            mss_parquet_frame = pd.read_parquet(mss_parquet_path)
            if "trade_date" in mss_parquet_frame.columns:
                mss_frame = mss_parquet_frame[
                    mss_parquet_frame["trade_date"].astype(str) == trade_date
                ].reset_index(drop=True)
    if validation_frame.empty:
        validation_parquet_path = parquet_root / "validation_gate_decision.parquet"
        if validation_parquet_path.exists():
            validation_parquet_frame = pd.read_parquet(validation_parquet_path)
            if "trade_date" in validation_parquet_frame.columns:
                validation_frame = validation_parquet_frame[
                    validation_parquet_frame["trade_date"].astype(str) == trade_date
                ].reset_index(drop=True)

    mss_sample_path = artifacts_dir / "mss_factor_intermediate_sample.parquet"
    validation_sample_path = artifacts_dir / "validation_gate_decision_sample.parquet"
    mss_frame.to_parquet(mss_sample_path, index=False)
    validation_frame.to_parquet(validation_sample_path, index=False)

    violations: list[str] = []
    if not has_mss_table and mss_frame.empty:
        violations.append("mss_factor_intermediate_source_missing")
    elif mss_frame.empty:
        violations.append("mss_factor_intermediate_empty_for_trade_date")

    if not has_validation_table and validation_frame.empty:
        violations.append("validation_gate_decision_source_missing")
    elif validation_frame.empty:
        violations.append("validation_gate_decision_empty_for_trade_date")

    return (int(len(validation_frame)), violations)


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
        "# S2 Quality Gate Report",
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
    s2c_artifacts_dir: Path | None = None,
    evidence_lane: str = "release",
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
        irs_result = run_irs_daily(
            trade_date=trade_date,
            config=config,
            artifacts_dir=s2c_artifacts_dir,
        )
        pas_result = run_pas_daily(
            trade_date=trade_date,
            config=config,
            artifacts_dir=s2c_artifacts_dir,
        )
        irs_count = irs_result.count
        pas_count = pas_result.count

        mss_exists = _has_mss_for_trade_date(database_path, trade_date)
        validation_result = run_validation_gate(
            trade_date=trade_date,
            config=config,
            irs_count=irs_count,
            pas_count=pas_count,
            mss_exists=mss_exists,
            artifacts_dir=s2c_artifacts_dir,
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
        evidence_lane=evidence_lane,
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
    with_validation_bridge: bool,
    config: Config,
    evidence_lane: str,
) -> RecommendRunResult:
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    artifacts_dir = (
        _resolve_s2c_artifacts_dir(trade_date=trade_date, evidence_lane=evidence_lane)
        if with_validation_bridge
        else Path("artifacts") / "spiral-s2b" / trade_date
    )
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
                s2c_artifacts_dir=artifacts_dir if with_validation_bridge else None,
                evidence_lane=evidence_lane,
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
            with_validation_bridge=with_validation_bridge,
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
        if with_validation_bridge:
            validation_count, sample_violations = _materialize_s2c_bridge_samples(
                database_path=database_path,
                parquet_root=parquet_root,
                trade_date=trade_date,
                artifacts_dir=artifacts_dir,
            )
            for item in sample_violations:
                add_error("P0", "s2c_bridge_samples", item)

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
        if with_validation_bridge:
            pd.DataFrame.from_records([]).to_parquet(
                artifacts_dir / "mss_factor_intermediate_sample.parquet",
                index=False,
            )
            pd.DataFrame.from_records([]).to_parquet(validation_sample_path, index=False)
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
        evidence_lane=evidence_lane,
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
    with_validation_bridge: bool = False,
    evidence_lane: str = "release",
    config: Config,
) -> RecommendRunResult:
    if evidence_lane not in {"release", "debug"}:
        raise ValueError(f"unsupported evidence_lane: {evidence_lane}")

    if mode == "mss_irs_pas":
        return _run_s2a(
            trade_date=trade_date,
            with_validation=with_validation,
            config=config,
            evidence_lane=evidence_lane,
        )
    if mode == "integrated":
        return _run_s2b(
            trade_date=trade_date,
            with_validation=with_validation,
            with_validation_bridge=with_validation_bridge,
            evidence_lane=evidence_lane,
            config=config,
        )
    raise ValueError(f"unsupported mode for current stage: {mode}")
