from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config
from src.db.helpers import table_exists as _table_exists

# DESIGN_TRACE:
# - Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md (§5 S4b)
# - Governance/SpiralRoadmap/execution-cards/S4B-EXECUTION-CARD.md (§2 run, §4 artifact)
# - Governance/SpiralRoadmap/execution-cards/S4BR-EXECUTION-CARD.md (§2 run, §4 artifact)
DESIGN_TRACE = {
    "s3a_s4b_roadmap": "Governance/SpiralRoadmap/planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md",
    "s4b_execution_card": "Governance/SpiralRoadmap/execution-cards/S4B-EXECUTION-CARD.md",
    "s4br_execution_card": "Governance/SpiralRoadmap/execution-cards/S4BR-EXECUTION-CARD.md",
}

SUPPORTED_SCENARIO = {"limit_down_chain", "liquidity_dryup", "all"}
SUPPORTED_REPAIR = {"", "s4br"}
SUPPORTED_CONTRACT_VERSION = "nc-v1"
RATIO_BY_DOMINANT_COMPONENT = {
    "signal": 0.30,
    "execution": 0.40,
    "cost": 0.50,
    "none": 0.20,
}


@dataclass(frozen=True)
class StressRunResult:
    trade_date: str
    scenario: str
    repair: str
    artifacts_dir: Path
    extreme_defense_report_path: Path
    deleveraging_policy_snapshot_path: Path
    stress_trade_replay_path: Path
    consumption_path: Path
    gate_report_path: Path
    error_manifest_path: Path
    gate_status: str
    go_nogo: str
    target_deleveraging_ratio: float
    executed_deleveraging_ratio: float
    has_error: bool
    s4br_patch_note_path: Path | None
    s4br_delta_report_path: Path | None


def _validate_trade_date(value: str) -> str:
    text = str(value).strip()
    try:
        datetime.strptime(text, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"invalid trade date: {value}; expected YYYYMMDD") from exc
    return text


def _normalize_scenario(scenario: str) -> str:
    normalized = str(scenario).strip().lower()
    if normalized not in SUPPORTED_SCENARIO:
        raise ValueError(
            f"unsupported stress scenario: {scenario}; supported={sorted(SUPPORTED_SCENARIO)}"
        )
    return normalized


def _normalize_repair(repair: str) -> str:
    normalized = str(repair).strip().lower()
    if normalized not in SUPPORTED_REPAIR:
        raise ValueError(f"unsupported stress repair mode: {repair}; supported=['s4br']")
    return normalized


def _artifacts_dir(*, trade_date: str, repair: str) -> Path:
    if repair == "s4br":
        return Path("artifacts") / "spiral-s4br" / trade_date
    return Path("artifacts") / "spiral-s4b" / trade_date


def _write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )




def _load_latest_positions(connection: duckdb.DuckDBPyConnection, trade_date: str) -> tuple[str, pd.DataFrame]:
    if not _table_exists(connection, "positions"):
        return ("", pd.DataFrame(columns=["stock_code", "shares", "market_value"]))
    row = connection.execute(
        "SELECT MAX(trade_date) FROM positions WHERE trade_date <= ?",
        [trade_date],
    ).fetchone()
    anchor_trade_date = str(row[0]) if row and row[0] is not None else ""
    if not anchor_trade_date:
        return ("", pd.DataFrame(columns=["stock_code", "shares", "market_value"]))
    frame = connection.execute(
        "SELECT stock_code, shares, market_value "
        "FROM positions WHERE trade_date = ? ORDER BY stock_code",
        [anchor_trade_date],
    ).df()
    return (anchor_trade_date, frame)


def _load_s3b_policy_source(
    connection: duckdb.DuckDBPyConnection, trade_date: str
) -> dict[str, Any]:
    default_payload = {
        "source": "fallback",
        "source_trade_date": "",
        "dominant_component": "none",
        "signal_deviation": 0.0,
        "execution_deviation": 0.0,
        "cost_deviation": 0.0,
        "total_deviation": 0.0,
    }
    if not _table_exists(connection, "live_backtest_deviation"):
        return default_payload

    row = connection.execute(
        "SELECT trade_date, dominant_component, signal_deviation, execution_deviation, "
        "cost_deviation, total_deviation "
        "FROM live_backtest_deviation "
        "WHERE trade_date <= ? "
        "ORDER BY trade_date DESC, created_at DESC LIMIT 1",
        [trade_date],
    ).fetchone()
    if row is None:
        return default_payload
    dominant_component = str(row[1] or "none").strip().lower()
    if dominant_component not in {"signal", "execution", "cost", "none"}:
        dominant_component = "none"
    return {
        "source": "live_backtest_deviation",
        "source_trade_date": str(row[0] or ""),
        "dominant_component": dominant_component,
        "signal_deviation": float(row[2] or 0.0),
        "execution_deviation": float(row[3] or 0.0),
        "cost_deviation": float(row[4] or 0.0),
        "total_deviation": float(row[5] or 0.0),
    }


def _clip_ratio(value: float) -> float:
    return round(min(0.90, max(0.10, float(value))), 6)


def _resolve_target_ratio(*, policy_source: dict[str, Any], repair: str) -> float:
    dominant_component = str(policy_source.get("dominant_component", "none"))
    base_ratio = float(RATIO_BY_DOMINANT_COMPONENT.get(dominant_component, 0.20))
    total_deviation = abs(float(policy_source.get("total_deviation", 0.0) or 0.0))
    if total_deviation >= 0.05:
        base_ratio += 0.10
    if repair == "s4br":
        base_ratio += 0.10
    return _clip_ratio(base_ratio)


def _to_board_lot(shares: int) -> int:
    if shares <= 0:
        return 0
    return (int(shares) // 100) * 100


def _simulate_stress_replay(
    *,
    positions_frame: pd.DataFrame,
    scenario: str,
    target_ratio: float,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for idx, row in enumerate(positions_frame.to_dict(orient="records"), start=1):
        stock_code = str(row.get("stock_code", "")).strip()
        pre_shares = int(row.get("shares", 0) or 0)
        if not stock_code or pre_shares <= 0:
            continue
        target_sell_shares = _to_board_lot(int(pre_shares * target_ratio))
        if target_sell_shares <= 0:
            target_sell_shares = min(pre_shares, 100)
        if scenario == "limit_down_chain":
            executed_sell_shares = 0
            reject_reason = "REJECT_LIMIT_DOWN_CHAIN"
            fill_ratio = 0.0
        elif scenario == "liquidity_dryup":
            executed_sell_shares = _to_board_lot(int(target_sell_shares * 0.30))
            reject_reason = (
                "REJECT_LIQUIDITY_DRYUP"
                if executed_sell_shares < target_sell_shares
                else "PASS_PARTIAL"
            )
            fill_ratio = (
                round(executed_sell_shares / target_sell_shares, 6)
                if target_sell_shares > 0
                else 0.0
            )
        else:
            if idx % 2 == 0:
                executed_sell_shares = _to_board_lot(int(target_sell_shares * 0.30))
                reject_reason = (
                    "REJECT_LIQUIDITY_DRYUP"
                    if executed_sell_shares < target_sell_shares
                    else "PASS_PARTIAL"
                )
            else:
                executed_sell_shares = 0
                reject_reason = "REJECT_LIMIT_DOWN_CHAIN"
            fill_ratio = (
                round(executed_sell_shares / target_sell_shares, 6)
                if target_sell_shares > 0
                else 0.0
            )
        blocked_shares = max(0, target_sell_shares - executed_sell_shares)
        records.append(
            {
                "trade_date": str(positions_frame.attrs.get("trade_date", "")),
                "scenario": scenario,
                "stock_code": stock_code,
                "pre_shares": pre_shares,
                "target_sell_shares": target_sell_shares,
                "executed_sell_shares": executed_sell_shares,
                "blocked_shares": blocked_shares,
                "fill_ratio": fill_ratio,
                "reject_reason": reject_reason,
            }
        )
    return pd.DataFrame.from_records(records)


def run_stress(
    *,
    trade_date: str,
    scenario: str,
    config: Config,
    repair: str = "",
) -> StressRunResult:
    normalized_trade_date = _validate_trade_date(trade_date)
    normalized_scenario = _normalize_scenario(scenario)
    normalized_repair = _normalize_repair(repair)

    artifacts_dir = _artifacts_dir(trade_date=normalized_trade_date, repair=normalized_repair)
    report_path = artifacts_dir / "extreme_defense_report.md"
    snapshot_path = artifacts_dir / "deleveraging_policy_snapshot.json"
    replay_path = artifacts_dir / "stress_trade_replay.csv"
    consumption_path = artifacts_dir / "consumption.md"
    gate_report_path = artifacts_dir / "gate_report.md"
    error_manifest_path = artifacts_dir / "error_manifest.json"
    s4br_patch_note_path = artifacts_dir / "s4br_patch_note.md" if normalized_repair == "s4br" else None
    s4br_delta_report_path = artifacts_dir / "s4br_delta_report.md" if normalized_repair == "s4br" else None

    errors: list[dict[str, str]] = []
    warnings: list[str] = []

    def add_error(level: str, step: str, message: str) -> None:
        errors.append(
            {
                "error_level": level,
                "step": step,
                "trade_date": normalized_trade_date,
                "message": message,
            }
        )

    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not database_path.exists():
        add_error("P0", "database", "duckdb_not_found")

    policy_source: dict[str, Any] = {}
    source_positions_trade_date = ""
    positions_frame = pd.DataFrame(columns=["stock_code", "shares", "market_value"])
    if not errors:
        with duckdb.connect(str(database_path), read_only=True) as connection:
            source_positions_trade_date, positions_frame = _load_latest_positions(
                connection, normalized_trade_date
            )
            policy_source = _load_s3b_policy_source(connection, normalized_trade_date)

    if not source_positions_trade_date:
        add_error("P0", "positions", "positions_not_ready")
    if not policy_source:
        policy_source = {
            "source": "fallback",
            "source_trade_date": "",
            "dominant_component": "none",
            "signal_deviation": 0.0,
            "execution_deviation": 0.0,
            "cost_deviation": 0.0,
            "total_deviation": 0.0,
        }
    if str(policy_source.get("source", "")) == "fallback":
        warnings.append("s3b_deviation_source_missing_use_fallback_policy")

    target_ratio = _resolve_target_ratio(policy_source=policy_source, repair=normalized_repair)
    positions_frame.attrs["trade_date"] = source_positions_trade_date
    replay_frame = _simulate_stress_replay(
        positions_frame=positions_frame,
        scenario=normalized_scenario,
        target_ratio=target_ratio,
    )
    total_target_sell_shares = int(replay_frame["target_sell_shares"].sum()) if not replay_frame.empty else 0
    total_executed_sell_shares = (
        int(replay_frame["executed_sell_shares"].sum()) if not replay_frame.empty else 0
    )
    executed_ratio = (
        round(total_executed_sell_shares / total_target_sell_shares, 6)
        if total_target_sell_shares > 0
        else 0.0
    )

    if not errors and total_target_sell_shares <= 0:
        warnings.append("no_target_sell_shares_under_policy")

    if errors:
        gate_status = "FAIL"
        go_nogo = "NO_GO"
    elif executed_ratio >= 0.60:
        gate_status = "PASS"
        go_nogo = "GO"
    else:
        gate_status = "WARN"
        go_nogo = "GO"

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    with replay_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "trade_date",
                "scenario",
                "stock_code",
                "pre_shares",
                "target_sell_shares",
                "executed_sell_shares",
                "blocked_shares",
                "fill_ratio",
                "reject_reason",
            ],
        )
        writer.writeheader()
        for record in replay_frame.to_dict(orient="records"):
            writer.writerow(record)

    _write_json(
        snapshot_path,
        {
            "trade_date": normalized_trade_date,
            "scenario": normalized_scenario,
            "repair": normalized_repair,
            "contract_version": SUPPORTED_CONTRACT_VERSION,
            "policy_source": policy_source,
            "target_deleveraging_ratio": target_ratio,
            "executed_deleveraging_ratio": executed_ratio,
            "warnings": warnings,
            "gate_status": gate_status,
            "go_nogo": go_nogo,
        },
    )

    _write_markdown(
        report_path,
        [
            "# S4b Extreme Defense Report",
            "",
            f"- trade_date: {normalized_trade_date}",
            f"- scenario: {normalized_scenario}",
            f"- repair: {normalized_repair or 'none'}",
            f"- source_positions_trade_date: {source_positions_trade_date or 'none'}",
            f"- policy_source: {policy_source.get('source', 'fallback')}",
            f"- dominant_component: {policy_source.get('dominant_component', 'none')}",
            f"- target_deleveraging_ratio: {target_ratio}",
            f"- executed_deleveraging_ratio: {executed_ratio}",
            f"- total_target_sell_shares: {total_target_sell_shares}",
            f"- total_executed_sell_shares: {total_executed_sell_shares}",
            f"- gate_status: {gate_status}",
            f"- go_nogo: {go_nogo}",
            f"- warnings: {','.join(warnings) if warnings else 'none'}",
            "",
        ],
    )

    _write_markdown(
        consumption_path,
        [
            "# S4b Consumption",
            "",
            "- producer: S3b analysis (live_backtest_deviation)",
            "- consumer: S4b extreme defense calibration",
            "- consumed_fields: dominant_component,total_deviation",
            f"- trade_date: {normalized_trade_date}",
            f"- source_trade_date: {policy_source.get('source_trade_date', '') or 'none'}",
            f"- policy_source: {policy_source.get('source', 'fallback')}",
            f"- dominant_component: {policy_source.get('dominant_component', 'none')}",
            "",
        ],
    )

    _write_markdown(
        gate_report_path,
        [
            "# S4b Gate Report",
            "",
            f"- trade_date: {normalized_trade_date}",
            f"- scenario: {normalized_scenario}",
            f"- repair: {normalized_repair or 'none'}",
            f"- gate_status: {gate_status}",
            f"- go_nogo: {go_nogo}",
            f"- target_deleveraging_ratio: {target_ratio}",
            f"- executed_deleveraging_ratio: {executed_ratio}",
            f"- warning_count: {len(warnings)}",
            f"- error_count: {len(errors)}",
            "",
        ],
    )

    _write_json(
        error_manifest_path,
        {
            "trade_date": normalized_trade_date,
            "scenario": normalized_scenario,
            "repair": normalized_repair,
            "error_count": len(errors),
            "errors": errors,
            "warning_count": len(warnings),
            "warnings": warnings,
        },
    )
    if normalized_repair == "s4br" and s4br_patch_note_path is not None and s4br_delta_report_path is not None:
        baseline_target_ratio = _resolve_target_ratio(policy_source=policy_source, repair="")
        ratio_delta = round(target_ratio - baseline_target_ratio, 6)
        _write_markdown(
            s4br_patch_note_path,
            [
                "# S4br Patch Note",
                "",
                f"- trade_date: {normalized_trade_date}",
                f"- scenario: {normalized_scenario}",
                "- repair_scope: extreme_defense_blockers_only",
                "- repair_mode: s4br",
                f"- gate_status: {gate_status}",
                f"- go_nogo: {go_nogo}",
                "- return_to_s4b_revalidation: "
                + ("pass" if go_nogo == "GO" else "blocked"),
                "",
            ],
        )
        _write_markdown(
            s4br_delta_report_path,
            [
                "# S4br Delta Report",
                "",
                f"- trade_date: {normalized_trade_date}",
                f"- scenario: {normalized_scenario}",
                f"- baseline_target_deleveraging_ratio: {baseline_target_ratio}",
                f"- repair_target_deleveraging_ratio: {target_ratio}",
                f"- ratio_delta: {ratio_delta}",
                f"- executed_deleveraging_ratio: {executed_ratio}",
                f"- gate_status: {gate_status}",
                f"- go_nogo: {go_nogo}",
                "",
            ],
        )

    return StressRunResult(
        trade_date=normalized_trade_date,
        scenario=normalized_scenario,
        repair=normalized_repair,
        artifacts_dir=artifacts_dir,
        extreme_defense_report_path=report_path,
        deleveraging_policy_snapshot_path=snapshot_path,
        stress_trade_replay_path=replay_path,
        consumption_path=consumption_path,
        gate_report_path=gate_report_path,
        error_manifest_path=error_manifest_path,
        gate_status=gate_status,
        go_nogo=go_nogo,
        target_deleveraging_ratio=target_ratio,
        executed_deleveraging_ratio=executed_ratio,
        has_error=bool(errors),
        s4br_patch_note_path=s4br_patch_note_path,
        s4br_delta_report_path=s4br_delta_report_path,
    )
