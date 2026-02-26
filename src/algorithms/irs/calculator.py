"""IRS Calculator 接口抽象（TD-DA-001 跟进）。

将行业轮动评分逻辑从编排中解耦，便于测试替换与后续推广。

DESIGN_TRACE:
- docs/design/core-algorithms/irs/irs-algorithm.md (§3 六因子, §5 轮动状态)
- Governance/SpiralRoadmap/execution-cards/DEBT-CARD-B-CONTRACT.md (§2 TD-DA-001)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd

from src.algorithms.irs.pipeline import (
    FACTOR_WEIGHTS,
    _allocation_advice,
    _clip,
    _concentration_level,
    _parse_json_list,
    _rotation_detail,
    _rotation_status,
    _score_with_history,
    _series_mean_std,
    _to_recommendation,
)

DESIGN_TRACE = {
    "irs_algorithm": "docs/design/core-algorithms/irs/irs-algorithm.md",
    "debt_card_b": "Governance/SpiralRoadmap/execution-cards/DEBT-CARD-B-CONTRACT.md",
}


@runtime_checkable
class IrsCalculator(Protocol):
    """IRS 行业评分接口协议。

    输入：行业快照 DataFrame（当日 + 历史）、基线参数。
    输出：评分后的 DataFrame（含 industry_score 等字段）。
    """

    def score(
        self,
        source: pd.DataFrame,
        history: pd.DataFrame,
        *,
        trade_date: str,
        baseline_map: dict[str, tuple[float, float]] | None = None,
        benchmark_history: pd.DataFrame | None = None,
        irs_history: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """对所有行业执行六因子评分，返回结果 DataFrame。"""
        ...


class DefaultIrsCalculator:
    """默认 IRS 评分实现（可独立运行的轻量抽取）。"""

    def score(
        self,
        source: pd.DataFrame,
        history: pd.DataFrame,
        *,
        trade_date: str,
        baseline_map: dict[str, tuple[float, float]] | None = None,
        benchmark_history: pd.DataFrame | None = None,
        irs_history: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        if source.empty:
            return pd.DataFrame.from_records([])

        baseline = baseline_map or {}
        benchmark_map = (
            benchmark_history.set_index("trade_date")["pct_chg"].to_dict()
            if benchmark_history is not None
            and not benchmark_history.empty
            and {"trade_date", "pct_chg"} <= set(benchmark_history.columns)
            else {}
        )

        work_history = history.copy()
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
            if column not in work_history.columns:
                work_history[column] = 0.0
            work_history[column] = pd.to_numeric(work_history[column], errors="coerce").fillna(0.0)

        market_amount_by_date = (
            work_history.groupby("trade_date")["industry_amount"].sum().to_dict()
            if not work_history.empty
            else {}
        )

        score_history_by_industry: dict[str, list[float]] = {}
        if irs_history is not None and not irs_history.empty:
            local_hist = irs_history.copy()
            if "industry_score" not in local_hist.columns and "irs_score" in local_hist.columns:
                local_hist["industry_score"] = local_hist["irs_score"]
            for tup in local_hist.itertuples(index=False):
                code = str(getattr(tup, "industry_code", "")).strip()
                if not code:
                    continue
                score_history_by_industry.setdefault(code, []).append(
                    float(getattr(tup, "industry_score", 0.0) or 0.0)
                )

        output_rows: list[dict[str, object]] = []
        for row in source.itertuples(index=False):
            item = row._asdict()
            industry_code = str(item.get("industry_code", "UNKNOWN") or "UNKNOWN")
            industry_name = str(item.get("industry_name", "未知行业") or "未知行业")
            industry_hist = work_history[work_history["industry_code"].astype(str) == industry_code].copy()
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
            amount_avg_20 = amount_series.rolling(window=20, min_periods=1).mean().clip(lower=1e-9)
            relative_volume = amount_series / amount_avg_20

            market_amount_total = industry_hist["trade_date"].map(market_amount_by_date).fillna(amount_series)
            flow_share = amount_series / market_amount_total.clip(lower=1e-9)
            flow_share_mean_20 = flow_share.rolling(window=20, min_periods=1).mean().clip(lower=1e-9)
            crowding_ratio = flow_share / flow_share_mean_20

            net_inflow_10d = amount_delta.rolling(window=10, min_periods=1).sum()
            net_inflow_score, _, _ = _score_with_history(
                value=float(net_inflow_10d.iloc[-1]),
                history_series=net_inflow_10d,
                baseline_map=baseline,
                baseline_key="irs_capital_flow_net_inflow_10d",
            )
            flow_share_score, _, _ = _score_with_history(
                value=float(flow_share.iloc[-1]),
                history_series=flow_share,
                baseline_map=baseline,
                baseline_key="irs_capital_flow_flow_share",
            )
            relative_volume_score, _, _ = _score_with_history(
                value=float(relative_volume.iloc[-1]),
                history_series=relative_volume,
                baseline_map=baseline,
                baseline_key="irs_capital_flow_relative_volume",
            )
            crowding_penalty = 6.0 * max(float(crowding_ratio.iloc[-1]) - 1.2, 0.0)
            capital_flow_score = _clip(
                0.5 * net_inflow_score + 0.3 * flow_share_score + 0.2 * relative_volume_score - crowding_penalty,
                0.0,
                100.0,
            )

            pe_series = pd.to_numeric(industry_hist["industry_pe_ttm"], errors="coerce").fillna(0.0)
            pb_series = pd.to_numeric(industry_hist["industry_pb"], errors="coerce").fillna(0.0)
            valuation_raw_series = 0.5 * (-pe_series) + 0.5 * (-pb_series)
            valuation_raw = float(valuation_raw_series.iloc[-1])

            top5_limit_ratio = pd.to_numeric(industry_hist["top5_limit_up"], errors="coerce").fillna(0.0) / 5.0
            top5_pct_avg = industry_hist["top5_pct_chg"].map(lambda v: (sum(_parse_json_list(v)) / max(len(_parse_json_list(v)), 1)))
            leader_raw_series = 0.6 * top5_pct_avg + 0.4 * top5_limit_ratio
            leader_raw = float(leader_raw_series.iloc[-1])

            gene_limit_ratio = pd.to_numeric(industry_hist["limit_up_count"], errors="coerce").fillna(0.0) / stock_count
            gene_high_ratio = pd.to_numeric(industry_hist["new_100d_high_count"], errors="coerce").fillna(0.0) / stock_count
            gene_raw_series = (
                0.6 * gene_limit_ratio.ewm(alpha=0.1, adjust=False).mean()
                + 0.4 * gene_high_ratio.ewm(alpha=0.1, adjust=False).mean()
            )
            gene_raw = float(gene_raw_series.iloc[-1])

            relative_strength_score, _, _ = _score_with_history(
                value=relative_strength_raw,
                history_series=relative_strength_raw_series,
                baseline_map=baseline,
                baseline_key="irs_relative_strength_raw",
            )
            continuity_score, _, _ = _score_with_history(
                value=continuity_raw,
                history_series=continuity_raw_series,
                baseline_map=baseline,
                baseline_key="irs_continuity_raw",
            )
            valuation_score, _, _ = _score_with_history(
                value=valuation_raw,
                history_series=valuation_raw_series,
                baseline_map=baseline,
                baseline_key="irs_valuation_raw",
            )
            leader_score, _, _ = _score_with_history(
                value=leader_raw,
                history_series=leader_raw_series,
                baseline_map=baseline,
                baseline_key="irs_leader_raw",
            )
            gene_score, _, _ = _score_with_history(
                value=gene_raw,
                history_series=gene_raw_series,
                baseline_map=baseline,
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

            output_rows.append(
                {
                    "trade_date": trade_date,
                    "industry_code": industry_code,
                    "industry_name": industry_name,
                    "industry_score": industry_score,
                    "irs_score": industry_score,
                    "sample_days": sample_days,
                    "relative_strength": round(relative_strength_score, 4),
                    "continuity_factor": round(continuity_score, 4),
                    "capital_flow": round(capital_flow_score, 4),
                    "valuation": round(valuation_score, 4),
                    "leader_score": round(leader_score, 4),
                    "gene_score": round(gene_score, 4),
                    "quality_flag": "cold_start" if sample_days < 60 else "normal",
                    "stale_days": int(float(item.get("stale_days", 0) or 0)),
                }
            )

        frame = pd.DataFrame.from_records(output_rows)
        if frame.empty:
            return frame

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

        rotation_statuses: list[str] = []
        rotation_slopes: list[float] = []
        rotation_details: list[str] = []
        for tup in frame.itertuples(index=False):
            code = str(tup.industry_code)
            score_hist = score_history_by_industry.get(code, []) + [float(tup.industry_score)]
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
        return frame
