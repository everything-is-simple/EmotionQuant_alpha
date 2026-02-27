"""PAS（个股活跃度评分）流水线：三因子评分 + 方向 + 机会等级。

对应执行卡 S2A / S2C。三因子：
  1. momentum_score  — 动量（涨跌幅 + 历史分位 + 新高/新低距离）
  2. volume_score    — 量能（换手率 + 量比 + 量价背离 + 涨停封单）
  3. pattern_score   — 形态（K线形态 + 连续涨跌 + 上下影线）

输出: pas_stock_daily 表 + pas_factor_intermediate 表。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from src.config.config import Config
from src.db.helpers import (
    duckdb_type as _duckdb_type,
    ensure_columns as _ensure_columns,
    persist_by_trade_date as _persist,
    table_exists as _table_exists,
)
from src.models.enums import PasDirection

# DESIGN_TRACE:
# - docs/design/core-algorithms/pas/pas-algorithm.md (3 三因子, 5 方向, 6 RR)
# - docs/design/core-algorithms/pas/pas-data-models.md (3 输出模型, 4 中间表)
# - Governance/SpiralRoadmap/execution-cards/S2C-EXECUTION-CARD.md (3 PAS, 6 artifact)
DESIGN_TRACE = {
    "pas_algorithm": "docs/design/core-algorithms/pas/pas-algorithm.md",
    "pas_data_models": "docs/design/core-algorithms/pas/pas-data-models.md",
    "s2c_execution_card": "Governance/SpiralRoadmap/execution-cards/S2C-EXECUTION-CARD.md",
}

SUPPORTED_CONTRACT_VERSION = "nc-v1"
EPS = 1e-9


@dataclass(frozen=True)
class PasRunResult:
    trade_date: str
    count: int
    frame: pd.DataFrame
    factor_intermediate_frame: pd.DataFrame
    factor_intermediate_sample_path: Path




def _clip(value: float, low: float, high: float) -> float:
    return float(max(low, min(high, value)))


def _to_opportunity_grade(score: float) -> str:
    if score >= 85.0:
        return "S"
    if score >= 70.0:
        return "A"
    if score >= 55.0:
        return "B"
    if score >= 40.0:
        return "C"
    return "D"


def _choose_adaptive_window(volatility_20d: float, turnover_rate: float, window_mode: str) -> int:
    if window_mode == "fixed":
        return 60
    if volatility_20d >= 0.045 or turnover_rate >= 8.0:
        return 20
    if volatility_20d <= 0.020 and turnover_rate <= 3.0:
        return 120
    return 60


def _consecutive_count(flags: pd.Series) -> int:
    count = 0
    for value in reversed(flags.tolist()):
        if not bool(value):
            break
        count += 1
    return count


def _score_from_history(value: float, series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return 50.0
    mean = float(values.tail(120).mean())
    std = float(values.tail(120).std(ddof=0))
    if abs(std) <= EPS:
        return 50.0
    z = (float(value) - mean) / std
    return _clip(((z + 3.0) / 6.0) * 100.0, 0.0, 100.0)


def _series_clip(series: pd.Series, low: float, high: float) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0).clip(lower=low, upper=high)


def _coalesce_float(value: float | int | None, fallback: float) -> float:
    if value is None:
        return float(fallback)
    number = float(value)
    if pd.isna(number):
        return float(fallback)
    return number


def _limit_up_pct(stock_code: str, name: str = "") -> float:
    """按板块返回涨跌停幅度（铁律#5）。

    主板 10% / 创业板·科创板 20% / ST 5%。
    """
    if name and ("ST" in name.upper()):
        return 0.05
    prefix = stock_code[:3] if len(stock_code) >= 3 else ""
    if prefix in ("300", "301"):
        return 0.20
    if prefix in ("688", "689"):
        return 0.20
    return 0.10


# ---------------------------------------------------------------------------
# 向量化辅助
# ---------------------------------------------------------------------------

def _vec_zscore(values: np.ndarray, means: np.ndarray, stds: np.ndarray) -> np.ndarray:
    """向量化 z-score → 0-100 评分，与 _score_from_history 语义一致。"""
    valid = np.abs(stds) > EPS
    z = np.where(valid, (values - means) / np.maximum(np.abs(stds), EPS), 0.0)
    scores = np.clip(((z + 3.0) / 6.0) * 100.0, 0.0, 100.0)
    return np.where(valid, scores, 50.0)


def _vec_consecutive_at_end(pct_chg_arr: np.ndarray, positive: bool) -> int:
    """统计数组末尾连续满足条件的天数。"""
    flags = pct_chg_arr > 0.0 if positive else pct_chg_arr < 0.0
    if len(flags) == 0 or not flags[-1]:
        return 0
    fp = np.where(~flags)[0]
    return int(len(flags) - 1 - fp[-1]) if len(fp) > 0 else int(len(flags))


def _grp_transform(g, col: str, window: int, stat: str) -> pd.Series:
    """groupby().transform 快捷封装。"""
    if stat == "mean":
        return g[col].transform(lambda x: x.rolling(window, min_periods=1).mean())
    if stat == "max":
        return g[col].transform(lambda x: x.rolling(window, min_periods=1).max())
    if stat == "min":
        return g[col].transform(lambda x: x.rolling(window, min_periods=1).min())
    if stat == "std0":
        return g[col].transform(
            lambda x: x.rolling(window, min_periods=1).std(ddof=0)
        ).fillna(0.0)
    raise ValueError(f"unsupported stat: {stat}")


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def run_pas_daily(
    *,
    trade_date: str,
    config: Config,
    artifacts_dir: Path | None = None,
) -> PasRunResult:
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not database_path.exists():
        raise FileNotFoundError("duckdb_not_found")

    with duckdb.connect(str(database_path), read_only=True) as connection:
        if not _table_exists(connection, "raw_daily"):
            raise ValueError("raw_daily_table_missing")

        _cols = "ts_code, stock_code, trade_date, open, high, low, close, vol, amount"
        source = connection.execute(
            f"SELECT {_cols} FROM raw_daily WHERE trade_date = ? ORDER BY stock_code",
            [trade_date],
        ).df()
        # 性能优化：仅拉取最近 150 个交易日（覆盖 max rolling window 120 + 30 安全余量）
        lookback_dates = connection.execute(
            "SELECT DISTINCT trade_date FROM raw_daily WHERE trade_date <= ? ORDER BY trade_date DESC LIMIT 150",
            [trade_date],
        ).fetchall()
        if lookback_dates:
            earliest = lookback_dates[-1][0]
            _hist_cols = "stock_code, trade_date, open, high, low, close, vol, amount"
            history = connection.execute(
                f"SELECT {_hist_cols} FROM raw_daily WHERE trade_date >= ? AND trade_date <= ?"
                " ORDER BY trade_date, stock_code",
                [earliest, trade_date],
            ).df()
        else:
            history = source.copy()

    if source.empty:
        raise ValueError("raw_daily_empty_for_trade_date")

    for column in ("open", "high", "low", "close", "vol", "amount"):
        if column not in source.columns:
            source[column] = 0.0
        source[column] = pd.to_numeric(source[column], errors="coerce").fillna(0.0)

        if column not in history.columns:
            history[column] = 0.0
        history[column] = pd.to_numeric(history[column], errors="coerce").fillna(0.0)

    # ===================================================================
    # 向量化计算（pivot-based rolling，消除 groupby.transform 瓶颈）
    # ===================================================================
    created_at = pd.Timestamp.utcnow().isoformat()

    # --- 1. 源数据元信息 ---
    source["_sc"] = source["stock_code"].astype(str).str.strip()
    _idx = source["_sc"].values
    _ts_col = (
        source["ts_code"].astype(str).str.strip()
        if "ts_code" in source.columns
        else pd.Series([""] * len(source), index=source.index)
    )
    _name_col = (
        source["name"].fillna("").astype(str).str.strip()
        if "name" in source.columns
        else pd.Series([""] * len(source), index=source.index)
    )

    # 涨跌停幅度向量化（铁律#5：主板10%/创业板·科创板20%/ST 5%）
    _codes_arr = _idx.astype(str)
    _names_arr = _name_col.values.astype(str)
    _bl = np.full(len(source), 0.10)
    _st_mask = np.array(["ST" in n.upper() for n in _names_arr])
    _gem_mask = np.array(
        [len(c) >= 3 and c[:3] in ("300", "301", "688", "689") for c in _codes_arr]
    )
    _bl[_st_mask] = 0.05
    _bl[~_st_mask & _gem_mask] = 0.20
    _blt = _bl - 0.005  # 涨停判定阈值（留 0.5% 容差）
    _blt_ser = pd.Series(dict(zip(_idx, _blt)))  # stock_code → threshold

    _stale_arr = (
        pd.to_numeric(source["stale_days"], errors="coerce").fillna(0).astype(int).values
        if "stale_days" in source.columns
        else np.zeros(len(source), dtype=int)
    )

    # --- 2. Pivot 历史数据到宽表（trade_date × stock_code）---
    history["_sc"] = history["stock_code"].astype(str).str.strip()
    hist = history.set_index(["trade_date", "_sc"]).sort_index()
    # 仅保留当日存在的股票
    _source_set = set(_idx)
    hist = hist.loc[hist.index.get_level_values("_sc").isin(_source_set)]

    def _unstack(col: str) -> pd.DataFrame:
        return hist[col].unstack(level="_sc")

    wc = _unstack("close")
    wh = _unstack("high")
    wl = _unstack("low")
    wv = _unstack("vol").fillna(0.0)
    wa = _unstack("amount").fillna(0.0)
    wo = _unstack("open")

    # --- 3. 衍生宽表序列 ---
    wpct = wc.pct_change(fill_method=None).fillna(0.0)
    _wo_safe = wo.replace(0.0, np.nan)
    wret = ((wc - wo) / _wo_safe).fillna(0.0)

    # --- 4. Rolling 统计（所有列并行，C 级向量化）---
    wvol20 = wpct.rolling(20, min_periods=1).std(ddof=0).fillna(0.0)
    wvolavg = wv.rolling(20, min_periods=1).mean()

    # 牛基因因子
    _blt_row = _blt_ser.reindex(wc.columns).fillna(0.095)
    wlu = wpct.ge(_blt_row, axis="columns").astype(float)
    wlur = wlu.rolling(120, min_periods=1).mean()

    wrh60 = wc.rolling(60, min_periods=1).max()
    wnh = (wc >= wrh60).astype(float)
    wnhr = wnh.rolling(60, min_periods=1).mean()

    wpcp = wpct.clip(lower=0.0)
    wmaxpct = (wpcp.rolling(120, min_periods=1).max() / 0.30).clip(0.0, 1.0)

    wbg = 0.4 * wlur + 0.4 * wnhr + 0.2 * wmaxpct

    # 结构因子
    whs1 = wh.shift(1)
    wh20p = whs1.rolling(20, min_periods=1).max()
    wh60p = whs1.rolling(60, min_periods=1).max()

    _wbr = np.maximum(wh20p.values, wh60p.values)
    _wbr_s = pd.DataFrame(_wbr, index=wh20p.index, columns=wh20p.columns)
    _wbr_abs = _wbr_s.abs().replace(0.0, EPS)
    _wbsn = (((wc - _wbr_s) / _wbr_abs).clip(-0.2, 0.2) + 0.2) / 0.4
    _wbsn = _wbsn.clip(0.0, 1.0)

    w_str: dict[int, pd.DataFrame] = {}
    for _w in (20, 60, 120):
        _wwh = wh.rolling(_w, min_periods=1).max()
        _wwl = wl.rolling(_w, min_periods=1).min()
        _rng = (_wwh - _wwl).clip(lower=EPS)
        _pos = ((wc - _wwl) / _rng).clip(0.0, 1.0)
        w_str[_w] = 0.7 * _pos + 0.3 * _wbsn

    # 行为因子
    _wva_safe = wvolavg.clip(lower=EPS)
    wvq = (wv / _wva_safe).clip(0.0, 2.0) / 2.0
    wpcomp = ((wret + 0.1) / 0.2).clip(0.0, 1.0)
    wuf = (wpct > 0.0).astype(float)

    w_beh: dict[int, pd.DataFrame] = {}
    for _tw in (10, 20, 40):
        _wtc = wuf.rolling(_tw, min_periods=1).mean().clip(0.0, 1.0)
        w_beh[_tw] = 0.4 * wvq + 0.4 * wpcomp + 0.2 * _wtc

    # 低价线
    wls1 = wl.shift(1)
    wl20p = wls1.rolling(20, min_periods=1).min()
    wl20 = wl.rolling(20, min_periods=1).min()

    # --- 5. z-score 基线（仅计算最后一行的 rolling(120) 均值/标准差）---
    _zn = min(len(wbg), 120)  # 可用行数

    def _tail_mean_std(wdf: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        """tail-only 均值/标准差，等价于 rolling(120, min_periods=1) 最后一行。"""
        tail = wdf.iloc[-_zn:]
        return tail.mean(), tail.std(ddof=0).fillna(0.0)

    wbg_rm_s, wbg_rs_s = _tail_mean_std(wbg)

    w_str_rm_s: dict[int, pd.Series] = {}
    w_str_rs_s: dict[int, pd.Series] = {}
    for _w in (20, 60, 120):
        w_str_rm_s[_w], w_str_rs_s[_w] = _tail_mean_std(w_str[_w])

    w_beh_rm_s: dict[int, pd.Series] = {}
    w_beh_rs_s: dict[int, pd.Series] = {}
    for _tw in (10, 20, 40):
        w_beh_rm_s[_tw], w_beh_rs_s[_tw] = _tail_mean_std(w_beh[_tw])

    # --- 6. 连涨/连跌天数（向量化）---
    _wpct_last_col = wpct.iloc[-1]  # 最后一行
    _wpct_vals = wpct.values  # ndarray 以避免逐列 Series 开销
    _col_indices = {c: i for i, c in enumerate(wpct.columns)}
    _cu_arr = np.zeros(len(_idx), dtype=float)
    _cd_arr = np.zeros(len(_idx), dtype=float)
    for i, sc in enumerate(_idx):
        ci = _col_indices.get(sc)
        if ci is not None:
            _pv = _wpct_vals[:, ci]
            # 去除 NaN
            _mask = ~np.isnan(_pv)
            _pv_clean = _pv[_mask]
            _cu_arr[i] = _vec_consecutive_at_end(_pv_clean, positive=True)
            _cd_arr[i] = _vec_consecutive_at_end(_pv_clean, positive=False)

    # --- 7. 提取最后一行 & 对齐到 source 顺序 ---
    def _last_row(wdf: pd.DataFrame) -> np.ndarray:
        """取宽表最后一行，按 _idx 对齐。"""
        return wdf.iloc[-1].reindex(_idx).values.astype(float)

    def _ser_align(ser: pd.Series, default: float = 0.0) -> np.ndarray:
        """将 Series 按 _idx 对齐为 ndarray。"""
        return np.nan_to_num(ser.reindex(_idx).values.astype(float), nan=default)

    _close = np.nan_to_num(_last_row(wc), nan=0.0)
    _high = np.nan_to_num(_last_row(wh), nan=0.0)
    _low = np.nan_to_num(_last_row(wl), nan=0.0)
    _vol = np.nan_to_num(_last_row(wv), nan=0.0)
    _amount = np.nan_to_num(_last_row(wa), nan=0.0)
    _open = np.nan_to_num(_last_row(wo), nan=0.0)
    _ret_ratio = np.nan_to_num(_last_row(wret), nan=0.0)
    _v20d = np.nan_to_num(_last_row(wvol20), nan=0.0)
    _h20p = np.where(np.isnan(_last_row(wh20p)), _high, _last_row(wh20p))
    _h60p = np.where(np.isnan(_last_row(wh60p)), _high, _last_row(wh60p))
    _l20p = np.where(np.isnan(_last_row(wl20p)), _low, _last_row(wl20p))
    _l20v = np.where(np.isnan(_last_row(wl20)), _low, _last_row(wl20))
    _bg_raw = np.nan_to_num(_last_row(wbg), nan=0.0)
    _bg_rm = _ser_align(wbg_rm_s)
    _bg_rs = _ser_align(wbg_rs_s)
    _vq = np.nan_to_num(_last_row(wvq), nan=0.5)
    _pc = np.nan_to_num(_last_row(wpcomp), nan=0.5)

    # 结构/行为因子各窗口最后一行
    _str_last: dict[int, np.ndarray] = {}
    _str_rm_last: dict[int, np.ndarray] = {}
    _str_rs_last: dict[int, np.ndarray] = {}
    for _w in (20, 60, 120):
        _str_last[_w] = np.nan_to_num(_last_row(w_str[_w]), nan=0.5)
        _str_rm_last[_w] = _ser_align(w_str_rm_s[_w], 0.5)
        _str_rs_last[_w] = _ser_align(w_str_rs_s[_w])

    _beh_rm_last: dict[int, np.ndarray] = {}
    _beh_rs_last: dict[int, np.ndarray] = {}
    for _tw in (10, 20, 40):
        _beh_rm_last[_tw] = _ser_align(w_beh_rm_s[_tw], 0.5)
        _beh_rs_last[_tw] = _ser_align(w_beh_rs_s[_tw])

    # --- 8. 自适应窗口（向量化）---
    _tr = _amount / np.maximum(_close * 10000.0, 1.0)
    _aw = np.full(len(_idx), 60, dtype=int)
    _aw[(_v20d >= 0.045) | (_tr >= 8.0)] = 20
    _aw[(_v20d <= 0.020) & (_tr <= 3.0)] = 120
    _tw_arr = np.clip(np.round(_aw / 3).astype(int), 10, 40)

    _hd_ser = (~wc.isna()).sum(axis=0)
    _hd = np.array([_hd_ser.get(sc, 1) for sc in _idx], dtype=int)
    _sd = np.minimum(_hd, _aw)
    _qf = np.where(_stale_arr > 0, "stale", np.where(_sd < _aw, "cold_start", "normal"))

    # --- 9. 按窗口选择结构因子 & 行为因子基线 ---
    def _select_by_window(keys: np.ndarray, mapping: dict[int, np.ndarray], default: float = 0.5) -> np.ndarray:
        result = np.full(len(keys), default)
        for k, arr in mapping.items():
            mask = keys == k
            result[mask] = arr[mask]
        return result

    _sr = _select_by_window(_aw, _str_last)
    _sr_rm = _select_by_window(_aw, _str_rm_last)
    _sr_rs = _select_by_window(_aw, _str_rs_last, 0.0)

    _br_rm = _select_by_window(_tw_arr, _beh_rm_last)
    _br_rs = _select_by_window(_tw_arr, _beh_rs_last, 0.0)

    # 行为因子标量值（用连涨天数，与 series 的 rolling 趋势不同）
    _trend_comp = np.clip(_cu_arr / np.maximum(_tw_arr.astype(float), 1.0), 0.0, 1.0)
    _beh_raw = 0.4 * _vq + 0.4 * _pc + 0.2 * _trend_comp

    # --- 10. z-score → 评分 ---
    _bg_score = _vec_zscore(_bg_raw, _bg_rm, _bg_rs)
    _str_score = _vec_zscore(_sr, _sr_rm, _sr_rs)
    _beh_score = _vec_zscore(_beh_raw, _br_rm, _br_rs)
    _opp_score = np.round(0.20 * _bg_score + 0.50 * _str_score + 0.30 * _beh_score, 4)

    # 方向（使用 .value 确保存储字符串）
    _dir = np.full(len(_idx), PasDirection.NEUTRAL.value, dtype=object)
    _dir[(_close > _h20p) & (_cu_arr >= 3)] = PasDirection.BULLISH.value
    _dir[(_close < _l20p) & (_cd_arr >= 3)] = PasDirection.BEARISH.value

    # 等级
    _grade = np.full(len(_idx), "D", dtype=object)
    _grade[_opp_score >= 40.0] = "C"
    _grade[_opp_score >= 55.0] = "B"
    _grade[_opp_score >= 70.0] = "A"
    _grade[_opp_score >= 85.0] = "S"

    # 中性度
    _neut = np.round(np.clip(1.0 - np.abs(_opp_score - 50.0) / 50.0, 0.0, 1.0), 4)

    # --- 11. 风险收益（向量化）---
    _entry = np.where(_close > 0.0, _close, np.where(_open > 0.0, _open, 1.0))
    _stop = np.minimum(_l20v, _entry * 0.92)
    _risk = np.maximum(_entry - _stop, EPS)
    _tgt_ref = np.maximum(_h20p, _h60p)
    _bf = _entry + _risk
    _tgt_a = np.maximum(np.maximum(_tgt_ref, _bf), _entry * 1.08)
    _tgt_b = np.maximum(_tgt_ref, _entry * 1.03)
    _tgt = np.where(_close > _tgt_ref, _tgt_a, _tgt_b)
    _reward = np.maximum(_tgt - _entry, 0.0)
    _rr = np.maximum(_reward / _risk, 1.0)

    # 可交易性折扣
    _pct_today = _ret_ratio
    _is_lu = _pct_today >= _blt
    _is_tlu = (_high >= _entry * (1.0 + _blt)) & (_close < _high)
    _liq_disc = np.clip(_vq, 0.50, 1.00)
    _trad_disc = np.where(_is_lu, 0.60, np.where(_is_tlu, 0.80, 1.00))
    _eff_rr = np.maximum(_rr * _liq_disc * _trad_disc, 0.0)

    # --- 12. 构建输出 DataFrame ---
    _ts_arr = _ts_col.values
    frame = pd.DataFrame(
        {
            "trade_date": trade_date,
            "ts_code": _ts_arr,
            "stock_code": _idx,
            "opportunity_score": _opp_score,
            "pas_score": _opp_score,
            "opportunity_grade": _grade,
            "direction": _dir,
            "pas_direction": _dir,
            "risk_reward_ratio": np.round(_rr, 6),
            "effective_risk_reward_ratio": np.round(_eff_rr, 6),
            "quality_flag": _qf,
            "sample_days": _sd.astype(int),
            "neutrality": _neut,
            "window_mode": "adaptive",
            "adaptive_window": _aw.astype(int),
            "trend_window": _tw_arr.astype(int),
            "volatility_20d": np.round(_v20d, 6),
            "turnover_rate": np.round(_tr, 6),
            "bull_gene_score": np.round(_bg_score, 4),
            "structure_score": np.round(_str_score, 4),
            "behavior_score": np.round(_beh_score, 4),
            "liquidity_discount": np.round(_liq_disc, 4),
            "tradability_discount": np.round(_trad_disc, 4),
            "contract_version": SUPPORTED_CONTRACT_VERSION,
            "created_at": created_at,
        }
    )
    frame = frame[
        [
            "trade_date",
            "ts_code",
            "stock_code",
            "opportunity_score",
            "pas_score",
            "opportunity_grade",
            "direction",
            "pas_direction",
            "risk_reward_ratio",
            "effective_risk_reward_ratio",
            "quality_flag",
            "sample_days",
            "neutrality",
            "window_mode",
            "adaptive_window",
            "trend_window",
            "volatility_20d",
            "turnover_rate",
            "bull_gene_score",
            "structure_score",
            "behavior_score",
            "liquidity_discount",
            "tradability_discount",
            "contract_version",
            "created_at",
        ]
    ]

    count = _persist(
        database_path=database_path,
        table_name="stock_pas_daily",
        frame=frame,
        trade_date=trade_date,
    )

    factor_frame = pd.DataFrame(
        {
            "trade_date": trade_date,
            "stock_code": _idx,
            "ts_code": _ts_arr,
            "bull_gene_raw": np.round(_bg_raw, 6),
            "structure_raw": np.round(_sr, 6),
            "behavior_raw": np.round(_beh_raw, 6),
            "volatility_20d": np.round(_v20d, 6),
            "turnover_rate": np.round(_tr, 6),
            "adaptive_window": _aw.astype(int),
            "created_at": created_at,
        }
    )
    _persist(
        database_path=database_path,
        table_name="pas_factor_intermediate",
        frame=factor_frame,
        trade_date=trade_date,
    )

    target_artifacts_dir = artifacts_dir or (Path("artifacts") / "spiral-s2c" / trade_date)
    artifact_path = target_artifacts_dir / "pas_factor_intermediate_sample.parquet"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    factor_frame.to_parquet(artifact_path, index=False)

    return PasRunResult(
        trade_date=trade_date,
        count=count,
        frame=frame,
        factor_intermediate_frame=factor_frame,
        factor_intermediate_sample_path=artifact_path,
    )
