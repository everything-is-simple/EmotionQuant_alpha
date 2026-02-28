"""数据层 L2 快照生成流水线：从 L1 原始表计算市场快照和行业快照。

流程：
1. 从 DuckDB 读取 L1 原始表（raw_daily / raw_limit_list / raw_daily_basic）
2. 加载申万行业分类 + 成分股映射
3. 生成 MarketSnapshot + IndustrySnapshot（SW31 维度或全市场兜底）
4. 写入 DuckDB + Parquet + 产物文件
5. 评估 L2 质量门禁
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.config.config import Config
from src.db.helpers import table_exists as _table_exists
from src.data.models.snapshots import IndustrySnapshot, MarketSnapshot
from src.data.quality_gate import STATUS_BLOCKED, evaluate_data_quality_gate
from src.data.quality_store import (
    decision_to_json,
    init_quality_context,
    persist_quality_outputs,
)

# DESIGN_TRACE:
# - docs/design/core-infrastructure/data-layer/data-layer-algorithm.md (§3 L2 快照计算, §4 质量门禁)
# - Governance/SpiralRoadmap/execution-cards/S0C-EXECUTION-CARD.md (§2 run, §3 test, §4 artifact)
DESIGN_TRACE = {
    "data_layer_algorithm": "docs/design/core-infrastructure/data-layer/data-layer-algorithm.md",
    "s0c_execution_card": "Governance/SpiralRoadmap/execution-cards/S0C-EXECUTION-CARD.md",
}

SW31_EXPECTED_COUNT = 31
SW31_SOURCE = "SW2021"
SW31_LEVEL = "L1"


@dataclass(frozen=True)
class L2RunResult:
    trade_date: str
    source: str
    artifacts_dir: Path
    market_snapshot_count: int
    industry_snapshot_count: int
    has_error: bool
    error_manifest_path: Path
    canary_report_path: Path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )




def _normalize_stock_code(row: pd.Series) -> str:
    stock_code = str(row.get("stock_code", "")).strip()
    if stock_code:
        return stock_code
    ts_code = str(row.get("ts_code", "")).strip()
    if "." in ts_code:
        return ts_code.split(".", maxsplit=1)[0]
    return ts_code or "UNKNOWN"


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _resolve_pct_chg_percent(frame: pd.DataFrame) -> tuple[pd.Series, str]:
    if frame.empty:
        return (pd.Series(dtype=float), "pct_chg")
    if "pct_chg" in frame.columns:
        pct = pd.to_numeric(frame["pct_chg"], errors="coerce").fillna(0.0)
        return (pct, "pct_chg")

    close = pd.to_numeric(
        frame.get("close", pd.Series([0.0] * len(frame), index=frame.index)),
        errors="coerce",
    ).fillna(0.0)
    if "pre_close" in frame.columns:
        pre_close = pd.to_numeric(frame["pre_close"], errors="coerce")
        pct = ((close - pre_close) / pre_close.replace(0.0, pd.NA)) * 100.0
        return (pct.fillna(0.0), "pre_close")

    open_price = pd.to_numeric(
        frame.get("open", pd.Series([0.0] * len(frame), index=frame.index)),
        errors="coerce",
    ).fillna(0.0)
    pct = ((close - open_price) / open_price.replace(0.0, pd.NA)) * 100.0
    return (pct.fillna(0.0), "open_close")


def _resolve_limit_type_series(limit_rows: pd.DataFrame) -> pd.Series:
    if limit_rows.empty:
        return pd.Series(dtype=str)
    if "limit_type" in limit_rows.columns:
        return limit_rows["limit_type"].astype(str).str.strip().str.upper()
    if "limit" in limit_rows.columns:
        return limit_rows["limit"].astype(str).str.strip().str.upper()
    return pd.Series([""] * len(limit_rows), index=limit_rows.index, dtype="object")


def _winsorized_median(series: pd.Series) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return 0.0
    lower = float(numeric.quantile(0.01))
    upper = float(numeric.quantile(0.99))
    return float(numeric.clip(lower=lower, upper=upper).median())


def _compute_amount_volatility(*, today_total_amount: float, recent_market_amounts: list[float]) -> tuple[float, str]:
    history = [float(value) for value in recent_market_amounts if float(value) > 0.0]
    if len(history) < 20:
        return (0.0, "cold_start")
    ma20_amount = float(sum(history[:20])) / 20.0
    if ma20_amount <= 0.0:
        return (0.0, "cold_start")
    volatility = (float(today_total_amount) - ma20_amount) / ma20_amount
    return (float(volatility), "normal")


def _load_recent_market_amounts(
    connection: duckdb.DuckDBPyConnection,
    *,
    trade_date: str,
    lookback_days: int = 20,
) -> list[float]:
    if not _table_exists(connection, "raw_daily"):
        return []
    frame = connection.execute(
        "SELECT CAST(trade_date AS VARCHAR) AS trade_date, "
        "SUM(COALESCE(amount, 0.0)) AS total_amount "
        "FROM raw_daily "
        "WHERE CAST(trade_date AS VARCHAR) < ? "
        "GROUP BY CAST(trade_date AS VARCHAR) "
        "ORDER BY trade_date DESC "
        "LIMIT ?",
        [trade_date, int(max(lookback_days, 1))],
    ).df()
    if frame.empty:
        return []
    amounts = pd.to_numeric(frame["total_amount"], errors="coerce").fillna(0.0).tolist()
    return [float(item) for item in amounts]


def _load_previous_industry_valuation_map(
    connection: duckdb.DuckDBPyConnection,
    *,
    trade_date: str,
) -> dict[str, tuple[float, float]]:
    if not _table_exists(connection, "industry_snapshot"):
        return {}
    row = connection.execute(
        "SELECT MAX(CAST(trade_date AS VARCHAR)) FROM industry_snapshot "
        "WHERE CAST(trade_date AS VARCHAR) < ?",
        [trade_date],
    ).fetchone()
    previous_trade_date = str(row[0] or "").strip() if row else ""
    if not previous_trade_date:
        return {}
    frame = connection.execute(
        "SELECT industry_code, industry_pe_ttm, industry_pb "
        "FROM industry_snapshot WHERE CAST(trade_date AS VARCHAR) = ?",
        [previous_trade_date],
    ).df()
    if frame.empty:
        return {}
    mapping: dict[str, tuple[float, float]] = {}
    for record in frame.to_dict("records"):
        industry_code = str(record.get("industry_code", "")).strip()
        if not industry_code:
            continue
        pe_value = pd.to_numeric(pd.Series([record.get("industry_pe_ttm")]), errors="coerce").iloc[0]
        pb_value = pd.to_numeric(pd.Series([record.get("industry_pb")]), errors="coerce").iloc[0]
        industry_pe_ttm = float(0.0 if pd.isna(pe_value) else pe_value)
        industry_pb = float(0.0 if pd.isna(pb_value) else pb_value)
        mapping[industry_code] = (industry_pe_ttm, industry_pb)
    return mapping


def _build_market_snapshot(
    *,
    trade_date: str,
    daily: pd.DataFrame,
    limit_list: pd.DataFrame,
    flat_threshold_ratio: float,
    recent_market_amounts: list[float],
) -> MarketSnapshot:
    working = daily.copy()
    for column in ("open", "close", "amount"):
        if column not in working.columns:
            working[column] = 0.0
        working[column] = pd.to_numeric(working[column], errors="coerce").fillna(0.0)

    pct, pct_source = _resolve_pct_chg_percent(working)
    total_amount = float(pd.to_numeric(working["amount"], errors="coerce").fillna(0.0).sum())
    amount_volatility, amount_quality = _compute_amount_volatility(
        today_total_amount=total_amount,
        recent_market_amounts=recent_market_amounts,
    )

    limit_rows = limit_list.copy() if not limit_list.empty else limit_list
    if not limit_rows.empty:
        limit_type_series = _resolve_limit_type_series(limit_rows)
        limit_up_count = int((limit_type_series == "U").sum())
        limit_down_count = int((limit_type_series == "D").sum())
        touched_limit_up = int(limit_type_series.isin({"U", "Z"}).sum())
    else:
        limit_up_count = 0
        limit_down_count = 0
        touched_limit_up = 0

    return MarketSnapshot(
        trade_date=trade_date,
        total_stocks=int(len(working)),
        rise_count=int((pct > 0.0).sum()),
        fall_count=int((pct < 0.0).sum()),
        flat_count=int((pct.abs() <= (flat_threshold_ratio * 100.0)).sum()),
        strong_up_count=int((pct >= 5.0).sum()),
        strong_down_count=int((pct <= -5.0).sum()),
        limit_up_count=limit_up_count,
        limit_down_count=limit_down_count,
        touched_limit_up=touched_limit_up,
        pct_chg_std=float(pct.std(ddof=0)),
        amount_volatility=float(amount_volatility),
        data_quality="normal" if pct_source == "pct_chg" and amount_quality == "normal" else "cold_start",
        stale_days=0,
        source_trade_date=trade_date,
    )


def _build_industry_snapshot_all(
    *,
    trade_date: str,
    daily: pd.DataFrame,
    limit_list: pd.DataFrame,
    flat_threshold_ratio: float,
) -> IndustrySnapshot:
    working = daily.copy()
    for column in ("open", "close", "amount", "vol"):
        if column not in working.columns:
            working[column] = 0.0
        working[column] = pd.to_numeric(working[column], errors="coerce").fillna(0.0)

    pct, _ = _resolve_pct_chg_percent(working)
    ranking = working.assign(pct=pct).sort_values("pct", ascending=False).head(5)
    top5_codes = [_normalize_stock_code(record) for record in ranking.to_dict("records")]
    top5_pct_chg = [float(round(float(value), 4)) for value in ranking["pct"]]

    limit_rows = limit_list.copy() if not limit_list.empty else limit_list
    if not limit_rows.empty:
        limit_type_series = _resolve_limit_type_series(limit_rows)
        limit_up_count = int((limit_type_series == "U").sum())
        limit_down_count = int((limit_type_series == "D").sum())
    else:
        limit_up_count = 0
        limit_down_count = 0

    return IndustrySnapshot(
        trade_date=trade_date,
        industry_code="ALL",
        industry_name="全市场聚合",
        stock_count=int(len(working)),
        rise_count=int((pct > 0.0).sum()),
        fall_count=int((pct < 0.0).sum()),
        flat_count=int((pct.abs() <= (flat_threshold_ratio * 100.0)).sum()),
        industry_close=float(working["close"].mean()),
        industry_pct_chg=float(pct.mean()),
        industry_amount=float(working["amount"].sum()),
        industry_turnover=float(working["vol"].sum()),
        market_amount_total=float(working["amount"].sum()),
        style_bucket="balanced",
        limit_up_count=limit_up_count,
        limit_down_count=limit_down_count,
        top5_codes=top5_codes,
        top5_pct_chg=top5_pct_chg,
        top5_limit_up=min(limit_up_count, len(top5_codes)),
        data_quality="normal",
        stale_days=0,
        source_trade_date=trade_date,
    )


def _normalize_member_stock_code(row: pd.Series) -> str:
    stock_code = _clean_text(row.get("stock_code", ""))
    if stock_code:
        return stock_code
    ts_code = _clean_text(row.get("ts_code", ""))
    if "." in ts_code:
        return ts_code.split(".", maxsplit=1)[0]
    con_code = _clean_text(row.get("con_code", ""))
    if "." in con_code:
        return con_code.split(".", maxsplit=1)[0]
    return ts_code or con_code


def _normalize_industry_code(row: pd.Series) -> str:
    return _clean_text(row.get("industry_code", ""))


def _is_member_active(row: pd.Series, trade_date: str) -> bool:
    in_date = _clean_text(row.get("in_date", ""))
    out_date = _clean_text(row.get("out_date", ""))
    start = in_date if len(in_date) == 8 and in_date.isdigit() else "00000000"
    end = out_date if len(out_date) == 8 and out_date.isdigit() else "99991231"
    return start <= trade_date <= end


def _load_sw31_classify(
    connection: duckdb.DuckDBPyConnection,
    *,
    trade_date: str,
) -> tuple[pd.DataFrame, str]:
    if not _table_exists(connection, "raw_index_classify"):
        return (pd.DataFrame.from_records([]), "")

    row = connection.execute(
        "SELECT MAX(CAST(trade_date AS VARCHAR)) FROM raw_index_classify "
        "WHERE CAST(trade_date AS VARCHAR) <= ? "
        "AND UPPER(COALESCE(src, '')) = ? "
        "AND UPPER(COALESCE(level, '')) = ?",
        [trade_date, SW31_SOURCE.upper(), SW31_LEVEL],
    ).fetchone()
    snapshot_trade_date = str(row[0] or "").strip() if row else ""
    if not snapshot_trade_date:
        return (pd.DataFrame.from_records([]), "")

    frame = connection.execute(
        "SELECT * FROM raw_index_classify "
        "WHERE CAST(trade_date AS VARCHAR) = ? "
        "AND UPPER(COALESCE(src, '')) = ? "
        "AND UPPER(COALESCE(level, '')) = ?",
        [snapshot_trade_date, SW31_SOURCE.upper(), SW31_LEVEL],
    ).df()
    if frame.empty:
        return (frame, snapshot_trade_date)

    normalized = frame.copy()
    normalized["index_code"] = normalized["index_code"].astype(str).str.strip()
    normalized["industry_code"] = normalized.apply(_normalize_industry_code, axis=1)
    normalized["industry_name"] = (
        normalized.get("industry_name", pd.Series([""] * len(normalized)))
        .astype(str)
        .str.strip()
    )
    normalized = normalized[
        (normalized["index_code"] != "")
        & normalized["industry_code"].astype(str).str.match(r"^\d{6}$")
    ].drop_duplicates(subset=["industry_code"], keep="first")
    return (normalized, snapshot_trade_date)


def _load_index_member(
    connection: duckdb.DuckDBPyConnection,
    *,
    trade_date: str,
) -> tuple[pd.DataFrame, str]:
    if not _table_exists(connection, "raw_index_member"):
        return (pd.DataFrame.from_records([]), "")

    month_prefix = f"{trade_date[:6]}%"
    row = connection.execute(
        "SELECT CAST(trade_date AS VARCHAR) AS trade_date, COUNT(*) AS row_count "
        "FROM raw_index_member "
        "WHERE CAST(trade_date AS VARCHAR) LIKE ? "
        "GROUP BY CAST(trade_date AS VARCHAR) "
        "ORDER BY row_count DESC, trade_date DESC LIMIT 1",
        [month_prefix],
    ).fetchone()
    snapshot_trade_date = str(row[0] or "").strip() if row else ""
    if not snapshot_trade_date:
        fallback = connection.execute(
            "SELECT MAX(CAST(trade_date AS VARCHAR)) FROM raw_index_member "
            "WHERE CAST(trade_date AS VARCHAR) <= ?",
            [trade_date],
        ).fetchone()
        snapshot_trade_date = str(fallback[0] or "").strip() if fallback else ""
    if not snapshot_trade_date:
        return (pd.DataFrame.from_records([]), "")

    frame = connection.execute(
        "SELECT * FROM raw_index_member WHERE CAST(trade_date AS VARCHAR) = ?",
        [snapshot_trade_date],
    ).df()
    if frame.empty:
        return (frame, snapshot_trade_date)

    normalized = frame.copy()
    normalized["index_code"] = normalized.get("index_code", pd.Series([""] * len(normalized))).astype(
        str
    ).str.strip()
    normalized["stock_code"] = normalized.apply(_normalize_member_stock_code, axis=1)
    normalized = normalized[
        (normalized["index_code"] != "") & (normalized["stock_code"] != "")
    ].drop_duplicates(subset=["index_code", "stock_code"], keep="last")
    return (normalized, snapshot_trade_date)


def _assign_style_bucket(frame: pd.DataFrame) -> pd.Series:
    style = pd.Series(["balanced"] * len(frame), index=frame.index, dtype="object")
    if frame.empty:
        return style

    pe = pd.to_numeric(frame.get("industry_pe_ttm", pd.Series([0.0] * len(frame))), errors="coerce").fillna(0.0)
    pb = pd.to_numeric(frame.get("industry_pb", pd.Series([0.0] * len(frame))), errors="coerce").fillna(0.0)
    composite = pe + pb
    valid = composite > 0.0
    if not valid.any():
        return style

    ranks = composite[valid].rank(method="average", pct=True)
    style.loc[ranks.index[ranks <= 1.0 / 3.0]] = "value"
    style.loc[ranks.index[ranks >= 2.0 / 3.0]] = "growth"
    return style


def _build_industry_snapshot_sw31(
    *,
    trade_date: str,
    daily: pd.DataFrame,
    limit_list: pd.DataFrame,
    daily_basic: pd.DataFrame,
    sw31_classify: pd.DataFrame,
    sw31_member: pd.DataFrame,
    classify_snapshot_trade_date: str,
    member_snapshot_trade_date: str,
    flat_threshold_ratio: float,
    previous_valuation_by_industry: dict[str, tuple[float, float]],
) -> tuple[list[IndustrySnapshot], dict[str, object]]:
    daily_working = daily.copy()
    for column in ("open", "close", "amount", "vol"):
        if column not in daily_working.columns:
            daily_working[column] = 0.0
        daily_working[column] = pd.to_numeric(daily_working[column], errors="coerce").fillna(0.0)

    daily_working["stock_code"] = daily_working.apply(_normalize_stock_code, axis=1)
    daily_working["pct"], _ = _resolve_pct_chg_percent(daily_working)
    market_amount_total = float(pd.to_numeric(daily_working["amount"], errors="coerce").fillna(0.0).sum())

    if sw31_classify.empty or sw31_member.empty:
        fallback = _build_industry_snapshot_all(
            trade_date=trade_date,
            daily=daily_working,
            limit_list=limit_list,
            flat_threshold_ratio=flat_threshold_ratio,
        )
        return (
            [fallback],
            {
                "uses_sw31": False,
                "reason": "sw31_mapping_source_missing",
                "classify_snapshot_trade_date": classify_snapshot_trade_date,
                "member_snapshot_trade_date": member_snapshot_trade_date,
                "mapped_stock_count": 0,
                "unmapped_stock_count": int(len(daily_working)),
                "mapping_coverage": 0.0,
                "industry_count": 1,
                "industry_codes": ["ALL"],
            },
        )

    classify = sw31_classify.copy()
    classify["index_code"] = classify["index_code"].astype(str).str.strip()
    classify["industry_code"] = classify["industry_code"].astype(str).str.strip()
    classify["industry_name"] = classify["industry_name"].astype(str).str.strip()
    classify = classify[
        (classify["index_code"] != "") & (classify["industry_code"] != "")
    ].drop_duplicates(subset=["industry_code"], keep="first")

    members = sw31_member.copy()
    members = members[members["index_code"].astype(str).isin(set(classify["index_code"].tolist()))]
    if "in_date" not in members.columns:
        members["in_date"] = ""
    if "out_date" not in members.columns:
        members["out_date"] = ""
    members = members[members.apply(lambda row: _is_member_active(row, trade_date), axis=1)]
    members = members.drop_duplicates(subset=["stock_code"], keep="first")
    members = members.merge(
        classify[["index_code", "industry_code", "industry_name"]],
        on="index_code",
        how="left",
    )
    members = members[members["industry_code"].astype(str) != ""]

    mapped = daily_working.merge(
        members[["stock_code", "industry_code", "industry_name"]],
        on="stock_code",
        how="left",
    )
    mapped_stock_count = int(mapped["industry_code"].notna().sum())
    unmapped_stock_count = int(len(mapped) - mapped_stock_count)
    mapping_coverage = float(mapped_stock_count) / max(float(len(mapped)), 1.0)

    limit_working = limit_list.copy() if not limit_list.empty else pd.DataFrame()
    if not limit_working.empty:
        limit_working["stock_code"] = limit_working.apply(_normalize_stock_code, axis=1)
        limit_working["limit_type"] = _resolve_limit_type_series(limit_working)
        limit_working = limit_working.merge(
            members[["stock_code", "industry_code"]],
            on="stock_code",
            how="left",
        )

    basic_working = daily_basic.copy() if not daily_basic.empty else pd.DataFrame()
    if not basic_working.empty:
        basic_working["stock_code"] = basic_working.apply(_normalize_stock_code, axis=1)
        for column in ("pe_ttm", "pb"):
            if column not in basic_working.columns:
                basic_working[column] = 0.0
            basic_working[column] = pd.to_numeric(basic_working[column], errors="coerce").fillna(0.0)
        basic_working = basic_working.merge(
            members[["stock_code", "industry_code"]],
            on="stock_code",
            how="left",
        )

    # 逐行业聚合是 SW31 语义口径的关键步骤，输出必须保持行业级可审计字段。
    row_dicts: list[dict[str, object]] = []
    for industry_row in classify.sort_values(["industry_code"]).itertuples(index=False):
        industry_code = str(industry_row.industry_code).strip()
        industry_name = str(industry_row.industry_name).strip() or industry_code
        subset = mapped[mapped["industry_code"].astype(str) == industry_code].copy()
        ranking = subset.sort_values("pct", ascending=False).head(5)
        # top5 采用当日涨幅排序，作为行业领涨强度与连板统计输入。
        top5_codes = [_normalize_stock_code(record) for record in ranking.to_dict("records")]
        top5_pct_chg = [float(round(float(value), 4)) for value in ranking["pct"]]

        if not limit_working.empty:
            limit_subset = limit_working[limit_working["industry_code"].astype(str) == industry_code]
            limit_up_count = int((limit_subset["limit_type"] == "U").sum())
            limit_down_count = int((limit_subset["limit_type"] == "D").sum())
        else:
            limit_up_count = 0
            limit_down_count = 0

        top5_set = set(top5_codes)
        if not limit_working.empty and top5_set:
            top5_limit_subset = limit_working[
                (limit_working["industry_code"].astype(str) == industry_code)
                & (limit_working["stock_code"].astype(str).isin(top5_set))
                & (limit_working["limit_type"] == "U")
            ]
            top5_limit_up = int(len(top5_limit_subset))
        else:
            top5_limit_up = 0

        previous_pe, previous_pb = previous_valuation_by_industry.get(industry_code, (0.0, 0.0))
        if not basic_working.empty:
            basic_subset = basic_working[basic_working["industry_code"].astype(str) == industry_code]
            valid_pe = pd.to_numeric(basic_subset["pe_ttm"], errors="coerce")
            valid_pe = valid_pe[(valid_pe > 0.0) & (valid_pe <= 1000.0)].dropna()
            if len(valid_pe) >= 8:
                industry_pe_ttm = _winsorized_median(valid_pe)
            else:
                industry_pe_ttm = float(previous_pe)

            valid_pb = pd.to_numeric(basic_subset["pb"], errors="coerce")
            valid_pb = valid_pb[(valid_pb > 0.0)].dropna()
            if len(valid_pb) >= 8:
                industry_pb = _winsorized_median(valid_pb)
            else:
                industry_pb = float(previous_pb)
        else:
            industry_pe_ttm = float(previous_pe)
            industry_pb = float(previous_pb)

        row_dicts.append(
            {
                "trade_date": trade_date,
                "industry_code": industry_code,
                "industry_name": industry_name,
                "stock_count": int(len(subset)),
                "rise_count": int((subset["pct"] > 0.0).sum()),
                "fall_count": int((subset["pct"] < 0.0).sum()),
                "flat_count": int((subset["pct"].abs() <= (flat_threshold_ratio * 100.0)).sum()),
                "industry_close": float(subset["close"].mean() or 0.0),
                "industry_pct_chg": float(subset["pct"].mean() if not subset.empty else 0.0),
                "industry_amount": float(subset["amount"].sum()),
                "industry_turnover": float(subset["vol"].sum()),
                "market_amount_total": market_amount_total,
                "style_bucket": "balanced",
                "industry_pe_ttm": industry_pe_ttm,
                "industry_pb": industry_pb,
                "limit_up_count": limit_up_count,
                "limit_down_count": limit_down_count,
                "new_100d_high_count": 0,
                "new_100d_low_count": 0,
                "top5_codes": top5_codes,
                "top5_pct_chg": top5_pct_chg,
                "top5_limit_up": top5_limit_up,
                "yesterday_limit_up_today_avg_pct": 0.0,
                "data_quality": "normal",
                "stale_days": 0,
                "source_trade_date": trade_date,
            }
        )

    industry_frame = pd.DataFrame.from_records(row_dicts)
    if industry_frame.empty:
        fallback = _build_industry_snapshot_all(
            trade_date=trade_date,
            daily=daily_working,
            limit_list=limit_list,
            flat_threshold_ratio=flat_threshold_ratio,
        )
        return (
            [fallback],
            {
                "uses_sw31": False,
                "reason": "sw31_mapping_result_empty",
                "classify_snapshot_trade_date": classify_snapshot_trade_date,
                "member_snapshot_trade_date": member_snapshot_trade_date,
                "mapped_stock_count": mapped_stock_count,
                "unmapped_stock_count": unmapped_stock_count,
                "mapping_coverage": mapping_coverage,
                "industry_count": 1,
                "industry_codes": ["ALL"],
            },
        )

    industry_frame["style_bucket"] = _assign_style_bucket(industry_frame)
    snapshots = [IndustrySnapshot(**row) for row in industry_frame.to_dict(orient="records")]
    return (
        snapshots,
        {
            "uses_sw31": True,
            "reason": "ok",
            "classify_snapshot_trade_date": classify_snapshot_trade_date,
            "member_snapshot_trade_date": member_snapshot_trade_date,
            "mapped_stock_count": mapped_stock_count,
            "unmapped_stock_count": unmapped_stock_count,
            "mapping_coverage": round(mapping_coverage, 6),
            "industry_count": int(len(industry_frame)),
            "industry_codes": sorted(industry_frame["industry_code"].astype(str).tolist()),
            "zero_stock_industries": int((industry_frame["stock_count"] <= 0).sum()),
        },
    )


def _persist_snapshot_table(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
) -> int:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database_path)) as connection:
        incoming = frame.copy()
        connection.register("incoming_df", incoming)
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} "
            "AS SELECT * FROM incoming_df WHERE 1=0"
        )
        existing_columns = {
            str(row[1]): str(row[2])
            for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        }
        for column in incoming.columns:
            if column in existing_columns:
                continue
            series = incoming[column]
            if pd.api.types.is_bool_dtype(series):
                column_type = "BOOLEAN"
            elif pd.api.types.is_integer_dtype(series):
                column_type = "BIGINT"
            elif pd.api.types.is_float_dtype(series):
                column_type = "DOUBLE"
            elif pd.api.types.is_datetime64_any_dtype(series):
                column_type = "TIMESTAMP"
            else:
                column_type = "VARCHAR"
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column} {column_type}"
            )

        table_columns = [
            str(row[1]) for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        ]
        aligned = incoming.copy()
        for column in table_columns:
            if column not in aligned.columns:
                aligned[column] = pd.NA
        aligned = aligned[table_columns]
        connection.unregister("incoming_df")
        connection.register("incoming_df", aligned)

        if "trade_date" in aligned.columns:
            connection.execute(
                f"DELETE FROM {table_name} WHERE CAST(trade_date AS VARCHAR) IN ("
                "SELECT DISTINCT CAST(trade_date AS VARCHAR) FROM incoming_df WHERE trade_date IS NOT NULL)"
            )
        connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_df")
        connection.unregister("incoming_df")
    return int(len(aligned))


def _write_sw_mapping_audit(path: Path, *, trade_date: str, strict_sw31: bool, payload: dict[str, object]) -> None:
    lines = [
        "# SW31 Mapping Audit",
        "",
        f"- trade_date: {trade_date}",
        f"- strict_sw31: {str(strict_sw31).lower()}",
        f"- uses_sw31: {str(bool(payload.get('uses_sw31', False))).lower()}",
        f"- reason: {str(payload.get('reason', ''))}",
        f"- classify_snapshot_trade_date: {str(payload.get('classify_snapshot_trade_date', ''))}",
        f"- member_snapshot_trade_date: {str(payload.get('member_snapshot_trade_date', ''))}",
        f"- mapped_stock_count: {int(payload.get('mapped_stock_count', 0) or 0)}",
        f"- unmapped_stock_count: {int(payload.get('unmapped_stock_count', 0) or 0)}",
        f"- mapping_coverage: {float(payload.get('mapping_coverage', 0.0) or 0.0):.4f}",
        f"- industry_count: {int(payload.get('industry_count', 0) or 0)}",
        f"- zero_stock_industries: {int(payload.get('zero_stock_industries', 0) or 0)}",
        "",
        "## Industry Codes",
    ]
    codes = payload.get("industry_codes", [])
    if isinstance(codes, list) and codes:
        lines.extend([f"- {str(code)}" for code in codes])
    else:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_l2_quality_gate_report(
    path: Path,
    *,
    decision_payload: dict[str, Any],
    report_rows: list[dict[str, Any]],
) -> None:
    lines = [
        "# L2 Quality Gate Report",
        "",
        f"- trade_date: {decision_payload.get('trade_date', '')}",
        f"- status: {decision_payload.get('status', '')}",
        f"- is_ready: {str(bool(decision_payload.get('is_ready', False))).lower()}",
        f"- coverage_ratio: {float(decision_payload.get('coverage_ratio', 0.0)):.4f}",
        f"- max_stale_days: {int(decision_payload.get('max_stale_days', 0) or 0)}",
        f"- cross_day_consistent: {str(bool(decision_payload.get('cross_day_consistent', False))).lower()}",
        "",
        "## Issues",
    ]
    issues = decision_payload.get("issues", [])
    if isinstance(issues, list) and issues:
        lines.extend([f"- {str(item)}" for item in issues])
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings"])
    warnings = decision_payload.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        lines.extend([f"- {str(item)}" for item in warnings])
    else:
        lines.append("- none")
    lines.extend(["", "## Checks"])
    for row in report_rows:
        lines.append(
            f"- {row.get('check_item', '')}: status={row.get('status', '')} "
            f"expected={row.get('expected_value', '')} actual={row.get('actual_value', '')} "
            f"action={row.get('action', '')}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_canary_report(
    *,
    path: Path,
    trade_date: str,
    market_snapshot_count: int,
    market_has_quality_fields: bool,
    industry_snapshot_count: int,
    errors: list[dict[str, str]],
) -> None:
    status = "PASS" if not errors else "FAIL"
    lines = [
        "# S0 Canary Report",
        "",
        f"- trade_date: {trade_date}",
        f"- status: {status}",
        f"- market_snapshot_count: {market_snapshot_count}",
        f"- industry_snapshot_count: {industry_snapshot_count}",
        f"- market_has_quality_fields: {str(market_has_quality_fields).lower()}",
        f"- error_count: {len(errors)}",
        "",
        "## Checks",
        f"- market_snapshot_exists: {'PASS' if market_snapshot_count > 0 else 'FAIL'}",
        f"- market_quality_fields: {'PASS' if market_has_quality_fields else 'FAIL'}",
        "",
        "## Errors",
    ]
    if not errors:
        lines.append("- none")
    else:
        for item in errors:
            lines.append(
                f"- [{item['error_level']}] {item['step']}: {item['message']}"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_l2_snapshot(
    *,
    trade_date: str,
    source: str,
    config: Config,
    strict_sw31: bool = True,
) -> L2RunResult:
    """执行单个交易日的 L2 快照生成。

    从 L1 表计算 MarketSnapshot + IndustrySnapshot，
    strict_sw31=True 时要求申万一级 31 个行业全覆盖，否则报错。
    """
    if source.lower() != "tushare":
        raise ValueError(f"unsupported source for S0c: {source}")

    artifacts_dir = Path("artifacts") / "spiral-s0c" / trade_date
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    parquet_root = Path(config.parquet_path) / "l2"
    thresholds = {
        "flat_threshold": float(config.flat_threshold),
        "min_coverage_ratio": float(config.min_coverage_ratio),
        "stale_hard_limit_days": int(config.stale_hard_limit_days),
    }
    quality_context_error = ""
    if database_path.exists():
        try:
            thresholds = init_quality_context(database_path, config=config)
        except Exception as exc:  # pragma: no cover - IO contention is environment-dependent
            quality_context_error = str(exc)
    flat_threshold_ratio = float(thresholds["flat_threshold"]) / 100.0
    min_coverage_ratio = float(thresholds["min_coverage_ratio"])
    stale_hard_limit_days = int(thresholds["stale_hard_limit_days"])
    errors: list[dict[str, str]] = []
    market_snapshot_count = 0
    industry_snapshot_count = 0
    market_has_quality_fields = False
    sw_audit_payload: dict[str, object] = {}
    recent_market_amounts: list[float] = []
    previous_valuation_by_industry: dict[str, tuple[float, float]] = {}

    def add_error(level: str, step: str, message: str) -> None:
        errors.append(
            {
                "error_level": level,
                "step": step,
                "trade_date": trade_date,
                "message": message,
            }
        )

    if quality_context_error:
        add_error("P1", "init_quality_context", f"quality_context_init_fallback:{quality_context_error}")

    try:
        if not database_path.exists():
            add_error("P0", "load_l1", "duckdb_not_found")
            raise RuntimeError("L1 database not found")

        with duckdb.connect(str(database_path), read_only=True) as connection:
            if not _table_exists(connection, "raw_daily"):
                add_error("P0", "load_l1", "raw_daily_table_missing")
                raise RuntimeError("raw_daily table missing")
            daily = connection.execute(
                "SELECT * FROM raw_daily WHERE trade_date = ?",
                [trade_date],
            ).df()
            if _table_exists(connection, "raw_limit_list"):
                limit_list = connection.execute(
                    "SELECT * FROM raw_limit_list WHERE trade_date = ?",
                    [trade_date],
                ).df()
            else:
                add_error("P1", "load_l1", "raw_limit_list_table_missing")
                limit_list = pd.DataFrame()
            if _table_exists(connection, "raw_daily_basic"):
                daily_basic = connection.execute(
                    "SELECT * FROM raw_daily_basic WHERE trade_date = ?",
                    [trade_date],
                ).df()
            else:
                daily_basic = pd.DataFrame()
            sw31_classify, classify_snapshot_trade_date = _load_sw31_classify(
                connection,
                trade_date=trade_date,
            )
            sw31_member, member_snapshot_trade_date = _load_index_member(
                connection,
                trade_date=trade_date,
            )
            recent_market_amounts = _load_recent_market_amounts(
                connection,
                trade_date=trade_date,
                lookback_days=20,
            )
            previous_valuation_by_industry = _load_previous_industry_valuation_map(
                connection,
                trade_date=trade_date,
            )

        if daily.empty:
            add_error("P0", "build_market_snapshot", "raw_daily_empty")
            raise RuntimeError("raw_daily is empty for trade_date")

        market_snapshot = _build_market_snapshot(
            trade_date=trade_date,
            daily=daily,
            limit_list=limit_list,
            flat_threshold_ratio=flat_threshold_ratio,
            recent_market_amounts=recent_market_amounts,
        )
        industry_snapshots, sw_audit_payload = _build_industry_snapshot_sw31(
            trade_date=trade_date,
            daily=daily,
            limit_list=limit_list,
            daily_basic=daily_basic,
            sw31_classify=sw31_classify,
            sw31_member=sw31_member,
            classify_snapshot_trade_date=classify_snapshot_trade_date,
            member_snapshot_trade_date=member_snapshot_trade_date,
            flat_threshold_ratio=flat_threshold_ratio,
            previous_valuation_by_industry=previous_valuation_by_industry,
        )

        market_frame = pd.DataFrame.from_records([market_snapshot.to_storage_record()])
        industry_frame = pd.DataFrame.from_records(
            [item.to_storage_record() for item in industry_snapshots]
        )

        market_snapshot_count = _persist_snapshot_table(
            database_path=database_path,
            table_name="market_snapshot",
            frame=market_frame,
        )
        industry_snapshot_count = _persist_snapshot_table(
            database_path=database_path,
            table_name="industry_snapshot",
            frame=industry_frame,
        )

        (parquet_root / "market_snapshot").mkdir(parents=True, exist_ok=True)
        market_frame.to_parquet(
            parquet_root / "market_snapshot" / f"{trade_date}.parquet", index=False,
        )
        (parquet_root / "industry_snapshot").mkdir(parents=True, exist_ok=True)
        industry_frame.to_parquet(
            parquet_root / "industry_snapshot" / f"{trade_date}.parquet", index=False,
        )

        artifacts_dir.mkdir(parents=True, exist_ok=True)
        market_frame.to_parquet(artifacts_dir / "market_snapshot_sample.parquet", index=False)
        industry_frame.to_parquet(
            artifacts_dir / "industry_snapshot_sample.parquet",
            index=False,
        )

        required_fields = {"data_quality", "stale_days", "source_trade_date"}
        market_has_quality_fields = required_fields <= set(market_frame.columns)
        if not market_has_quality_fields:
            add_error("P1", "gate", "market_snapshot_quality_fields_missing")

        if market_snapshot_count <= 0:
            add_error("P0", "gate", "market_snapshot_empty")
        if industry_snapshot_count <= 0:
            add_error("P0", "gate", "industry_snapshot_empty")

        if strict_sw31:
            industry_codes = set(industry_frame["industry_code"].astype(str).tolist())
            if "ALL" in industry_codes:
                add_error("P0", "gate", "sw31_contains_all_aggregate")
            if len(industry_codes) != SW31_EXPECTED_COUNT:
                add_error(
                    "P0",
                    "gate",
                    f"sw31_industry_count_invalid:{len(industry_codes)}",
                )
            if not bool(sw_audit_payload.get("uses_sw31", False)):
                add_error("P0", "gate", "sw31_mapping_source_missing")
    except Exception as exc:  # pragma: no cover - validated through contract tests
        add_error("P0", "run_l2_snapshot", str(exc))

    source_trade_dates = {
        "market_snapshot": trade_date,
        "industry_snapshot": trade_date,
    }
    coverage_ratio = (
        float(1 if market_snapshot_count > 0 else 0) + float(1 if industry_snapshot_count > 0 else 0)
    ) / 2.0
    quality_by_dataset = {
        "market_snapshot": "normal" if market_snapshot_count > 0 else "stale",
        "industry_snapshot": "normal" if industry_snapshot_count > 0 else "stale",
    }
    stale_days_by_dataset = {
        "market_snapshot": 0 if market_snapshot_count > 0 else 1,
        "industry_snapshot": 0 if industry_snapshot_count > 0 else 1,
    }
    decision = evaluate_data_quality_gate(
        trade_date=trade_date,
        coverage_ratio=coverage_ratio,
        source_trade_dates=source_trade_dates,
        quality_by_dataset=quality_by_dataset,
        stale_days_by_dataset=stale_days_by_dataset,
        min_coverage=min_coverage_ratio,
        stale_hard_limit=stale_hard_limit_days,
    )
    p0_messages = [
        f"{item.get('step', 'unknown')}:{item.get('message', '')}"
        for item in errors
        if str(item.get("error_level", "")) == "P0"
    ]
    if p0_messages:
        merged_issues = [*decision.issues, *p0_messages]
        decision = replace(
            decision,
            status=STATUS_BLOCKED,
            is_ready=False,
            issues=merged_issues,
        )
    if decision.status == STATUS_BLOCKED and not any(
        item.get("message") == "data_readiness_gate_blocked"
        for item in errors
    ):
        add_error("P0", "gate", "data_readiness_gate_blocked")

    report_rows: list[dict[str, Any]] = [
        {
            "check_item": "l2_market_snapshot_count",
            "expected_value": ">0",
            "actual_value": str(market_snapshot_count),
            "deviation": 0.0 if market_snapshot_count > 0 else 1.0,
            "status": "PASS" if market_snapshot_count > 0 else "FAIL",
            "gate_status": decision.status,
            "affected_layers": "L2",
            "action": "continue" if market_snapshot_count > 0 else "block",
        },
        {
            "check_item": "l2_industry_snapshot_count",
            "expected_value": ">0",
            "actual_value": str(industry_snapshot_count),
            "deviation": 0.0 if industry_snapshot_count > 0 else 1.0,
            "status": "PASS" if industry_snapshot_count > 0 else "FAIL",
            "gate_status": decision.status,
            "affected_layers": "L2",
            "action": "continue" if industry_snapshot_count > 0 else "block",
        },
    ]
    if strict_sw31:
        strict_ok = (
            bool(sw_audit_payload.get("uses_sw31", False))
            and int(sw_audit_payload.get("industry_count", 0) or 0) == SW31_EXPECTED_COUNT
            and ("ALL" not in set(sw_audit_payload.get("industry_codes", [])))
        )
        report_rows.append(
            {
                "check_item": "l2_sw31_strict_gate",
                "expected_value": "industry_count=31 & no_ALL",
                "actual_value": (
                    f"industry_count={int(sw_audit_payload.get('industry_count', 0) or 0)}, "
                    f"uses_sw31={str(bool(sw_audit_payload.get('uses_sw31', False))).lower()}"
                ),
                "deviation": 0.0 if strict_ok else 1.0,
                "status": "PASS" if strict_ok else "FAIL",
                "gate_status": decision.status,
                "affected_layers": "L2",
                "action": "continue" if strict_ok else "block",
            }
        )
    report_rows.append(
        {
            "check_item": "l2_readiness_gate",
            "expected_value": "ready/degraded",
            "actual_value": decision.status,
            "deviation": max(0.0, min_coverage_ratio - coverage_ratio),
            "status": "PASS" if decision.status == "ready" else ("WARN" if decision.status == "degraded" else "FAIL"),
            "gate_status": decision.status,
            "affected_layers": "L2",
            "action": "continue" if decision.is_ready else "block",
        }
    )
    persist_quality_outputs(
        database_path,
        decision=decision,
        report_rows=report_rows,
        config=config,
    )
    _write_l2_quality_gate_report(
        artifacts_dir / "l2_quality_gate_report.md",
        decision_payload=decision_to_json(decision),
        report_rows=report_rows,
    )

    canary_report_path = artifacts_dir / "s0_canary_report.md"
    _write_canary_report(
        path=canary_report_path,
        trade_date=trade_date,
        market_snapshot_count=market_snapshot_count,
        market_has_quality_fields=market_has_quality_fields,
        industry_snapshot_count=industry_snapshot_count,
        errors=errors,
    )

    error_manifest_payload = {
        "trade_date": trade_date,
        "source": source,
        "error_count": len(errors),
        "errors": errors,
    }
    sample_path = artifacts_dir / "error_manifest_sample.json"
    _write_json(sample_path, error_manifest_payload)
    if errors:
        manifest_path = artifacts_dir / "error_manifest.json"
        _write_json(manifest_path, error_manifest_payload)
    else:
        manifest_path = sample_path

    if sw_audit_payload:
        s3c_artifacts_dir = Path("artifacts") / "spiral-s3c" / trade_date
        s3c_artifacts_dir.mkdir(parents=True, exist_ok=True)
        if industry_snapshot_count > 0 and database_path.exists():
            with duckdb.connect(str(database_path), read_only=True) as connection:
                if _table_exists(connection, "industry_snapshot"):
                    snapshot_frame = connection.execute(
                        "SELECT * FROM industry_snapshot WHERE trade_date = ? ORDER BY industry_code",
                        [trade_date],
                    ).df()
                    if not snapshot_frame.empty:
                        snapshot_frame.to_parquet(
                            s3c_artifacts_dir / "industry_snapshot_sw31_sample.parquet",
                            index=False,
                        )
        _write_sw_mapping_audit(
            s3c_artifacts_dir / "sw_mapping_audit.md",
            trade_date=trade_date,
            strict_sw31=strict_sw31,
            payload=sw_audit_payload,
        )

    return L2RunResult(
        trade_date=trade_date,
        source=source,
        artifacts_dir=artifacts_dir,
        market_snapshot_count=market_snapshot_count,
        industry_snapshot_count=industry_snapshot_count,
        has_error=bool(errors),
        error_manifest_path=manifest_path,
        canary_report_path=canary_report_path,
    )
