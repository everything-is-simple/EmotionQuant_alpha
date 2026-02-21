from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config

# DESIGN_TRACE:
# - docs/design/core-algorithms/irs/irs-algorithm.md (3 六因子, 5 轮动状态, 6 配置建议)
# - docs/design/core-algorithms/irs/irs-data-models.md (3 输出模型, 4 中间表)
# - Governance/SpiralRoadmap/S2C-EXECUTION-CARD.md (3 IRS, 6 artifact)
DESIGN_TRACE = {
    "irs_algorithm": "docs/design/core-algorithms/irs/irs-algorithm.md",
    "irs_data_models": "docs/design/core-algorithms/irs/irs-data-models.md",
    "s2c_execution_card": "Governance/SpiralRoadmap/S2C-EXECUTION-CARD.md",
}

SUPPORTED_CONTRACT_VERSION = "nc-v1"
EPS = 1e-9
SW31_EXPECTED_COUNT = 31

FACTOR_WEIGHTS = {
    "relative_strength": 0.25,
    "continuity_factor": 0.20,
    "capital_flow": 0.20,
    "valuation": 0.15,
    "leader_score": 0.12,
    "gene_score": 0.08,
}

STYLE_WEIGHTS = {
    "growth": (0.35, 0.65),
    "balanced": (0.50, 0.50),
    "value": (0.65, 0.35),
}


@dataclass(frozen=True)
class IrsRunResult:
    trade_date: str
    count: int
    frame: pd.DataFrame
    factor_intermediate_frame: pd.DataFrame
    factor_intermediate_sample_path: Path
    coverage_report_path: Path


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


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / max(float(denominator), 1.0)


def _clip(value: float, low: float, high: float) -> float:
    return float(max(low, min(high, value)))


def _to_recommendation(score: float) -> str:
    if score >= 75.0:
        return "STRONG_BUY"
    if score >= 70.0:
        return "BUY"
    if score >= 50.0:
        return "HOLD"
    if score >= 30.0:
        return "SELL"
    return "AVOID"


def _zscore_to_score(value: float, mean: float, std: float) -> float:
    if abs(float(std)) <= EPS:
        return 50.0
    z = (float(value) - float(mean)) / float(std)
    return _clip(((z + 3.0) / 6.0) * 100.0, 0.0, 100.0)


def _series_mean_std(series: pd.Series) -> tuple[float, float]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return (0.0, 0.0)
    return (float(values.mean()), float(values.std(ddof=0)))


def _parse_json_list(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, str):
        payload = value.strip()
        if not payload:
            return []
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            return []
        if isinstance(obj, list):
            return [float(item) for item in obj]
    return []


def _avg_json_list(value: Any) -> float:
    items = _parse_json_list(value)
    if not items:
        return 0.0
    return float(sum(items) / len(items))


def _robust_slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    y = [float(v) for v in values]
    x = list(range(len(y)))
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y, strict=False))
    denominator = sum((xi - x_mean) ** 2 for xi in x)
    if abs(denominator) <= EPS:
        return 0.0
    return float(numerator / denominator)


def _mad(values: list[float]) -> float:
    if not values:
        return 0.0
    series = pd.Series([float(v) for v in values])
    median = float(series.median())
    return float((series - median).abs().median())


def _rotation_status(score_hist: list[float]) -> tuple[str, float, float]:
    if len(score_hist) < 5:
        if len(score_hist) >= 3 and score_hist[-3] < score_hist[-2] < score_hist[-1]:
            return ("IN", 0.0, 0.0)
        if len(score_hist) >= 3 and score_hist[-3] > score_hist[-2] > score_hist[-1]:
            return ("OUT", 0.0, 0.0)
        return ("HOLD", 0.0, 0.0)

    slope = _robust_slope(score_hist[-5:])
    band = max(1.5, 0.25 * _mad(score_hist[-20:]))
    if slope >= band:
        return ("IN", slope, band)
    if slope <= -band:
        return ("OUT", slope, band)
    return ("HOLD", slope, band)


def _rotation_detail(status: str, slope: float, band: float) -> str:
    if status == "IN" and abs(slope) >= max(2.0 * band, 2.0):
        return "rotation_accelerating"
    if status == "IN":
        return "strong_leading"
    if status == "OUT":
        return "trend_reversal"
    if slope > 0.0:
        return "hotspot_diffusion"
    return "high_level_consolidation"


def _concentration_level(scores: pd.Series) -> str:
    clipped = pd.to_numeric(scores, errors="coerce").clip(lower=0.0)
    total = float(clipped.sum())
    if total <= EPS:
        return "low"
    weights = clipped / total
    hhi = float((weights * weights).sum())
    if hhi >= 0.090:
        return "high"
    if hhi >= 0.060:
        return "medium"
    return "low"


def _allocation_advice(
    *,
    score: float,
    rank: int,
    q25: float,
    q55: float,
    q80: float,
    concentration_level: str,
    allocation_mode: str,
) -> str:
    if allocation_mode == "fixed":
        if 1 <= rank <= 3:
            return "超配"
        if 4 <= rank <= 10:
            return "标配"
        if 11 <= rank <= 26:
            return "减配"
        return "回避"

    if score >= q80 and concentration_level != "high":
        return "超配"
    if q55 <= score < q80:
        return "标配"
    if q25 <= score < q55:
        return "减配"
    return "回避"


def _write_coverage_report(
    *,
    path: Path,
    trade_date: str,
    require_sw31: bool,
    source_industry_count: int,
    source_has_all: bool,
    output_industry_count: int,
    output_has_all: bool,
    allocation_missing_count: int,
    gate_status: str,
    gate_reason: str,
) -> None:
    lines = [
        "# IRS SW31 Coverage Report",
        "",
        f"- trade_date: {trade_date}",
        f"- require_sw31: {str(require_sw31).lower()}",
        f"- source_industry_count: {source_industry_count}",
        f"- source_has_all: {str(source_has_all).lower()}",
        f"- output_industry_count: {output_industry_count}",
        f"- output_has_all: {str(output_has_all).lower()}",
        f"- allocation_missing_count: {allocation_missing_count}",
        f"- expected_sw31_count: {SW31_EXPECTED_COUNT}",
        f"- gate_status: {gate_status}",
        f"- gate_reason: {gate_reason}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _load_baseline_map(config: Config) -> dict[str, tuple[float, float]]:
    baseline_path = Path(config.data_path) / "config" / "irs_zscore_baseline.parquet"
    if not baseline_path.exists():
        return {}

    try:
        baseline = pd.read_parquet(baseline_path)
    except Exception:
        return {}

    if baseline.empty:
        return {}

    key_col = None
    for candidate in ("factor_name", "factor", "name", "key"):
        if candidate in baseline.columns:
            key_col = candidate
            break
    if key_col is None or "mean" not in baseline.columns or "std" not in baseline.columns:
        return {}

    mapping: dict[str, tuple[float, float]] = {}
    for _, row in baseline.iterrows():
        key = str(row.get(key_col, "")).strip()
        if not key:
            continue
        mapping[key] = (float(row.get("mean", 0.0)), float(row.get("std", 0.0)))
    return mapping


def _score_with_history(
    *,
    value: float,
    history_series: pd.Series,
    baseline_map: dict[str, tuple[float, float]],
    baseline_key: str,
) -> tuple[float, float, float]:
    if baseline_key in baseline_map:
        mean, std = baseline_map[baseline_key]
    else:
        mean, std = _series_mean_std(history_series.tail(120))
    if abs(std) <= EPS:
        return (50.0, mean, std)
    return (_zscore_to_score(value, mean, std), mean, std)


def run_irs_daily(
    *,
    trade_date: str,
    config: Config,
    artifacts_dir: Path | None = None,
    require_sw31: bool = False,
) -> IrsRunResult:
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not database_path.exists():
        raise FileNotFoundError("duckdb_not_found")

    baseline_map = _load_baseline_map(config)

    with duckdb.connect(str(database_path), read_only=True) as connection:
        if not _table_exists(connection, "industry_snapshot"):
            raise ValueError("industry_snapshot_table_missing")

        source = connection.execute(
            "SELECT * FROM industry_snapshot WHERE trade_date = ?",
            [trade_date],
        ).df()
        history = connection.execute(
            "SELECT * FROM industry_snapshot WHERE trade_date <= ? "
            "ORDER BY trade_date, industry_code",
            [trade_date],
        ).df()

        if _table_exists(connection, "raw_index_daily"):
            benchmark_history = connection.execute(
                "SELECT trade_date, pct_chg FROM raw_index_daily "
                "WHERE trade_date <= ? ORDER BY trade_date",
                [trade_date],
            ).df()
        else:
            benchmark_history = pd.DataFrame.from_records([])

        if _table_exists(connection, "irs_industry_daily"):
            irs_history = connection.execute(
                "SELECT trade_date, industry_code, industry_score, irs_score "
                "FROM irs_industry_daily WHERE trade_date < ? ORDER BY trade_date",
                [trade_date],
            ).df()
        else:
            irs_history = pd.DataFrame.from_records([])

    if source.empty:
        raise ValueError("industry_snapshot_empty_for_trade_date")

    target_artifacts_dir = artifacts_dir or (
        Path("artifacts") / ("spiral-s3c" if require_sw31 else "spiral-s2c") / trade_date
    )
    coverage_report_path = target_artifacts_dir / "irs_allocation_coverage_report.md"

    source_codes = sorted(
        {
            str(code).strip()
            for code in source.get("industry_code", pd.Series([], dtype="object")).tolist()
            if str(code).strip()
        }
    )
    source_has_all = "ALL" in source_codes

    for column in (
        "industry_pct_chg",
        "industry_amount",
        "industry_turnover",
        "industry_pe_ttm",
        "industry_pb",
        "rise_count",
        "fall_count",
        "new_100d_high_count",
        "new_100d_low_count",
        "limit_up_count",
        "top5_limit_up",
        "stock_count",
        "stale_days",
    ):
        if column not in history.columns:
            history[column] = 0.0
        history[column] = pd.to_numeric(history[column], errors="coerce").fillna(0.0)

    market_amount_by_date = (
        history.groupby("trade_date")["industry_amount"].sum().to_dict()
        if not history.empty
        else {}
    )

    benchmark_map = (
        benchmark_history.set_index("trade_date")["pct_chg"].to_dict()
        if not benchmark_history.empty and {"trade_date", "pct_chg"} <= set(benchmark_history.columns)
        else {}
    )

    output_rows: list[dict[str, object]] = []
    factor_rows: list[dict[str, object]] = []
    created_at = pd.Timestamp.utcnow().isoformat()

    for _, row in source.iterrows():
        item = row.to_dict()
        industry_code = str(item.get("industry_code", "UNKNOWN") or "UNKNOWN")
        industry_name = str(item.get("industry_name", "未知行业") or "未知行业")

        industry_hist = history[history["industry_code"].astype(str) == industry_code].copy()
        if industry_hist.empty:
            industry_hist = source[source["industry_code"].astype(str) == industry_code].copy()
        industry_hist = industry_hist.sort_values("trade_date")
        sample_days = int(len(industry_hist))

        stock_count = industry_hist["stock_count"].clip(lower=1.0)
        rise_ratio = industry_hist["rise_count"] / stock_count
        fall_ratio = industry_hist["fall_count"] / stock_count
        new_high_ratio = industry_hist["new_100d_high_count"] / stock_count
        new_low_ratio = industry_hist["new_100d_low_count"] / stock_count

        benchmark_series = industry_hist["trade_date"].map(benchmark_map).fillna(0.0)
        relative_strength_raw_series = (
            pd.to_numeric(industry_hist["industry_pct_chg"], errors="coerce").fillna(0.0)
            - benchmark_series
        )
        relative_strength_raw = float(relative_strength_raw_series.iloc[-1])

        net_breadth = rise_ratio - fall_ratio
        net_new_high = new_high_ratio - new_low_ratio
        continuity_raw_series = (
            0.6 * net_breadth.rolling(window=5, min_periods=1).sum()
            + 0.4 * net_new_high.rolling(window=5, min_periods=1).sum()
        )
        continuity_raw = float(continuity_raw_series.iloc[-1])

        amount_series = pd.to_numeric(industry_hist["industry_amount"], errors="coerce").fillna(0.0)
        amount_delta = amount_series.diff().fillna(0.0)
        amount_avg_20 = amount_series.rolling(window=20, min_periods=1).mean().clip(lower=EPS)
        relative_volume = amount_series / amount_avg_20

        market_amount_total = industry_hist["trade_date"].map(market_amount_by_date).fillna(amount_series)
        flow_share = amount_series / market_amount_total.clip(lower=EPS)
        flow_share_mean_20 = flow_share.rolling(window=20, min_periods=1).mean().clip(lower=EPS)
        crowding_ratio = flow_share / flow_share_mean_20

        net_inflow_10d = amount_delta.rolling(window=10, min_periods=1).sum()
        net_inflow_score, _, _ = _score_with_history(
            value=float(net_inflow_10d.iloc[-1]),
            history_series=net_inflow_10d,
            baseline_map=baseline_map,
            baseline_key="irs_capital_flow_net_inflow_10d",
        )
        flow_share_score, _, _ = _score_with_history(
            value=float(flow_share.iloc[-1]),
            history_series=flow_share,
            baseline_map=baseline_map,
            baseline_key="irs_capital_flow_flow_share",
        )
        relative_volume_score, _, _ = _score_with_history(
            value=float(relative_volume.iloc[-1]),
            history_series=relative_volume,
            baseline_map=baseline_map,
            baseline_key="irs_capital_flow_relative_volume",
        )
        crowding_penalty = 6.0 * max(float(crowding_ratio.iloc[-1]) - 1.2, 0.0)
        capital_flow_score = _clip(
            0.5 * net_inflow_score + 0.3 * flow_share_score + 0.2 * relative_volume_score - crowding_penalty,
            0.0,
            100.0,
        )

        style_bucket = str(item.get("style_bucket", "balanced") or "balanced").strip().lower()
        w_pe, w_pb = STYLE_WEIGHTS.get(style_bucket, STYLE_WEIGHTS["balanced"])
        pe_series = pd.to_numeric(industry_hist["industry_pe_ttm"], errors="coerce").fillna(0.0)
        pb_series = pd.to_numeric(industry_hist["industry_pb"], errors="coerce").fillna(0.0)
        valuation_raw_series = w_pe * (-pe_series) + w_pb * (-pb_series)
        valuation_raw = float(valuation_raw_series.iloc[-1])

        top5_limit_ratio = pd.to_numeric(industry_hist["top5_limit_up"], errors="coerce").fillna(0.0) / 5.0
        top5_pct_avg = industry_hist["top5_pct_chg"].map(_avg_json_list)
        leader_raw_series = 0.6 * top5_pct_avg + 0.4 * top5_limit_ratio
        leader_raw = float(leader_raw_series.iloc[-1])

        gene_limit_ratio = pd.to_numeric(industry_hist["limit_up_count"], errors="coerce").fillna(0.0) / stock_count
        gene_high_ratio = pd.to_numeric(industry_hist["new_100d_high_count"], errors="coerce").fillna(0.0) / stock_count
        gene_raw_series = (
            0.6 * gene_limit_ratio.ewm(alpha=0.1, adjust=False).mean()
            + 0.4 * gene_high_ratio.ewm(alpha=0.1, adjust=False).mean()
        )
        gene_raw = float(gene_raw_series.iloc[-1])

        relative_strength_score, rs_mean, rs_std = _score_with_history(
            value=relative_strength_raw,
            history_series=relative_strength_raw_series,
            baseline_map=baseline_map,
            baseline_key="irs_relative_strength_raw",
        )
        continuity_score, cont_mean, cont_std = _score_with_history(
            value=continuity_raw,
            history_series=continuity_raw_series,
            baseline_map=baseline_map,
            baseline_key="irs_continuity_raw",
        )
        valuation_score, valuation_mean, valuation_std = _score_with_history(
            value=valuation_raw,
            history_series=valuation_raw_series,
            baseline_map=baseline_map,
            baseline_key="irs_valuation_raw",
        )
        leader_score, leader_mean, leader_std = _score_with_history(
            value=leader_raw,
            history_series=leader_raw_series,
            baseline_map=baseline_map,
            baseline_key="irs_leader_raw",
        )
        gene_score, gene_mean, gene_std = _score_with_history(
            value=gene_raw,
            history_series=gene_raw_series,
            baseline_map=baseline_map,
            baseline_key="irs_gene_raw",
        )

        industry_score = round(
            relative_strength_score * FACTOR_WEIGHTS["relative_strength"]
            + continuity_score * FACTOR_WEIGHTS["continuity_factor"]
            + capital_flow_score * FACTOR_WEIGHTS["capital_flow"]
            + valuation_score * FACTOR_WEIGHTS["valuation"]
            + leader_score * FACTOR_WEIGHTS["leader_score"]
            + gene_score * FACTOR_WEIGHTS["gene_score"],
            4,
        )

        stale_days = int(float(item.get("stale_days", 0) or 0))
        quality_flag = "stale" if stale_days > 0 else ("cold_start" if sample_days < 60 else "normal")

        output_rows.append(
            {
                "trade_date": trade_date,
                "industry_code": industry_code,
                "industry_name": industry_name,
                "industry_score": industry_score,
                "irs_score": industry_score,
                "quality_flag": quality_flag,
                "sample_days": sample_days,
                "relative_strength": round(relative_strength_score, 4),
                "continuity_factor": round(continuity_score, 4),
                "capital_flow": round(capital_flow_score, 4),
                "valuation": round(valuation_score, 4),
                "leader_score": round(leader_score, 4),
                "gene_score": round(gene_score, 4),
                "data_quality": str(item.get("data_quality", "normal") or "normal"),
                "stale_days": stale_days,
                "source_trade_date": str(item.get("source_trade_date", trade_date) or trade_date),
                "contract_version": SUPPORTED_CONTRACT_VERSION,
                "created_at": created_at,
            }
        )

        factor_rows.append(
            {
                "trade_date": trade_date,
                "industry_code": industry_code,
                "relative_strength_raw": round(relative_strength_raw, 6),
                "continuity_factor_raw": round(continuity_raw, 6),
                "capital_flow_raw": round(
                    0.5 * float(net_inflow_10d.iloc[-1])
                    + 0.3 * float(flow_share.iloc[-1])
                    + 0.2 * float(relative_volume.iloc[-1]),
                    6,
                ),
                "valuation_raw": round(valuation_raw, 6),
                "leader_score_raw": round(leader_raw, 6),
                "gene_score_raw": round(gene_raw, 6),
                "relative_strength_mean": round(rs_mean, 6),
                "relative_strength_std": round(rs_std, 6),
                "continuity_factor_mean": round(cont_mean, 6),
                "continuity_factor_std": round(cont_std, 6),
                "valuation_mean": round(valuation_mean, 6),
                "valuation_std": round(valuation_std, 6),
                "leader_score_mean": round(leader_mean, 6),
                "leader_score_std": round(leader_std, 6),
                "gene_score_mean": round(gene_mean, 6),
                "gene_score_std": round(gene_std, 6),
                "created_at": created_at,
            }
        )

    frame = pd.DataFrame.from_records(output_rows)
    if frame.empty:
        raise ValueError("irs_empty_after_semantic_scoring")

    frame["rank"] = frame["industry_score"].rank(method="dense", ascending=False).astype(int)
    q25 = float(frame["industry_score"].quantile(0.25))
    q55 = float(frame["industry_score"].quantile(0.55))
    q80 = float(frame["industry_score"].quantile(0.80))
    concentration_level = _concentration_level(frame["industry_score"])

    frame["allocation_mode"] = "dynamic"
    frame["allocation_advice"] = frame.apply(
        lambda row: _allocation_advice(
            score=float(row["industry_score"]),
            rank=int(row["rank"]),
            q25=q25,
            q55=q55,
            q80=q80,
            concentration_level=concentration_level,
            allocation_mode="dynamic",
        ),
        axis=1,
    )

    score_history_by_industry: dict[str, list[float]] = {}
    if not irs_history.empty:
        local_hist = irs_history.copy()
        if "industry_score" not in local_hist.columns and "irs_score" in local_hist.columns:
            local_hist["industry_score"] = local_hist["irs_score"]
        for _, old_row in local_hist.iterrows():
            code = str(old_row.get("industry_code", "")).strip()
            if not code:
                continue
            score_history_by_industry.setdefault(code, []).append(
                float(old_row.get("industry_score", 0.0) or 0.0)
            )

    rotation_statuses: list[str] = []
    rotation_slopes: list[float] = []
    rotation_details: list[str] = []
    for _, day_row in frame.iterrows():
        code = str(day_row["industry_code"])
        score_hist = score_history_by_industry.get(code, []) + [float(day_row["industry_score"])]
        status, slope, band = _rotation_status(score_hist)
        rotation_statuses.append(status)
        rotation_slopes.append(round(float(slope), 6))
        rotation_details.append(_rotation_detail(status, slope, band))

    frame["rotation_status"] = rotation_statuses
    frame["rotation_slope"] = rotation_slopes
    frame["rotation_detail"] = rotation_details
    frame["neutrality"] = frame["industry_score"].map(
        lambda score: round(_clip(1.0 - abs(float(score) - 50.0) / 50.0, 0.0, 1.0), 4)
    )
    frame["recommendation"] = frame["industry_score"].map(_to_recommendation)
    frame["created_at"] = pd.Timestamp.utcnow().isoformat()

    output_codes = sorted(
        {
            str(code).strip()
            for code in frame.get("industry_code", pd.Series([], dtype="object")).tolist()
            if str(code).strip()
        }
    )
    output_has_all = "ALL" in output_codes
    allocation_missing_count = int(
        (frame["allocation_advice"].astype(str).str.strip() == "").sum()
    )
    sw31_pass = (
        (not output_has_all)
        and len(output_codes) == SW31_EXPECTED_COUNT
        and allocation_missing_count == 0
    )
    gate_status = "PASS" if sw31_pass else "FAIL"
    gate_reason = (
        "ok"
        if sw31_pass
        else (
            f"output_industry_count={len(output_codes)}, "
            f"output_has_all={str(output_has_all).lower()}, "
            f"allocation_missing_count={allocation_missing_count}"
        )
    )
    _write_coverage_report(
        path=coverage_report_path,
        trade_date=trade_date,
        require_sw31=require_sw31,
        source_industry_count=len(source_codes),
        source_has_all=source_has_all,
        output_industry_count=len(output_codes),
        output_has_all=output_has_all,
        allocation_missing_count=allocation_missing_count,
        gate_status=gate_status,
        gate_reason=gate_reason,
    )
    if require_sw31 and not sw31_pass:
        raise ValueError(f"irs_sw31_coverage_gate_failed: {gate_reason}")

    frame = frame[
        [
            "trade_date",
            "industry_code",
            "industry_name",
            "industry_score",
            "irs_score",
            "rank",
            "rotation_status",
            "rotation_slope",
            "rotation_detail",
            "allocation_advice",
            "allocation_mode",
            "quality_flag",
            "sample_days",
            "relative_strength",
            "continuity_factor",
            "capital_flow",
            "valuation",
            "leader_score",
            "gene_score",
            "neutrality",
            "recommendation",
            "data_quality",
            "stale_days",
            "source_trade_date",
            "contract_version",
            "created_at",
        ]
    ]

    count = _persist(
        database_path=database_path,
        table_name="irs_industry_daily",
        frame=frame,
        trade_date=trade_date,
    )

    factor_frame = pd.DataFrame.from_records(factor_rows)
    _persist(
        database_path=database_path,
        table_name="irs_factor_intermediate",
        frame=factor_frame,
        trade_date=trade_date,
    )

    artifact_path = target_artifacts_dir / "irs_factor_intermediate_sample.parquet"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    factor_frame.to_parquet(artifact_path, index=False)

    return IrsRunResult(
        trade_date=trade_date,
        count=count,
        frame=frame,
        factor_intermediate_frame=factor_frame,
        factor_intermediate_sample_path=artifact_path,
        coverage_report_path=coverage_report_path,
    )
