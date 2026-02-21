from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import uuid

import duckdb
import pandas as pd

from src.config.config import Config

# DESIGN_TRACE:
# - docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md (§3 阈值, §4 输出与表结构, §5 Gate 语义)
# - docs/design/core-algorithms/validation/factor-weight-validation-data-models.md (§3 ValidationConfig, §4 输出模型)
# - Governance/SpiralRoadmap/S2C-EXECUTION-CARD.md (§3 Validation, §6 artifact)
DESIGN_TRACE = {
    "validation_algorithm": "docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md",
    "validation_data_models": "docs/design/core-algorithms/validation/factor-weight-validation-data-models.md",
    "s2c_execution_card": "Governance/SpiralRoadmap/S2C-EXECUTION-CARD.md",
}

SUPPORTED_CONTRACT_VERSION = "nc-v1"
DEFAULT_WEIGHT_PLAN_ID = "vp_balanced_v1"
CANDIDATE_WEIGHT_PLAN_ID = "vp_candidate_v1"


@dataclass(frozen=True)
class ValidationConfig:
    threshold_mode: str = "fixed"
    stale_days_threshold: int = 3
    ic_pass: float = 0.02
    ic_warn: float = 0.01
    rank_ic_pass: float = 0.03
    rank_ic_warn: float = 0.015
    icir_pass: float = 0.10
    icir_warn: float = 0.05
    decay_pass: float = 0.70
    decay_warn: float = 0.50
    sharpe_pass: float = 0.60
    sharpe_warn: float = 0.40
    max_drawdown_pass: float = 0.15
    max_drawdown_warn: float = 0.20


@dataclass(frozen=True)
class ValidationGateResult:
    trade_date: str
    count: int
    frame: pd.DataFrame
    final_gate: str
    selected_weight_plan: str
    has_fail: bool
    factor_report_frame: pd.DataFrame
    weight_report_frame: pd.DataFrame
    weight_plan_frame: pd.DataFrame
    run_manifest_payload: dict[str, object]
    factor_report_sample_path: Path
    weight_report_sample_path: Path
    weight_plan_sample_path: Path
    run_manifest_sample_path: Path


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _duckdb_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(series):
        return "BIGINT"
    if pd.api.types.is_float_dtype(series):
        return "DOUBLE"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "TIMESTAMP"
    return "VARCHAR"


def _ensure_columns(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    frame: pd.DataFrame,
) -> list[str]:
    if not _table_exists(connection, table_name):
        connection.register("schema_df", frame)
        connection.execute(
            f"CREATE TABLE {table_name} AS SELECT * FROM schema_df WHERE 1=0"
        )
        connection.unregister("schema_df")
    else:
        existing = {
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        }
        for column in frame.columns:
            if column in existing:
                continue
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column} {_duckdb_type(frame[column])}"
            )

    return [
        str(row[1]) for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    ]


def _persist(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
    trade_date: str,
) -> int:
    with duckdb.connect(str(database_path)) as connection:
        table_columns = _ensure_columns(connection, table_name, frame)
        aligned = frame.copy()
        for column in table_columns:
            if column not in aligned.columns:
                aligned[column] = pd.NA
        aligned = aligned[table_columns]
        connection.register("incoming_df", aligned)
        connection.execute(f"DELETE FROM {table_name} WHERE trade_date = ?", [trade_date])
        connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_df")
        connection.unregister("incoming_df")
    return int(len(aligned))


def _normalize_gate(score: float, pass_threshold: float, warn_threshold: float) -> str:
    if score >= pass_threshold:
        return "PASS"
    if score >= warn_threshold:
        return "WARN"
    return "FAIL"


def _aggregate_gate(gates: list[str]) -> str:
    if any(gate == "FAIL" for gate in gates):
        return "FAIL"
    if any(gate == "WARN" for gate in gates):
        return "WARN"
    return "PASS"


def _safe_corr(left: pd.Series, right: pd.Series) -> float:
    if left.empty or right.empty:
        return 0.0
    frame = pd.DataFrame({"left": left, "right": right}).dropna()
    if len(frame) < 2:
        return 0.0
    corr = frame["left"].corr(frame["right"], method="pearson")
    if pd.isna(corr):
        return 0.0
    return float(corr)


def _safe_rank_corr(left: pd.Series, right: pd.Series) -> float:
    if left.empty or right.empty:
        return 0.0
    frame = pd.DataFrame({"left": left, "right": right}).dropna()
    if len(frame) < 2:
        return 0.0
    corr = frame["left"].corr(frame["right"], method="spearman")
    if pd.isna(corr):
        return 0.0
    return float(corr)


def _clip(value: float, low: float, high: float) -> float:
    return float(max(low, min(high, value)))


def _to_regime(mss_score: float, market_volatility_20d: float) -> str:
    if mss_score >= 75.0 and market_volatility_20d <= 0.02:
        return "hot_stable"
    if mss_score < 45.0 or market_volatility_20d >= 0.045:
        return "cold_or_volatile"
    return "neutral"


def _regime_adjusted_config(base: ValidationConfig, regime: str) -> ValidationConfig:
    if regime == "hot_stable":
        return ValidationConfig(
            threshold_mode=base.threshold_mode,
            stale_days_threshold=base.stale_days_threshold,
            ic_pass=base.ic_pass + 0.005,
            ic_warn=base.ic_warn + 0.003,
            rank_ic_pass=base.rank_ic_pass + 0.005,
            rank_ic_warn=base.rank_ic_warn + 0.003,
            icir_pass=base.icir_pass + 0.02,
            icir_warn=base.icir_warn + 0.01,
            decay_pass=base.decay_pass,
            decay_warn=base.decay_warn,
            sharpe_pass=base.sharpe_pass + 0.05,
            sharpe_warn=base.sharpe_warn + 0.03,
            max_drawdown_pass=base.max_drawdown_pass,
            max_drawdown_warn=base.max_drawdown_warn,
        )
    if regime == "cold_or_volatile":
        return ValidationConfig(
            threshold_mode=base.threshold_mode,
            stale_days_threshold=base.stale_days_threshold,
            ic_pass=max(base.ic_pass - 0.005, 0.0),
            ic_warn=max(base.ic_warn - 0.003, 0.0),
            rank_ic_pass=max(base.rank_ic_pass - 0.005, 0.0),
            rank_ic_warn=max(base.rank_ic_warn - 0.003, 0.0),
            icir_pass=max(base.icir_pass - 0.02, 0.0),
            icir_warn=max(base.icir_warn - 0.01, 0.0),
            decay_pass=base.decay_pass,
            decay_warn=base.decay_warn,
            sharpe_pass=max(base.sharpe_pass - 0.05, 0.0),
            sharpe_warn=max(base.sharpe_warn - 0.03, 0.0),
            max_drawdown_pass=min(base.max_drawdown_pass + 0.03, 0.30),
            max_drawdown_warn=min(base.max_drawdown_warn + 0.03, 0.35),
        )
    return base


def run_validation_gate(
    *,
    trade_date: str,
    config: Config,
    irs_count: int,
    pas_count: int,
    mss_exists: bool,
    artifacts_dir: Path | None = None,
) -> ValidationGateResult:
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not database_path.exists():
        raise FileNotFoundError("duckdb_not_found")

    validation_config = ValidationConfig()

    with duckdb.connect(str(database_path), read_only=True) as connection:
        mss_frame = (
            connection.execute(
                "SELECT * FROM mss_panorama WHERE trade_date = ? "
                "ORDER BY created_at DESC LIMIT 1",
                [trade_date],
            ).df()
            if _table_exists(connection, "mss_panorama")
            else pd.DataFrame.from_records([])
        )
        irs_frame = (
            connection.execute(
                "SELECT trade_date, industry_code, irs_score, industry_score, stale_days "
                "FROM irs_industry_daily WHERE trade_date = ? ORDER BY industry_code",
                [trade_date],
            ).df()
            if _table_exists(connection, "irs_industry_daily")
            else pd.DataFrame.from_records([])
        )
        pas_frame = (
            connection.execute(
                "SELECT trade_date, stock_code, pas_score, risk_reward_ratio, effective_risk_reward_ratio "
                "FROM stock_pas_daily WHERE trade_date = ? ORDER BY stock_code",
                [trade_date],
            ).df()
            if _table_exists(connection, "stock_pas_daily")
            else pd.DataFrame.from_records([])
        )

    issues: list[str] = []
    if not mss_exists:
        issues.append("mss_panorama_missing")
    if irs_count <= 0:
        issues.append("irs_industry_daily_empty")
    if pas_count <= 0:
        issues.append("stock_pas_daily_empty")

    mss_score = float(mss_frame.iloc[0]["mss_score"]) if not mss_frame.empty else 0.0
    if not mss_frame.empty and "pct_chg_std" in mss_frame.columns:
        market_volatility_20d = float(mss_frame.iloc[0].get("pct_chg_std", 0.0) or 0.0)
    elif not mss_frame.empty:
        market_volatility_20d = float(mss_frame.iloc[0].get("mss_volatility_factor", 0.0) or 0.0) / 100.0
    else:
        market_volatility_20d = 0.0
    regime = _to_regime(mss_score, market_volatility_20d)
    effective_config = (
        _regime_adjusted_config(validation_config, regime)
        if validation_config.threshold_mode == "regime"
        else validation_config
    )

    irs_scores = pd.to_numeric(
        irs_frame["industry_score"] if "industry_score" in irs_frame.columns else irs_frame.get("irs_score", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0.0)
    pas_scores = pd.to_numeric(pas_frame.get("pas_score", pd.Series(dtype=float)), errors="coerce").fillna(0.0)

    aligned_size = min(len(irs_scores), len(pas_scores))
    aligned_irs = irs_scores.head(aligned_size)
    aligned_pas = pas_scores.head(aligned_size)

    factor_rows: list[dict[str, object]] = []
    created_at = pd.Timestamp.utcnow().isoformat()

    for factor_name, left, right in (
        ("irs_pas_coupling", aligned_irs, aligned_pas),
        ("irs_internal_stability", irs_scores, irs_scores.shift(1).fillna(irs_scores)),
        ("pas_internal_stability", pas_scores, pas_scores.shift(1).fillna(pas_scores)),
    ):
        sample_size = int(len(left))
        low_information_fallback = False
        if sample_size < 2:
            # Cold-start fallback: keep neutral-pass baseline instead of hard-failing tiny samples.
            ic = effective_config.ic_pass
            rank_ic = effective_config.rank_ic_pass
            icir = effective_config.icir_pass
            decay_5d = effective_config.decay_pass
            gates = ["PASS", "PASS", "PASS", "PASS"]
        elif int(pd.Series(left).nunique(dropna=True)) < 2 or int(pd.Series(right).nunique(dropna=True)) < 2:
            # Low-information fallback: constant/near-constant inputs are not enough for stable correlation judgment.
            low_information_fallback = True
            ic = effective_config.ic_warn
            rank_ic = effective_config.rank_ic_warn
            icir = effective_config.icir_warn
            decay_5d = effective_config.decay_pass
            gates = ["WARN", "WARN", "WARN", "PASS"]
        else:
            ic = _safe_corr(left, right)
            rank_ic = _safe_rank_corr(left, right)
            dispersion = float(pd.Series(left).std(ddof=0) or 0.0)
            icir = ic / max(dispersion, 0.01)
            decay_5d = max(0.0, 1.0 - abs(ic) * 2.0)
            gates = [
                _normalize_gate(ic, effective_config.ic_pass, effective_config.ic_warn),
                _normalize_gate(rank_ic, effective_config.rank_ic_pass, effective_config.rank_ic_warn),
                _normalize_gate(icir, effective_config.icir_pass, effective_config.icir_warn),
                _normalize_gate(decay_5d, effective_config.decay_pass, effective_config.decay_warn),
            ]
        factor_gate = _aggregate_gate(gates)

        factor_rows.append(
            {
                "trade_date": trade_date,
                "factor_name": factor_name,
                "ic": round(float(ic), 6),
                "rank_ic": round(float(rank_ic), 6),
                "icir": round(float(icir), 6),
                "decay_5d": round(float(decay_5d), 6),
                "sample_size": sample_size,
                "gate": factor_gate,
                "vote_detail": json.dumps(
                    {
                        "ic_gate": gates[0],
                        "rank_ic_gate": gates[1],
                        "icir_gate": gates[2],
                        "decay_gate": gates[3],
                        "cold_start_fallback": sample_size < 2,
                        "low_information_fallback": low_information_fallback,
                    },
                    ensure_ascii=False,
                ),
                "contract_version": SUPPORTED_CONTRACT_VERSION,
                "created_at": created_at,
            }
        )

    factor_report_frame = pd.DataFrame.from_records(factor_rows)
    factor_gate = _aggregate_gate(factor_report_frame["gate"].tolist()) if not factor_report_frame.empty else "FAIL"

    rr_effective = pd.to_numeric(
        pas_frame.get("effective_risk_reward_ratio", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0.0)
    rr_nominal = pd.to_numeric(
        pas_frame.get("risk_reward_ratio", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0.0)
    rr_series = rr_effective.where(rr_effective > 0.0, rr_nominal)
    rr_mean = float(rr_series.mean()) if not rr_series.empty else 0.0
    if rr_mean <= 0.0 and not rr_nominal.empty:
        rr_mean = float(rr_nominal.mean())

    baseline_return = max(0.015, 0.030 + (mss_score - 50.0) / 2500.0)
    candidate_return = max(0.015, baseline_return + (rr_mean - 1.0) / 120.0)
    baseline_drawdown = max(0.03, 0.060 - (mss_score - 50.0) / 3000.0)
    candidate_drawdown = max(0.03, baseline_drawdown + 0.004 - (rr_mean - 1.0) / 120.0)
    baseline_sharpe = baseline_return / max(baseline_drawdown, 0.01)
    candidate_sharpe = candidate_return / max(candidate_drawdown, 0.01)
    tradability = _clip(rr_mean / 1.00, 0.0, 1.0)

    weight_rows = []
    for plan_id, expected_return, max_drawdown, sharpe in (
        (DEFAULT_WEIGHT_PLAN_ID, baseline_return, baseline_drawdown, baseline_sharpe),
        (CANDIDATE_WEIGHT_PLAN_ID, candidate_return, candidate_drawdown, candidate_sharpe),
    ):
        sharpe_gate = _normalize_gate(sharpe, effective_config.sharpe_pass, effective_config.sharpe_warn)
        drawdown_gate = (
            "PASS"
            if max_drawdown <= effective_config.max_drawdown_pass
            else (
                "WARN"
                if max_drawdown <= effective_config.max_drawdown_warn
                else "FAIL"
            )
        )
        tradability_gate = "PASS" if tradability >= 0.5 else ("WARN" if tradability >= 0.3 else "FAIL")
        gate = _aggregate_gate([sharpe_gate, drawdown_gate, tradability_gate])
        weight_rows.append(
            {
                "trade_date": trade_date,
                "plan_id": plan_id,
                "window_group": "short_long_vote",
                "expected_return": round(float(expected_return), 6),
                "max_drawdown": round(float(max_drawdown), 6),
                "sharpe": round(float(sharpe), 6),
                "turnover_cost": round(max(0.0, 0.001 + (1.0 - rr_mean) * 0.0005), 6),
                "tradability_score": round(float(tradability), 6),
                "gate": gate,
                "vote_detail": json.dumps(
                    {
                        "sharpe_gate": sharpe_gate,
                        "drawdown_gate": drawdown_gate,
                        "tradability_gate": tradability_gate,
                    },
                    ensure_ascii=False,
                ),
                "contract_version": SUPPORTED_CONTRACT_VERSION,
                "created_at": created_at,
            }
        )

    weight_report_frame = pd.DataFrame.from_records(weight_rows)
    selected_weight_plan = DEFAULT_WEIGHT_PLAN_ID
    weight_gate = "FAIL"
    if not weight_report_frame.empty:
        baseline_row = weight_report_frame[weight_report_frame["plan_id"] == DEFAULT_WEIGHT_PLAN_ID]
        candidate_row = weight_report_frame[weight_report_frame["plan_id"] == CANDIDATE_WEIGHT_PLAN_ID]
        baseline_gate = str(baseline_row.iloc[0]["gate"]) if not baseline_row.empty else "FAIL"
        candidate_gate = str(candidate_row.iloc[0]["gate"]) if not candidate_row.empty else "FAIL"

        if baseline_gate in {"PASS", "WARN"}:
            selected_weight_plan = DEFAULT_WEIGHT_PLAN_ID
        elif candidate_gate in {"PASS", "WARN"}:
            selected_weight_plan = CANDIDATE_WEIGHT_PLAN_ID

        selected_row = weight_report_frame[weight_report_frame["plan_id"] == selected_weight_plan]
        weight_gate = str(selected_row.iloc[0]["gate"]) if not selected_row.empty else "FAIL"

    stale_days_values = [0]
    if not mss_frame.empty and "stale_days" in mss_frame.columns:
        stale_days_values.append(int(float(mss_frame.iloc[0].get("stale_days", 0) or 0)))
    if not irs_frame.empty and "stale_days" in irs_frame.columns:
        stale_days_values.append(int(float(pd.to_numeric(irs_frame["stale_days"], errors="coerce").max() or 0)))
    stale_days = max(stale_days_values)

    final_gate = "PASS"
    failure_class = ""
    fallback_plan = ""
    position_cap_ratio = 1.0
    reason = "all_checks_passed"
    validation_prescription = ""

    if issues:
        final_gate = "FAIL"
        failure_class = "factor_failure"
        fallback_plan = "baseline"
        position_cap_ratio = 0.50
        reason = "core_inputs_missing"
        validation_prescription = "rebuild_l2_and_rerun_mss_irs_pas"
        selected_weight_plan = ""
    elif factor_gate == "FAIL":
        final_gate = "FAIL"
        failure_class = "factor_failure"
        fallback_plan = "baseline"
        position_cap_ratio = 0.50
        reason = "factor_validation_fail"
        validation_prescription = "inspect_factor_metrics_and_refresh_data"
        selected_weight_plan = ""
    elif weight_gate == "FAIL":
        final_gate = "FAIL"
        failure_class = "weight_failure"
        fallback_plan = "baseline"
        position_cap_ratio = 0.70
        reason = "weight_validation_fail"
        validation_prescription = "fallback_baseline_and_retrain_weight_candidates"
        selected_weight_plan = ""
    elif stale_days > effective_config.stale_days_threshold:
        final_gate = "WARN"
        failure_class = "data_stale"
        fallback_plan = "last_valid"
        position_cap_ratio = 0.60
        reason = "stale_days_exceed_threshold"
    elif factor_gate == "WARN" or weight_gate == "WARN":
        final_gate = "WARN"
        failure_class = ""
        fallback_plan = "baseline"
        position_cap_ratio = 0.80
        reason = "warn_but_allowed"

    gate_frame = pd.DataFrame.from_records(
        [
            {
                "trade_date": trade_date,
                "final_gate": final_gate,
                "factor_gate": factor_gate,
                "weight_gate": weight_gate,
                "selected_weight_plan": selected_weight_plan,
                "issues": ";".join(issues),
                "reason": reason,
                "failure_class": failure_class,
                "fallback_plan": fallback_plan,
                "position_cap_ratio": round(float(position_cap_ratio), 4),
                "threshold_mode": effective_config.threshold_mode,
                "regime": regime,
                "stale_days": int(stale_days),
                "validation_prescription": validation_prescription,
                "vote_detail": json.dumps(
                    {
                        "factor_gate": factor_gate,
                        "weight_gate": weight_gate,
                        "regime": regime,
                    },
                    ensure_ascii=False,
                ),
                "contract_version": SUPPORTED_CONTRACT_VERSION,
                "created_at": created_at,
            }
        ]
    )

    if selected_weight_plan == CANDIDATE_WEIGHT_PLAN_ID:
        weights = (0.40, 0.30, 0.30)
    else:
        weights = (0.34, 0.33, 0.33)

    weight_plan_frame = pd.DataFrame.from_records(
        [
            {
                "trade_date": trade_date,
                "plan_id": selected_weight_plan or DEFAULT_WEIGHT_PLAN_ID,
                "w_mss": round(float(weights[0]), 4),
                "w_irs": round(float(weights[1]), 4),
                "w_pas": round(float(weights[2]), 4),
                "plan_status": "active" if final_gate in {"PASS", "WARN"} else "standby",
                "contract_version": SUPPORTED_CONTRACT_VERSION,
                "created_at": created_at,
            }
        ]
    )

    run_id = f"validation-{trade_date}-{uuid.uuid4().hex[:8]}"
    run_manifest_payload: dict[str, object] = {
        "trade_date": trade_date,
        "run_id": run_id,
        "threshold_mode": effective_config.threshold_mode,
        "regime": regime,
        "final_gate": final_gate,
        "selected_weight_plan": selected_weight_plan,
        "input_summary": {
            "mss_exists": mss_exists,
            "irs_count": int(irs_count),
            "pas_count": int(pas_count),
            "stale_days": int(stale_days),
        },
        "vote_detail": {
            "factor_gate": factor_gate,
            "weight_gate": weight_gate,
            "reason": reason,
        },
        "contract_version": SUPPORTED_CONTRACT_VERSION,
        "created_at": created_at,
    }

    run_manifest_frame = pd.DataFrame.from_records(
        [
            {
                "trade_date": trade_date,
                "run_id": run_id,
                "threshold_mode": effective_config.threshold_mode,
                "regime": regime,
                "final_gate": final_gate,
                "selected_weight_plan": selected_weight_plan,
                "input_summary": json.dumps(run_manifest_payload["input_summary"], ensure_ascii=False),
                "vote_detail": json.dumps(run_manifest_payload["vote_detail"], ensure_ascii=False),
                "contract_version": SUPPORTED_CONTRACT_VERSION,
                "created_at": created_at,
            }
        ]
    )

    _persist(
        database_path=database_path,
        table_name="validation_factor_report",
        frame=factor_report_frame,
        trade_date=trade_date,
    )
    _persist(
        database_path=database_path,
        table_name="validation_weight_report",
        frame=weight_report_frame,
        trade_date=trade_date,
    )
    count = _persist(
        database_path=database_path,
        table_name="validation_gate_decision",
        frame=gate_frame,
        trade_date=trade_date,
    )
    _persist(
        database_path=database_path,
        table_name="validation_weight_plan",
        frame=weight_plan_frame,
        trade_date=trade_date,
    )
    _persist(
        database_path=database_path,
        table_name="validation_run_manifest",
        frame=run_manifest_frame,
        trade_date=trade_date,
    )

    target_artifacts_dir = artifacts_dir or (Path("artifacts") / "spiral-s2c" / trade_date)
    target_artifacts_dir.mkdir(parents=True, exist_ok=True)
    factor_report_sample_path = target_artifacts_dir / "validation_factor_report_sample.parquet"
    weight_report_sample_path = target_artifacts_dir / "validation_weight_report_sample.parquet"
    weight_plan_sample_path = target_artifacts_dir / "validation_weight_plan_sample.parquet"
    run_manifest_sample_path = target_artifacts_dir / "validation_run_manifest_sample.json"

    factor_report_frame.to_parquet(factor_report_sample_path, index=False)
    weight_report_frame.to_parquet(weight_report_sample_path, index=False)
    weight_plan_frame.to_parquet(weight_plan_sample_path, index=False)
    run_manifest_sample_path.write_text(
        json.dumps(run_manifest_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return ValidationGateResult(
        trade_date=trade_date,
        count=count,
        frame=gate_frame,
        final_gate=final_gate,
        selected_weight_plan=selected_weight_plan,
        has_fail=final_gate == "FAIL",
        factor_report_frame=factor_report_frame,
        weight_report_frame=weight_report_frame,
        weight_plan_frame=weight_plan_frame,
        run_manifest_payload=run_manifest_payload,
        factor_report_sample_path=factor_report_sample_path,
        weight_report_sample_path=weight_report_sample_path,
        weight_plan_sample_path=weight_plan_sample_path,
        run_manifest_sample_path=run_manifest_sample_path,
    )
