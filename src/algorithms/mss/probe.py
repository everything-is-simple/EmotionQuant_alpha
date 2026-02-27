"""MSS 探针（S1B）：验证 MSS 评分对未来收益的预测能力。

核心指标: top_bottom_spread_5d（高温度组 vs 低温度组的 5 日前瞻收益差）。
若 spread > 0 则表明 MSS 具备方向性预测价值。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config
from src.db.helpers import table_exists as _table_exists
from src.integration.mss_consumer import load_mss_panorama_for_integration

# DESIGN_TRACE:
# - docs/design/core-algorithms/mss/mss-algorithm.md (§5 周期与消费语义)
# - docs/design/core-algorithms/integration/integration-algorithm.md (§2 输入规范, §4 方向一致性)
# - Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md (§5 S1b)
# - Governance/SpiralRoadmap/execution-cards/S1B-EXECUTION-CARD.md (§2 run, §3 test, §4 artifact)
DESIGN_TRACE = {
    "mss_algorithm": "docs/design/core-algorithms/mss/mss-algorithm.md",
    "integration_algorithm": "docs/design/core-algorithms/integration/integration-algorithm.md",
    "s0_s2_roadmap": "Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md",
    "s1b_execution_card": "Governance/SpiralRoadmap/execution-cards/S1B-EXECUTION-CARD.md",
}

SUPPORTED_CONTRACT_VERSION = "nc-v1"


@dataclass(frozen=True)
class MssProbeResult:
    start_date: str
    end_date: str
    artifacts_dir: Path
    return_series_source: str
    has_error: bool
    error_manifest_path: Path
    probe_report_path: Path
    consumption_case_path: Path
    gate_report_path: Path
    top_bottom_spread_5d: float
    conclusion: str


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _validate_date_range(start_date: str, end_date: str) -> None:
    if len(start_date) != 8 or not start_date.isdigit():
        raise ValueError(f"invalid start_date: {start_date}")
    if len(end_date) != 8 or not end_date.isdigit():
        raise ValueError(f"invalid end_date: {end_date}")
    if start_date > end_date:
        raise ValueError(f"start_date_after_end_date: {start_date}>{end_date}")


def _compute_top_bottom_spread_5d(frame: pd.DataFrame) -> tuple[float, str, int, int, int]:
    if len(frame) < 6:
        return 0.0, "WARN_INSUFFICIENT_SAMPLE", 0, 0, 0

    work = frame.copy().reset_index(drop=True)
    valid = work.dropna(subset=["forward_5d"]).copy()
    if valid.empty:
        return 0.0, "WARN_INSUFFICIENT_SAMPLE", 0, 0, 0

    q_top = float(valid["mss_temperature"].quantile(0.7))
    q_bottom = float(valid["mss_temperature"].quantile(0.3))

    top_bucket = valid[valid["mss_temperature"] >= q_top]
    bottom_bucket = valid[valid["mss_temperature"] <= q_bottom]
    if top_bucket.empty or bottom_bucket.empty:
        return 0.0, "WARN_INSUFFICIENT_DISTRIBUTION", len(valid), len(top_bucket), len(bottom_bucket)

    spread = float(mean(top_bucket["forward_5d"]) - mean(bottom_bucket["forward_5d"]))
    if spread > 0:
        conclusion = "PASS_POSITIVE_SPREAD"
    elif spread < 0:
        conclusion = "WARN_NEGATIVE_SPREAD"
    else:
        conclusion = "WARN_FLAT_SPREAD"
    return spread, conclusion, len(valid), len(top_bucket), len(bottom_bucket)




def _load_future_returns_5d(
    *,
    database_path: Path,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    if not database_path.exists():
        return pd.DataFrame(columns=["trade_date", "forward_5d"])
    with duckdb.connect(str(database_path), read_only=True) as connection:
        if not _table_exists(connection, "raw_index_daily"):
            return pd.DataFrame(columns=["trade_date", "forward_5d"])
        index_frame = connection.execute(
            "SELECT CAST(trade_date AS VARCHAR) AS trade_date, AVG(close) AS market_close "
            "FROM raw_index_daily "
            "WHERE CAST(trade_date AS VARCHAR) >= ? AND CAST(trade_date AS VARCHAR) <= ? "
            "GROUP BY trade_date ORDER BY trade_date",
            [start_date, end_date],
        ).df()
    if index_frame.empty:
        return pd.DataFrame(columns=["trade_date", "forward_5d"])
    index_frame["market_close"] = pd.to_numeric(index_frame["market_close"], errors="coerce")
    index_frame["forward_5d"] = (
        index_frame["market_close"].shift(-5) - index_frame["market_close"]
    ) / index_frame["market_close"].replace(0.0, pd.NA)
    return index_frame[["trade_date", "forward_5d"]].dropna(subset=["forward_5d"]).reset_index(drop=True)


def _write_probe_report(
    *,
    path: Path,
    start_date: str,
    end_date: str,
    sample_days: int,
    effective_samples_5d: int,
    top_bucket_count: int,
    bottom_bucket_count: int,
    spread: float,
    conclusion: str,
    return_series_source: str,
) -> None:
    lines = [
        "# MSS Only Probe Report",
        "",
        f"- start_date: {start_date}",
        f"- end_date: {end_date}",
        f"- sample_days: {sample_days}",
        f"- effective_samples_5d: {effective_samples_5d}",
        f"- top_bucket_count: {top_bucket_count}",
        f"- bottom_bucket_count: {bottom_bucket_count}",
        f"- return_series_source: {return_series_source}",
        f"- top_bottom_spread_5d: {round(spread, 6)}",
        f"- conclusion: {conclusion}",
        "",
        "## Gate",
        f"- gate_result: {'PASS' if conclusion == 'PASS_POSITIVE_SPREAD' else 'WARN'}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_consumption_case(
    *,
    path: Path,
    latest_row: pd.Series,
    conclusion: str,
) -> None:
    lines = [
        "# MSS Consumption Case",
        "",
        "- consumer: S2a pre-integration validation",
        "- consumed_fields: mss_score,mss_temperature,mss_cycle,mss_trend,trade_date",
        f"- latest_trade_date: {latest_row['trade_date']}",
        f"- latest_mss_score: {latest_row['mss_score']}",
        f"- latest_mss_temperature: {latest_row['mss_temperature']}",
        f"- latest_mss_cycle: {latest_row['mss_cycle']}",
        f"- latest_mss_trend: {latest_row['mss_trend']}",
        f"- contract_version: {latest_row['contract_version']}",
        f"- consumption_conclusion: {conclusion}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_gate_report(
    *,
    path: Path,
    start_date: str,
    end_date: str,
    return_series_source: str,
    conclusion: str,
    has_error: bool,
) -> None:
    gate_result = "FAIL" if has_error else ("PASS" if conclusion == "PASS_POSITIVE_SPREAD" else "WARN")
    lines = [
        "# MSS Probe Gate Report",
        "",
        f"- start_date: {start_date}",
        f"- end_date: {end_date}",
        f"- return_series_source: {return_series_source}",
        f"- conclusion: {conclusion}",
        f"- gate_result: {gate_result}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_mss_probe(
    *,
    start_date: str,
    end_date: str,
    config: Config,
    return_series_source: str = "temperature_delta",
    artifacts_dir: Path | None = None,
) -> MssProbeResult:
    _validate_date_range(start_date, end_date)
    source = str(return_series_source or "temperature_delta").strip().lower() or "temperature_delta"
    if source not in {"temperature_delta", "future_returns"}:
        raise ValueError(
            "unsupported return_series_source: "
            f"{return_series_source}; allowed=['future_returns', 'temperature_delta']"
        )

    resolved_artifacts_dir = artifacts_dir or (Path("artifacts") / "spiral-s1b" / f"{start_date}_{end_date}")
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    errors: list[dict[str, str]] = []

    def add_error(level: str, step: str, message: str) -> None:
        errors.append(
            {
                "error_level": level,
                "step": step,
                "start_date": start_date,
                "end_date": end_date,
                "message": message,
            }
        )

    spread = 0.0
    conclusion = "WARN_NOT_RUN"
    probe_report_name = "mss_probe_return_series_report.md" if source == "future_returns" else "mss_only_probe_report.md"
    consumption_name = "consumption.md" if source == "future_returns" else "mss_consumption_case.md"
    probe_report_path = resolved_artifacts_dir / probe_report_name
    consumption_case_path = resolved_artifacts_dir / consumption_name
    gate_report_path = resolved_artifacts_dir / "gate_report.md"

    try:
        frame = load_mss_panorama_for_integration(
            database_path=database_path,
            start_date=start_date,
            end_date=end_date,
        )
        if frame.empty:
            add_error("P0", "load_mss_panorama", "mss_panorama_empty_in_window")
            raise RuntimeError("mss_panorama_empty_in_window")
        unsupported_versions = sorted(
            {
                str(item).strip()
                for item in frame["contract_version"].astype(str).tolist()
                if str(item).strip() != SUPPORTED_CONTRACT_VERSION
            }
        )
        if unsupported_versions:
            add_error(
                "P0",
                "contract",
                f"contract_version_mismatch:{'|'.join(unsupported_versions)}",
            )
            raise RuntimeError("contract_version_mismatch")

        work = frame.copy().reset_index(drop=True)
        if source == "future_returns":
            future_returns = _load_future_returns_5d(
                database_path=database_path,
                start_date=start_date,
                end_date=end_date,
            )
            if future_returns.empty:
                add_error("P1", "future_returns", "future_returns_series_missing")
            work = work.merge(future_returns, on="trade_date", how="left")
        else:
            work["forward_5d"] = (
                work["mss_temperature"].shift(-5) - work["mss_temperature"]
            ) / work["mss_temperature"].abs().replace(0.0, 1.0)

        spread, conclusion, effective_samples_5d, top_count, bottom_count = _compute_top_bottom_spread_5d(work)
        _write_probe_report(
            path=probe_report_path,
            start_date=start_date,
            end_date=end_date,
            sample_days=len(frame),
            effective_samples_5d=effective_samples_5d,
            top_bucket_count=top_count,
            bottom_bucket_count=bottom_count,
            spread=spread,
            conclusion=conclusion,
            return_series_source=source,
        )
        latest_row = frame.iloc[-1]
        _write_consumption_case(
            path=consumption_case_path,
            latest_row=latest_row,
            conclusion=conclusion,
        )
        _write_gate_report(
            path=gate_report_path,
            start_date=start_date,
            end_date=end_date,
            return_series_source=source,
            conclusion=conclusion,
            has_error=bool(errors),
        )
    except Exception as exc:  # pragma: no cover - guarded by contract tests
        if not errors:
            add_error("P0", "run_mss_probe", str(exc))
        resolved_artifacts_dir.mkdir(parents=True, exist_ok=True)
        probe_report_path.write_text(
            "# MSS Only Probe Report\n\n- status: FAIL\n",
            encoding="utf-8",
        )
        consumption_case_path.write_text(
            "# MSS Consumption Case\n\n- status: FAIL\n",
            encoding="utf-8",
        )
        _write_gate_report(
            path=gate_report_path,
            start_date=start_date,
            end_date=end_date,
            return_series_source=source,
            conclusion=conclusion,
            has_error=True,
        )

    error_manifest_payload = {
        "start_date": start_date,
        "end_date": end_date,
        "return_series_source": source,
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

    return MssProbeResult(
        start_date=start_date,
        end_date=end_date,
        artifacts_dir=resolved_artifacts_dir,
        return_series_source=source,
        has_error=bool(errors),
        error_manifest_path=manifest_path,
        probe_report_path=probe_report_path,
        consumption_case_path=consumption_case_path,
        gate_report_path=gate_report_path,
        top_bottom_spread_5d=spread,
        conclusion=conclusion,
    )
