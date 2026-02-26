"""Validation 生产级 IC/ICIR 校准基线模块。

提供基于真实 pct_chg 收益序列的 IC/ICIR 校准能力，
产出可审计的校准报告 JSON 产物。

DESIGN_TRACE:
- docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md (§3 阈值, §4 输出)
- docs/design/core-algorithms/validation/factor-weight-validation-data-models.md (§3 ValidationConfig)
- Governance/SpiralRoadmap/execution-cards/DEBT-CARD-C-BACKLOG.md (TD-S0-002)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import duckdb
import pandas as pd

from src.config.config import Config
from src.db.helpers import table_exists as _table_exists

DESIGN_TRACE = {
    "validation_algorithm": "docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md",
    "validation_data_models": "docs/design/core-algorithms/validation/factor-weight-validation-data-models.md",
    "debt_card_c": "Governance/SpiralRoadmap/execution-cards/DEBT-CARD-C-BACKLOG.md",
}


@dataclass(frozen=True)
class CalibrationResult:
    """IC/ICIR 校准基线报告。"""

    trade_date: str
    lookback_days: int
    sample_count: int
    ic_mean: float
    ic_std: float
    icir: float
    rank_ic_mean: float
    rank_ic_std: float
    rank_icir: float
    return_source: str
    calibration_gate: str
    tolerance_ic: float
    tolerance_icir: float
    report_path: Path


def _safe_corr(left: pd.Series, right: pd.Series, method: str = "pearson") -> float:
    """安全计算相关系数，样本不足时返回 0.0。"""
    frame = pd.DataFrame({"left": left, "right": right}).dropna()
    if len(frame) < 2:
        return 0.0
    corr = frame["left"].corr(frame["right"], method=method)
    if pd.isna(corr):
        return 0.0
    return float(corr)


def _load_calibration_series(
    *,
    database_path: Path,
    trade_date: str,
    lookback_days: int,
) -> tuple[pd.DataFrame, str]:
    """加载 MSS 因子值与真实收益序列。

    从 mss_panorama + raw_daily 联合查询。
    优先使用 pct_chg 列；若不存在则从 close 计算日度收益率。
    返回 (DataFrame[trade_date, mss_score, market_pct_chg], return_source)。
    """
    empty = pd.DataFrame(columns=["trade_date", "mss_score", "market_pct_chg"])
    if not database_path.exists():
        return empty, "real_pct_chg"

    with duckdb.connect(str(database_path), read_only=True) as conn:
        has_mss = _table_exists(conn, "mss_panorama")
        has_daily = _table_exists(conn, "raw_daily")
        if not has_mss or not has_daily:
            return empty, "real_pct_chg"

        # 检查 raw_daily 是否有 pct_chg 列（模拟客户端可能无此列）
        cols = {str(r[0]) for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'raw_daily'"
        ).fetchall()}
        use_pct_chg = "pct_chg" in cols
        if use_pct_chg:
            return_expr = "AVG(CAST(pct_chg AS DOUBLE))"
            where_clause = "WHERE pct_chg IS NOT NULL"
        else:
            # 回退：从 close 列计算市场平均收盘价，外层再算日度收益率
            return_expr = "AVG(CAST(close AS DOUBLE))"
            where_clause = "WHERE close IS NOT NULL"

        frame = conn.execute(
            "WITH market_return AS ("
            f"  SELECT CAST(trade_date AS VARCHAR) AS trade_date, "
            f"         {return_expr} AS market_pct_chg "
            f"  FROM raw_daily "
            f"  {where_clause} "
            "  GROUP BY trade_date"
            "), mss_daily AS ("
            "  SELECT CAST(trade_date AS VARCHAR) AS trade_date, "
            "         MAX(mss_score) AS mss_score "
            "  FROM mss_panorama "
            "  WHERE CAST(trade_date AS VARCHAR) <= ? "
            "  GROUP BY trade_date "
            "  ORDER BY trade_date DESC "
            "  LIMIT ?"
            ") "
            "SELECT m.trade_date, m.mss_score, r.market_pct_chg "
            "FROM mss_daily m "
            "LEFT JOIN market_return r ON m.trade_date = r.trade_date "
            "WHERE r.market_pct_chg IS NOT NULL "
            "ORDER BY m.trade_date",
            [trade_date, int(max(lookback_days, 10))],
        ).df()

    return_source = "real_pct_chg" if use_pct_chg else "close_derived"

    if frame.empty:
        return empty, return_source

    work = frame.copy().reset_index(drop=True)
    work["mss_score"] = pd.to_numeric(work["mss_score"], errors="coerce")
    work["market_pct_chg"] = pd.to_numeric(work["market_pct_chg"], errors="coerce")

    if not use_pct_chg:
        # 从平均 close 序列计算日度收益率
        work["market_pct_chg"] = work["market_pct_chg"].pct_change() * 100.0
        work = work.iloc[1:]  # 首行无前值

    return work.dropna(subset=["mss_score", "market_pct_chg"]).reset_index(drop=True), return_source


def calibrate_ic_baseline(
    *,
    trade_date: str,
    config: Config,
    lookback_days: int = 60,
    artifacts_dir: Path | None = None,
    tolerance_ic: float = 0.02,
    tolerance_icir: float = 0.10,
) -> CalibrationResult:
    """执行 IC/ICIR 校准基线，产出可审计报告。

    流程：
    1. 加载 MSS 因子 + 真实 pct_chg 收益序列（lookback 窗口）
    2. 逐日计算截面 IC（pearson）与 Rank IC（spearman）
    3. 汇总 IC_mean / IC_std / ICIR / Rank_IC_mean / Rank_IC_std / Rank_ICIR
    4. 与容差阈值对比，输出 PASS / WARN / FAIL 判定
    5. 写入 JSON 校准报告
    """
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"

    series, return_source = _load_calibration_series(
        database_path=database_path,
        trade_date=trade_date,
        lookback_days=lookback_days,
    )

    sample_count = len(series)

    if sample_count < 5:
        # 样本不足，无法产出有意义的校准结论
        ic_mean = 0.0
        ic_std = 0.0
        icir = 0.0
        rank_ic_mean = 0.0
        rank_ic_std = 0.0
        rank_icir = 0.0
        gate = "WARN"
    else:
        # 计算整体 IC 与 Rank IC
        mss_scores = series["mss_score"]
        market_returns = series["market_pct_chg"]

        # 滚动日级 IC（每 5 日一个窗口滑动）
        window_size = min(5, sample_count)
        ic_values: list[float] = []
        rank_ic_values: list[float] = []

        for i in range(window_size, sample_count + 1):
            window_mss = mss_scores.iloc[i - window_size : i]
            window_ret = market_returns.iloc[i - window_size : i]
            ic_values.append(_safe_corr(window_mss, window_ret, "pearson"))
            rank_ic_values.append(_safe_corr(window_mss, window_ret, "spearman"))

        ic_series = pd.Series(ic_values)
        rank_ic_series = pd.Series(rank_ic_values)

        ic_mean = float(ic_series.mean()) if not ic_series.empty else 0.0
        ic_std = float(ic_series.std(ddof=1)) if len(ic_series) > 1 else 0.0
        icir = ic_mean / max(ic_std, 0.001) if ic_std > 0 else 0.0

        rank_ic_mean = float(rank_ic_series.mean()) if not rank_ic_series.empty else 0.0
        rank_ic_std = float(rank_ic_series.std(ddof=1)) if len(rank_ic_series) > 1 else 0.0
        rank_icir = rank_ic_mean / max(rank_ic_std, 0.001) if rank_ic_std > 0 else 0.0

        # 校准判定
        if abs(ic_mean) >= tolerance_ic and abs(icir) >= tolerance_icir:
            gate = "PASS"
        elif abs(ic_mean) >= tolerance_ic * 0.5 or abs(icir) >= tolerance_icir * 0.5:
            gate = "WARN"
        else:
            gate = "FAIL"

    # 写入校准报告
    target_dir = artifacts_dir or (Path("artifacts") / "calibration" / trade_date)
    target_dir.mkdir(parents=True, exist_ok=True)
    report_path = target_dir / "ic_calibration_baseline.json"

    report_payload = {
        "trade_date": trade_date,
        "lookback_days": lookback_days,
        "sample_count": sample_count,
        "return_source": return_source,
        "ic_mean": round(ic_mean, 6),
        "ic_std": round(ic_std, 6),
        "icir": round(icir, 6),
        "rank_ic_mean": round(rank_ic_mean, 6),
        "rank_ic_std": round(rank_ic_std, 6),
        "rank_icir": round(rank_icir, 6),
        "tolerance_ic": tolerance_ic,
        "tolerance_icir": tolerance_icir,
        "calibration_gate": gate,
        "contract_version": "nc-v1",
        "created_at": pd.Timestamp.utcnow().isoformat(),
    }
    report_path.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return CalibrationResult(
        trade_date=trade_date,
        lookback_days=lookback_days,
        sample_count=sample_count,
        ic_mean=round(ic_mean, 6),
        ic_std=round(ic_std, 6),
        icir=round(icir, 6),
        rank_ic_mean=round(rank_ic_mean, 6),
        rank_ic_std=round(rank_ic_std, 6),
        rank_icir=round(rank_icir, 6),
        return_source=return_source,
        calibration_gate=gate,
        tolerance_ic=tolerance_ic,
        tolerance_icir=tolerance_icir,
        report_path=report_path,
    )
