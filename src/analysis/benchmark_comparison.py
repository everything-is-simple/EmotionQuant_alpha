"""基准策略对比模块（螺旋1 阻断项清零）：MSS vs 随机基准 / MSS vs 技术基线。

功能：
  1. 随机基准策略：每日从可交易股票池随机选股（同等数量），固定 seed 可复现。
  2. 技术基线策略：MA5/MA20 金叉 + RSI(14) 超卖反弹 + MACD 金叉 投票。
  3. 简化回测循环：复用 backtest/pipeline.py 的 A股约束与成本模型。
  4. 对比报告生成：MSS vs 随机、MSS vs 技术基线。

DESIGN_TRACE:
  - Governance/SpiralRoadmap/planA/PLAN-A-REVALIDATION-CHECKLIST.md (§2.2 对比归因)
  - Governance/SpiralRoadmap/planA/planA-ENHANCEMENT.md (§2 螺旋1 归因对比门禁)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from src.backtest.pipeline import (
    LIMIT_RATIO_GEM_STAR,
    LIMIT_RATIO_MAIN_BOARD,
    LIMIT_RATIO_ST,
    MIN_FILL_PROBABILITY,
    QUEUE_PARTICIPATION_RATE,
    _build_prev_close_lookup,
    _build_price_lookup,
    _clip,
    _compute_daily_return_distribution,
    _compute_max_drawdown_days,
    _estimate_fill,
    _estimate_impact_cost,
    _is_limit_down,
    _is_limit_up,
    _is_liquidity_dryup,
    _is_one_word_board,
    _next_trade_day,
    _read_price_frame,
    _read_stock_profiles,
    _read_trading_days,
    _resolve_fee_tier,
    _resolve_limit_ratio,
)
from src.config.config import Config
from src.db.helpers import table_exists as _table_exists


@dataclass(frozen=True)
class BenchmarkResult:
    """单个基准策略的回测结果。"""

    strategy_name: str
    total_return: float
    max_drawdown: float
    win_rate: float
    sharpe_ratio: float
    total_trades: int
    daily_return_mean: float
    daily_return_std: float
    equity_curve: list[float]


@dataclass(frozen=True)
class BenchmarkComparisonResult:
    """MSS vs 随机 / MSS vs 技术基线 的完整对比结果。"""

    mss_result: BenchmarkResult
    random_result: BenchmarkResult
    technical_result: BenchmarkResult
    mss_vs_random_excess: float
    mss_vs_technical_excess: float
    mss_vs_random_conclusion: str
    mss_vs_technical_conclusion: str


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _annualized_sharpe(
    daily_returns: pd.Series, risk_free_rate: float = 0.015
) -> float:
    """年化夏普比率。"""
    if daily_returns.empty or daily_returns.std() == 0:
        return 0.0
    daily_rf = risk_free_rate / 252.0
    excess = daily_returns - daily_rf
    std = float(excess.std(ddof=0))
    if std <= 0:
        return 0.0
    return round(float(excess.mean() / std) * math.sqrt(252), 4)


def _equity_to_daily_returns(equity_curve: list[float]) -> pd.Series:
    """权益曲线转日收益率序列。"""
    if len(equity_curve) <= 1:
        return pd.Series(dtype="float64")
    s = pd.Series(equity_curve, dtype="float64")
    returns = s.pct_change().replace([float("inf"), float("-inf")], 0.0).fillna(0.0).iloc[1:]
    return returns


def _calc_fees(
    amount: float,
    direction: str,
    *,
    commission_rate: float,
    stamp_duty_rate: float,
    transfer_fee_rate: float,
    min_commission: float,
) -> tuple[float, float, float, float]:
    """计算交易费用（佣金 + 印花税 + 过户费）。"""
    _, fee_multiplier = _resolve_fee_tier(amount)
    commission = max(min_commission, amount * commission_rate * fee_multiplier)
    stamp_tax = amount * stamp_duty_rate if direction == "sell" else 0.0
    transfer_fee = amount * transfer_fee_rate
    total_fee = commission + stamp_tax + transfer_fee
    return (
        round(commission, 6),
        round(stamp_tax, 6),
        round(transfer_fee, 6),
        round(total_fee, 6),
    )


# ---------------------------------------------------------------------------
# 随机信号生成
# ---------------------------------------------------------------------------


def generate_random_signals(
    *,
    mss_signals_by_date: dict[str, list[str]],
    available_stocks_by_date: dict[str, list[str]],
    seed: int = 42,
) -> dict[str, list[str]]:
    """为每个交易日生成随机买入信号（与 MSS 同等数量）。

    Args:
        mss_signals_by_date: {trade_date: [stock_code, ...]} MSS 当日推荐列表
        available_stocks_by_date: {trade_date: [stock_code, ...]} 当日可交易股票池
        seed: 随机种子
    Returns:
        {trade_date: [stock_code, ...]} 随机选股结果
    """
    rng = np.random.default_rng(seed)
    result: dict[str, list[str]] = {}
    for trade_date, mss_stocks in mss_signals_by_date.items():
        n = len(mss_stocks)
        pool = available_stocks_by_date.get(trade_date, [])
        if not pool or n <= 0:
            result[trade_date] = []
            continue
        actual_n = min(n, len(pool))
        chosen_indices = rng.choice(len(pool), size=actual_n, replace=False)
        result[trade_date] = [pool[i] for i in chosen_indices]
    return result


# ---------------------------------------------------------------------------
# 技术指标计算
# ---------------------------------------------------------------------------


def compute_technical_signals(
    price_frame: pd.DataFrame,
    *,
    ma_short: int = 5,
    ma_long: int = 20,
    rsi_period: int = 14,
    rsi_oversold: float = 30.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
) -> pd.DataFrame:
    """基于 raw_daily 行情数据计算 MA/RSI/MACD 技术信号。

    向量化实现，对每只股票独立计算。
    返回 DataFrame 包含: trade_date, stock_code, ma_signal, rsi_signal, macd_signal, vote_count
    """
    if price_frame.empty:
        return pd.DataFrame(
            columns=["trade_date", "stock_code", "ma_signal", "rsi_signal", "macd_signal", "vote_count"]
        )

    df = price_frame.copy()
    df["trade_date"] = df["trade_date"].astype(str).str.strip()
    df["stock_code"] = df["stock_code"].astype(str).str.strip()
    df["close"] = pd.to_numeric(df["close"], errors="coerce").fillna(0.0)
    df = df.sort_values(["stock_code", "trade_date"]).reset_index(drop=True)

    grouped = df.groupby("stock_code")

    # --- MA 金叉 ---
    df["ma_short"] = grouped["close"].transform(lambda x: x.rolling(ma_short, min_periods=ma_short).mean())
    df["ma_long"] = grouped["close"].transform(lambda x: x.rolling(ma_long, min_periods=ma_long).mean())
    df["ma_prev_short"] = grouped["ma_short"].shift(1)
    df["ma_prev_long"] = grouped["ma_long"].shift(1)
    df["ma_signal"] = (
        (df["ma_short"] > df["ma_long"])
        & (df["ma_prev_short"] <= df["ma_prev_long"])
        & df["ma_short"].notna()
        & df["ma_long"].notna()
    ).astype(int)

    # --- RSI 超卖反弹 ---
    delta = grouped["close"].diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.groupby(df["stock_code"]).transform(
        lambda x: x.rolling(rsi_period, min_periods=rsi_period).mean()
    )
    avg_loss = loss.groupby(df["stock_code"]).transform(
        lambda x: x.rolling(rsi_period, min_periods=rsi_period).mean()
    )
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    df["rsi"] = 100.0 - 100.0 / (1.0 + rs)
    df["rsi_prev"] = grouped["rsi"].shift(1)
    df["rsi_signal"] = (
        (df["rsi"] > rsi_oversold)
        & (df["rsi_prev"] <= rsi_oversold)
        & df["rsi"].notna()
    ).astype(int)

    # --- MACD 金叉 ---
    df["ema_fast"] = grouped["close"].transform(
        lambda x: x.ewm(span=macd_fast, adjust=False, min_periods=macd_fast).mean()
    )
    df["ema_slow"] = grouped["close"].transform(
        lambda x: x.ewm(span=macd_slow, adjust=False, min_periods=macd_slow).mean()
    )
    df["macd_line"] = df["ema_fast"] - df["ema_slow"]
    df["macd_signal_line"] = df.groupby("stock_code")["macd_line"].transform(
        lambda x: x.ewm(span=macd_signal, adjust=False, min_periods=macd_signal).mean()
    )
    df["macd_prev_line"] = grouped["macd_line"].shift(1)
    df["macd_prev_signal"] = grouped["macd_signal_line"].shift(1)
    df["macd_signal_flag"] = (
        (df["macd_line"] > df["macd_signal_line"])
        & (df["macd_prev_line"] <= df["macd_prev_signal"])
        & df["macd_line"].notna()
        & df["macd_signal_line"].notna()
    ).astype(int)

    # --- 投票汇总 ---
    df["vote_count"] = df["ma_signal"] + df["rsi_signal"] + df["macd_signal_flag"]

    return df[["trade_date", "stock_code", "ma_signal", "rsi_signal", "macd_signal_flag", "vote_count"]].rename(
        columns={"macd_signal_flag": "macd_signal"}
    )


def generate_technical_signals(
    *,
    tech_frame: pd.DataFrame,
    mss_signals_by_date: dict[str, list[str]],
    min_votes: int = 2,
) -> dict[str, list[str]]:
    """从技术指标中筛选信号，每日取与 MSS 同等数量的 top 信号。

    Args:
        tech_frame: compute_technical_signals 的输出
        mss_signals_by_date: MSS 每日推荐列表（用于确定每日选股数量）
        min_votes: 最少投票数（MA/RSI/MACD 至少 min_votes 个触发）
    Returns:
        {trade_date: [stock_code, ...]}
    """
    if tech_frame.empty:
        return {}
    qualified = tech_frame[tech_frame["vote_count"] >= min_votes].copy()
    qualified = qualified.sort_values(["trade_date", "vote_count"], ascending=[True, False])

    result: dict[str, list[str]] = {}
    for trade_date, n_mss in ((d, len(s)) for d, s in mss_signals_by_date.items()):
        day_df = qualified[qualified["trade_date"] == trade_date]
        top_stocks = day_df["stock_code"].head(n_mss).tolist()
        result[trade_date] = top_stocks
    return result


# ---------------------------------------------------------------------------
# 简化回测循环
# ---------------------------------------------------------------------------


def run_simplified_backtest(
    *,
    signals_by_date: dict[str, list[str]],
    trading_days: list[str],
    price_lookup: dict[tuple[str, str], dict[str, float]],
    prev_close_lookup: dict[tuple[str, str], float],
    stock_profiles: dict[str, dict[str, str]],
    config: Config,
    strategy_name: str,
) -> BenchmarkResult:
    """简化回测循环：使用与主回测相同的 A股约束和成本模型。

    与主回测差异：
      - 不需要 quality_gate / bridge_check（基准策略不经过 integration）
      - position_size 统一使用 max_position_pct（公平对比）
    """
    initial_cash = float(config.backtest_initial_cash)
    max_position_pct = float(config.backtest_max_position_pct)
    cash = initial_cash
    equity_curve: list[float] = [initial_cash]
    positions: dict[str, dict[str, Any]] = {}
    total_trades = 0
    win_count = 0
    sell_count = 0

    # 构建 signal -> execute_date 映射
    signals_by_execute_date: dict[str, list[str]] = {}
    for signal_date, stocks in signals_by_date.items():
        execute_date = _next_trade_day(trading_days, signal_date)
        if execute_date is None:
            continue
        signals_by_execute_date.setdefault(execute_date, []).extend(stocks)

    for replay_day in trading_days:
        # 1) 卖出：T+1 解锁后平仓
        for stock_code in list(positions.keys()):
            pos = positions[stock_code]
            can_sell_date = str(pos.get("can_sell_date", replay_day))
            if replay_day < can_sell_date:
                continue

            price = price_lookup.get((replay_day, stock_code))
            if not price:
                continue
            stock_name = str(stock_profiles.get(stock_code, {}).get("stock_name", ""))
            limit_ratio = _resolve_limit_ratio(stock_code=stock_code, stock_name=stock_name)
            prev_close = prev_close_lookup.get((replay_day, stock_code))
            if _is_limit_down(price=price, prev_close=prev_close, limit_ratio=limit_ratio):
                continue

            filled_price = float(price.get("open", 0.0) or 0.0)
            if filled_price <= 0.0:
                filled_price = float(price.get("close", 0.0) or 0.0)
            if filled_price <= 0.0:
                continue

            shares = int(pos["shares"])
            amount = round(filled_price * shares, 4)
            _, _, _, total_fee = _calc_fees(
                amount,
                "sell",
                commission_rate=float(config.backtest_commission_rate),
                stamp_duty_rate=float(config.backtest_stamp_duty_rate),
                transfer_fee_rate=float(config.backtest_transfer_fee_rate),
                min_commission=float(config.backtest_min_commission),
            )
            impact_cost, _, _ = _estimate_impact_cost(
                price=price,
                order_shares=shares,
                amount=amount,
                slippage_rate=float(config.backtest_slippage_value),
            )
            total_fee = round(total_fee + impact_cost, 6)
            cash = round(cash + amount - total_fee, 4)

            buy_amount = float(pos.get("buy_amount", 0.0))
            buy_fee = float(pos.get("buy_fee", 0.0))
            pnl = round(amount - total_fee - buy_amount - buy_fee, 4)
            sell_count += 1
            total_trades += 1
            if pnl > 0:
                win_count += 1

            del positions[stock_code]

        # 2) 买入
        for stock_code in signals_by_execute_date.get(replay_day, []):
            if not stock_code or stock_code in positions:
                continue

            price = price_lookup.get((replay_day, stock_code))
            if not price:
                continue
            stock_name = str(stock_profiles.get(stock_code, {}).get("stock_name", ""))
            limit_ratio = _resolve_limit_ratio(stock_code=stock_code, stock_name=stock_name)
            prev_close = prev_close_lookup.get((replay_day, stock_code))
            if _is_one_word_board(price):
                continue
            if _is_limit_up(price=price, prev_close=prev_close, limit_ratio=limit_ratio):
                continue
            if _is_liquidity_dryup(price):
                continue

            filled_price = float(price.get("open", 0.0) or 0.0)
            if filled_price <= 0.0:
                continue

            raw_shares = int((cash * max_position_pct) / filled_price)
            shares = (raw_shares // 100) * 100
            if shares <= 0:
                continue

            fill_prob, fill_ratio, _ = _estimate_fill(price=price, order_shares=shares)
            if fill_prob < MIN_FILL_PROBABILITY:
                continue
            filled_shares = (int(shares * fill_ratio) // 100) * 100
            if filled_shares <= 0:
                continue

            amount = round(filled_price * filled_shares, 4)
            _, _, _, buy_fee = _calc_fees(
                amount,
                "buy",
                commission_rate=float(config.backtest_commission_rate),
                stamp_duty_rate=float(config.backtest_stamp_duty_rate),
                transfer_fee_rate=float(config.backtest_transfer_fee_rate),
                min_commission=float(config.backtest_min_commission),
            )
            impact_cost, _, _ = _estimate_impact_cost(
                price=price,
                order_shares=filled_shares,
                amount=amount,
                slippage_rate=float(config.backtest_slippage_value),
            )
            buy_fee = round(buy_fee + impact_cost, 6)
            required = amount + buy_fee
            if required > cash:
                continue
            cash = round(cash - required, 4)
            total_trades += 1

            can_sell_date = _next_trade_day(trading_days, replay_day) or replay_day
            positions[stock_code] = {
                "shares": filled_shares,
                "buy_amount": amount,
                "buy_fee": buy_fee,
                "can_sell_date": can_sell_date,
            }

        # 3) 盯市
        market_value = 0.0
        for stock_code, pos in positions.items():
            p = price_lookup.get((replay_day, stock_code), {})
            close_price = float(p.get("close", 0.0) or 0.0)
            if close_price <= 0.0:
                close_price = float(p.get("open", 0.0) or 0.0)
            if close_price <= 0.0:
                close_price = float(pos.get("buy_amount", 0.0)) / max(1, int(pos.get("shares", 1)))
            market_value += close_price * int(pos["shares"])
        equity_curve.append(round(cash + market_value, 4))

    # 汇总
    total_pnl = equity_curve[-1] - initial_cash
    total_return = round(total_pnl / max(1.0, initial_cash), 8)
    max_eq = max(equity_curve) if equity_curve else initial_cash
    min_eq = min(equity_curve) if equity_curve else initial_cash
    max_drawdown = round((max_eq - min_eq) / max(1.0, max_eq), 8)
    win_rate = round(win_count / max(1, sell_count), 6)

    daily_returns = _equity_to_daily_returns(equity_curve)
    dr_dist = _compute_daily_return_distribution(equity_curve)
    sharpe = _annualized_sharpe(daily_returns, risk_free_rate=float(config.backtest_risk_free_rate))

    return BenchmarkResult(
        strategy_name=strategy_name,
        total_return=total_return,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        sharpe_ratio=sharpe,
        total_trades=total_trades,
        daily_return_mean=dr_dist["daily_return_mean"],
        daily_return_std=dr_dist["daily_return_std"],
        equity_curve=equity_curve,
    )


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def run_benchmark_comparison(
    *,
    config: Config,
    start_date: str,
    end_date: str,
) -> BenchmarkComparisonResult:
    """运行 MSS vs 随机 / MSS vs 技术基线 完整对比实验。"""
    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not db_path.exists():
        raise FileNotFoundError(f"DuckDB not found: {db_path}")

    # 读取公共数据
    trading_days = _read_trading_days(database_path=db_path, start_date=start_date, end_date=end_date)
    if not trading_days:
        raise ValueError("No trading days found in window")

    # 需要额外的前置窗口来计算技术指标（MA20 需要 20 个交易日前置）
    with duckdb.connect(str(db_path), read_only=True) as conn:
        warmup_frame = conn.execute(
            "SELECT DISTINCT trade_date FROM raw_trade_cal "
            "WHERE trade_date < ? AND CAST(is_open AS INTEGER) = 1 "
            "ORDER BY trade_date DESC LIMIT 60",
            [start_date],
        ).df()
    warmup_start = str(warmup_frame["trade_date"].min()) if not warmup_frame.empty else start_date

    price_frame = _read_price_frame(database_path=db_path, start_date=warmup_start, end_date=end_date)
    price_lookup = _build_price_lookup(price_frame)
    prev_close_lookup = _build_prev_close_lookup(price_frame)
    stock_profiles = _read_stock_profiles(database_path=db_path)

    # 读取 MSS 推荐信号
    with duckdb.connect(str(db_path), read_only=True) as conn:
        mss_recs = conn.execute(
            "SELECT trade_date, stock_code FROM integrated_recommendation "
            "WHERE trade_date >= ? AND trade_date <= ? "
            "AND recommendation IN ('STRONG_BUY', 'BUY') "
            "ORDER BY trade_date, final_score DESC",
            [start_date, end_date],
        ).df()

    mss_signals_by_date: dict[str, list[str]] = {}
    if not mss_recs.empty:
        for td, group in mss_recs.groupby("trade_date"):
            mss_signals_by_date[str(td)] = group["stock_code"].astype(str).str.strip().tolist()

    # 构建每日可交易股票池（当日有行情的股票）
    available_stocks_by_date: dict[str, list[str]] = {}
    window_prices = price_frame[
        (price_frame["trade_date"].astype(str) >= start_date)
        & (price_frame["trade_date"].astype(str) <= end_date)
    ]
    if not window_prices.empty:
        for td, group in window_prices.groupby("trade_date"):
            td_str = str(td).strip()
            stocks = group["stock_code"].astype(str).str.strip().tolist()
            available_stocks_by_date[td_str] = [s for s in stocks if s]

    # --- MSS 策略回测 ---
    mss_result = run_simplified_backtest(
        signals_by_date=mss_signals_by_date,
        trading_days=trading_days,
        price_lookup=price_lookup,
        prev_close_lookup=prev_close_lookup,
        stock_profiles=stock_profiles,
        config=config,
        strategy_name="MSS_Integrated",
    )

    # --- 随机基准回测 ---
    random_signals = generate_random_signals(
        mss_signals_by_date=mss_signals_by_date,
        available_stocks_by_date=available_stocks_by_date,
        seed=42,
    )
    random_result = run_simplified_backtest(
        signals_by_date=random_signals,
        trading_days=trading_days,
        price_lookup=price_lookup,
        prev_close_lookup=prev_close_lookup,
        stock_profiles=stock_profiles,
        config=config,
        strategy_name="Random_Baseline",
    )

    # --- 技术基线回测 ---
    tech_frame = compute_technical_signals(price_frame)
    tech_signals = generate_technical_signals(
        tech_frame=tech_frame,
        mss_signals_by_date=mss_signals_by_date,
        min_votes=2,
    )
    technical_result = run_simplified_backtest(
        signals_by_date=tech_signals,
        trading_days=trading_days,
        price_lookup=price_lookup,
        prev_close_lookup=prev_close_lookup,
        stock_profiles=stock_profiles,
        config=config,
        strategy_name="Technical_MA_RSI_MACD",
    )

    # --- 对比 ---
    mss_vs_random_excess = round(mss_result.total_return - random_result.total_return, 8)
    mss_vs_technical_excess = round(mss_result.total_return - technical_result.total_return, 8)

    mss_vs_random_conclusion = (
        "MSS_OUTPERFORMS_RANDOM"
        if mss_vs_random_excess > 0
        else "RANDOM_OUTPERFORMS_MSS" if mss_vs_random_excess < 0 else "TIE"
    )
    mss_vs_technical_conclusion = (
        "MSS_OUTPERFORMS_TECHNICAL"
        if mss_vs_technical_excess > 0
        else "TECHNICAL_OUTPERFORMS_MSS" if mss_vs_technical_excess < 0 else "TIE"
    )

    return BenchmarkComparisonResult(
        mss_result=mss_result,
        random_result=random_result,
        technical_result=technical_result,
        mss_vs_random_excess=mss_vs_random_excess,
        mss_vs_technical_excess=mss_vs_technical_excess,
        mss_vs_random_conclusion=mss_vs_random_conclusion,
        mss_vs_technical_conclusion=mss_vs_technical_conclusion,
    )


def format_benchmark_report(result: BenchmarkComparisonResult) -> list[str]:
    """格式化对比报告为 markdown 行列表。"""
    lines = [
        "# S3b A/B Benchmark Report (Full Mode)",
        "",
        "## 1. MSS Integrated Strategy (A)",
        "",
        f"- total_return: {result.mss_result.total_return}",
        f"- max_drawdown: {result.mss_result.max_drawdown}",
        f"- win_rate: {result.mss_result.win_rate}",
        f"- sharpe_ratio: {result.mss_result.sharpe_ratio}",
        f"- total_trades: {result.mss_result.total_trades}",
        f"- daily_return_mean: {result.mss_result.daily_return_mean}",
        f"- daily_return_std: {result.mss_result.daily_return_std}",
        "",
        "## 2. Random Baseline",
        "",
        f"- total_return: {result.random_result.total_return}",
        f"- max_drawdown: {result.random_result.max_drawdown}",
        f"- win_rate: {result.random_result.win_rate}",
        f"- sharpe_ratio: {result.random_result.sharpe_ratio}",
        f"- total_trades: {result.random_result.total_trades}",
        f"- daily_return_mean: {result.random_result.daily_return_mean}",
        f"- daily_return_std: {result.random_result.daily_return_std}",
        f"- seed: 42",
        "",
        "## 3. Technical Baseline (MA5/MA20 + RSI14 + MACD)",
        "",
        f"- total_return: {result.technical_result.total_return}",
        f"- max_drawdown: {result.technical_result.max_drawdown}",
        f"- win_rate: {result.technical_result.win_rate}",
        f"- sharpe_ratio: {result.technical_result.sharpe_ratio}",
        f"- total_trades: {result.technical_result.total_trades}",
        f"- daily_return_mean: {result.technical_result.daily_return_mean}",
        f"- daily_return_std: {result.technical_result.daily_return_std}",
        "",
        "## 4. MSS vs Random Baseline",
        "",
        f"- mss_total_return: {result.mss_result.total_return}",
        f"- random_total_return: {result.random_result.total_return}",
        f"- excess_return: {result.mss_vs_random_excess}",
        f"- conclusion: {result.mss_vs_random_conclusion}",
        f"- sharpe_delta: {round(result.mss_result.sharpe_ratio - result.random_result.sharpe_ratio, 4)}",
        "",
        "## 5. MSS vs Technical Baseline",
        "",
        f"- mss_total_return: {result.mss_result.total_return}",
        f"- technical_total_return: {result.technical_result.total_return}",
        f"- excess_return: {result.mss_vs_technical_excess}",
        f"- conclusion: {result.mss_vs_technical_conclusion}",
        f"- sharpe_delta: {round(result.mss_result.sharpe_ratio - result.technical_result.sharpe_ratio, 4)}",
        "",
        "## 6. Gate Decision",
        "",
    ]

    # 门禁判定：MSS 必须同时优于随机 AND 技术基线才能 GO
    if result.mss_vs_random_excess > 0 and result.mss_vs_technical_excess > 0:
        lines.append("- gate: PASS")
        lines.append("- go_nogo: GO")
        lines.append("- reason: MSS outperforms both random and technical baselines")
    elif result.mss_vs_random_excess > 0 or result.mss_vs_technical_excess > 0:
        lines.append("- gate: WARN")
        lines.append("- go_nogo: CONDITIONAL_GO")
        lines.append("- reason: MSS outperforms one baseline but not both")
    else:
        lines.append("- gate: FAIL")
        lines.append("- go_nogo: NO_GO")
        lines.append("- reason: MSS does not outperform either baseline")
    lines.append("")
    return lines
