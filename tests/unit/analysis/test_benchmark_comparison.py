from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.analysis.benchmark_comparison import (
    BenchmarkComparisonResult,
    BenchmarkResult,
    _annualized_sharpe,
    _calc_fees,
    _equity_to_daily_returns,
    compute_technical_signals,
    format_benchmark_report,
    generate_random_signals,
    generate_technical_signals,
)


# ---------------------------------------------------------------------------
# _annualized_sharpe
# ---------------------------------------------------------------------------


class TestAnnualizedSharpe:
    def test_empty_series_returns_zero(self) -> None:
        assert _annualized_sharpe(pd.Series(dtype="float64")) == 0.0

    def test_constant_returns_zero_std(self) -> None:
        s = pd.Series([0.01, 0.01, 0.01], dtype="float64")
        assert _annualized_sharpe(s) == 0.0

    def test_positive_returns(self) -> None:
        rng = np.random.default_rng(99)
        returns = pd.Series(rng.normal(0.001, 0.01, 252), dtype="float64")
        sharpe = _annualized_sharpe(returns, risk_free_rate=0.015)
        assert isinstance(sharpe, float)
        assert sharpe != 0.0


# ---------------------------------------------------------------------------
# _equity_to_daily_returns
# ---------------------------------------------------------------------------


class TestEquityToDailyReturns:
    def test_single_point_returns_empty(self) -> None:
        result = _equity_to_daily_returns([100.0])
        assert result.empty

    def test_basic_returns(self) -> None:
        result = _equity_to_daily_returns([100.0, 110.0, 99.0])
        assert len(result) == 2
        assert abs(result.iloc[0] - 0.1) < 1e-9
        assert abs(result.iloc[1] - (-0.1)) < 1e-9


# ---------------------------------------------------------------------------
# _calc_fees
# ---------------------------------------------------------------------------


class TestCalcFees:
    def test_buy_no_stamp_duty(self) -> None:
        commission, stamp, transfer, total = _calc_fees(
            10000.0,
            "buy",
            commission_rate=0.0003,
            stamp_duty_rate=0.001,
            transfer_fee_rate=0.00002,
            min_commission=5.0,
        )
        assert stamp == 0.0
        assert commission > 0.0
        assert total == commission + transfer

    def test_sell_includes_stamp_duty(self) -> None:
        _, stamp, _, total = _calc_fees(
            10000.0,
            "sell",
            commission_rate=0.0003,
            stamp_duty_rate=0.001,
            transfer_fee_rate=0.00002,
            min_commission=5.0,
        )
        assert stamp > 0.0
        assert total > stamp

    def test_min_commission_floor(self) -> None:
        commission, _, _, _ = _calc_fees(
            10.0,
            "buy",
            commission_rate=0.0003,
            stamp_duty_rate=0.001,
            transfer_fee_rate=0.00002,
            min_commission=5.0,
        )
        assert commission >= 5.0


# ---------------------------------------------------------------------------
# generate_random_signals
# ---------------------------------------------------------------------------


class TestGenerateRandomSignals:
    def test_same_count_as_mss(self) -> None:
        mss = {"20240102": ["000001", "000002", "000003"]}
        pool = {"20240102": [f"{i:06d}" for i in range(1, 101)]}
        result = generate_random_signals(
            mss_signals_by_date=mss,
            available_stocks_by_date=pool,
            seed=42,
        )
        assert len(result["20240102"]) == 3

    def test_reproducible_with_same_seed(self) -> None:
        mss = {"20240102": ["000001", "000002"]}
        pool = {"20240102": [f"{i:06d}" for i in range(1, 51)]}
        r1 = generate_random_signals(mss_signals_by_date=mss, available_stocks_by_date=pool, seed=42)
        r2 = generate_random_signals(mss_signals_by_date=mss, available_stocks_by_date=pool, seed=42)
        assert r1 == r2

    def test_different_seed_different_result(self) -> None:
        mss = {"20240102": ["000001", "000002"]}
        pool = {"20240102": [f"{i:06d}" for i in range(1, 51)]}
        r1 = generate_random_signals(mss_signals_by_date=mss, available_stocks_by_date=pool, seed=1)
        r2 = generate_random_signals(mss_signals_by_date=mss, available_stocks_by_date=pool, seed=2)
        assert r1 != r2

    def test_empty_pool_returns_empty(self) -> None:
        mss = {"20240102": ["000001"]}
        pool: dict[str, list[str]] = {"20240102": []}
        result = generate_random_signals(mss_signals_by_date=mss, available_stocks_by_date=pool, seed=42)
        assert result["20240102"] == []

    def test_missing_date_in_pool(self) -> None:
        mss = {"20240102": ["000001"]}
        result = generate_random_signals(mss_signals_by_date=mss, available_stocks_by_date={}, seed=42)
        assert result["20240102"] == []


# ---------------------------------------------------------------------------
# compute_technical_signals
# ---------------------------------------------------------------------------


def _build_price_frame(n_stocks: int = 2, n_days: int = 40) -> pd.DataFrame:
    """Build a synthetic price frame with enough data for MA20 warmup."""
    rows = []
    rng = np.random.default_rng(7)
    for s in range(1, n_stocks + 1):
        code = f"{s:06d}"
        price = 10.0
        for d in range(n_days):
            date = f"2024{(d // 28) + 1:02d}{(d % 28) + 1:02d}"
            change = rng.normal(0.0, 0.02)
            price = max(1.0, price * (1.0 + change))
            rows.append({
                "trade_date": date,
                "stock_code": code,
                "open": round(price * 0.99, 2),
                "high": round(price * 1.01, 2),
                "low": round(price * 0.98, 2),
                "close": round(price, 2),
                "volume": rng.integers(100000, 10000000),
                "amount": round(price * rng.integers(100000, 10000000), 2),
            })
    return pd.DataFrame(rows)


class TestComputeTechnicalSignals:
    def test_returns_expected_columns(self) -> None:
        pf = _build_price_frame()
        result = compute_technical_signals(pf)
        expected_cols = {"trade_date", "stock_code", "ma_signal", "rsi_signal", "macd_signal", "vote_count"}
        assert set(result.columns) == expected_cols

    def test_vote_count_range(self) -> None:
        pf = _build_price_frame()
        result = compute_technical_signals(pf)
        assert result["vote_count"].min() >= 0
        assert result["vote_count"].max() <= 3

    def test_empty_input(self) -> None:
        result = compute_technical_signals(pd.DataFrame())
        assert result.empty
        assert "vote_count" in result.columns


# ---------------------------------------------------------------------------
# generate_technical_signals
# ---------------------------------------------------------------------------


class TestGenerateTechnicalSignals:
    def test_respects_min_votes(self) -> None:
        tech_frame = pd.DataFrame({
            "trade_date": ["20240110"] * 3,
            "stock_code": ["000001", "000002", "000003"],
            "ma_signal": [1, 1, 0],
            "rsi_signal": [1, 0, 0],
            "macd_signal": [1, 0, 0],
            "vote_count": [3, 1, 0],
        })
        mss = {"20240110": ["A", "B"]}
        result = generate_technical_signals(tech_frame=tech_frame, mss_signals_by_date=mss, min_votes=2)
        # Only 000001 has vote_count >= 2
        assert "000001" in result.get("20240110", [])
        assert "000003" not in result.get("20240110", [])

    def test_caps_at_mss_count(self) -> None:
        tech_frame = pd.DataFrame({
            "trade_date": ["20240110"] * 4,
            "stock_code": ["000001", "000002", "000003", "000004"],
            "ma_signal": [1, 1, 1, 1],
            "rsi_signal": [1, 1, 1, 0],
            "macd_signal": [1, 1, 0, 1],
            "vote_count": [3, 3, 2, 2],
        })
        mss = {"20240110": ["A"]}  # only 1 stock in MSS
        result = generate_technical_signals(tech_frame=tech_frame, mss_signals_by_date=mss, min_votes=2)
        assert len(result["20240110"]) == 1

    def test_empty_tech_frame(self) -> None:
        result = generate_technical_signals(
            tech_frame=pd.DataFrame(),
            mss_signals_by_date={"20240110": ["A"]},
        )
        assert result == {}


# ---------------------------------------------------------------------------
# format_benchmark_report
# ---------------------------------------------------------------------------


class TestFormatBenchmarkReport:
    @pytest.fixture()
    def sample_result(self) -> BenchmarkComparisonResult:
        mss = BenchmarkResult(
            strategy_name="MSS_Integrated",
            total_return=0.12,
            max_drawdown=-0.05,
            win_rate=0.55,
            sharpe_ratio=1.2,
            total_trades=100,
            daily_return_mean=0.0005,
            daily_return_std=0.012,
            equity_curve=[1_000_000, 1_120_000],
        )
        rand = BenchmarkResult(
            strategy_name="Random_Baseline",
            total_return=0.03,
            max_drawdown=-0.08,
            win_rate=0.48,
            sharpe_ratio=0.3,
            total_trades=100,
            daily_return_mean=0.0001,
            daily_return_std=0.015,
            equity_curve=[1_000_000, 1_030_000],
        )
        tech = BenchmarkResult(
            strategy_name="Technical_MA_RSI_MACD",
            total_return=0.06,
            max_drawdown=-0.07,
            win_rate=0.50,
            sharpe_ratio=0.6,
            total_trades=80,
            daily_return_mean=0.0002,
            daily_return_std=0.014,
            equity_curve=[1_000_000, 1_060_000],
        )
        return BenchmarkComparisonResult(
            mss_result=mss,
            random_result=rand,
            technical_result=tech,
            mss_vs_random_excess=0.09,
            mss_vs_technical_excess=0.06,
            mss_vs_random_conclusion="MSS_OUTPERFORMS_RANDOM",
            mss_vs_technical_conclusion="MSS_OUTPERFORMS_TECHNICAL",
        )

    def test_contains_all_sections(self, sample_result: BenchmarkComparisonResult) -> None:
        lines = format_benchmark_report(sample_result)
        text = "\n".join(lines)
        assert "MSS Integrated Strategy" in text
        assert "Random Baseline" in text
        assert "Technical Baseline" in text
        assert "MSS vs Random Baseline" in text
        assert "MSS vs Technical Baseline" in text
        assert "Gate Decision" in text

    def test_go_when_both_outperform(self, sample_result: BenchmarkComparisonResult) -> None:
        lines = format_benchmark_report(sample_result)
        text = "\n".join(lines)
        assert "gate: PASS" in text
        assert "go_nogo: GO" in text

    def test_conditional_go_when_one_outperforms(self) -> None:
        mss = BenchmarkResult("MSS", 0.05, -0.03, 0.5, 0.8, 50, 0.0002, 0.01, [1e6])
        rand = BenchmarkResult("Rand", 0.03, -0.04, 0.48, 0.3, 50, 0.0001, 0.012, [1e6])
        tech = BenchmarkResult("Tech", 0.07, -0.02, 0.52, 0.9, 50, 0.0003, 0.011, [1e6])
        result = BenchmarkComparisonResult(
            mss_result=mss,
            random_result=rand,
            technical_result=tech,
            mss_vs_random_excess=0.02,
            mss_vs_technical_excess=-0.02,
            mss_vs_random_conclusion="MSS_OUTPERFORMS_RANDOM",
            mss_vs_technical_conclusion="TECHNICAL_OUTPERFORMS_MSS",
        )
        lines = format_benchmark_report(result)
        text = "\n".join(lines)
        assert "gate: WARN" in text
        assert "go_nogo: CONDITIONAL_GO" in text

    def test_nogo_when_none_outperform(self) -> None:
        mss = BenchmarkResult("MSS", 0.01, -0.03, 0.4, 0.2, 50, 0.0001, 0.01, [1e6])
        rand = BenchmarkResult("Rand", 0.05, -0.02, 0.52, 0.7, 50, 0.0002, 0.012, [1e6])
        tech = BenchmarkResult("Tech", 0.07, -0.02, 0.55, 0.9, 50, 0.0003, 0.011, [1e6])
        result = BenchmarkComparisonResult(
            mss_result=mss,
            random_result=rand,
            technical_result=tech,
            mss_vs_random_excess=-0.04,
            mss_vs_technical_excess=-0.06,
            mss_vs_random_conclusion="RANDOM_OUTPERFORMS_MSS",
            mss_vs_technical_conclusion="TECHNICAL_OUTPERFORMS_MSS",
        )
        lines = format_benchmark_report(result)
        text = "\n".join(lines)
        assert "gate: FAIL" in text
        assert "go_nogo: NO_GO" in text

    def test_conclusion_keywords_present(self, sample_result: BenchmarkComparisonResult) -> None:
        lines = format_benchmark_report(sample_result)
        text = "\n".join(lines)
        assert "conclusion: MSS_OUTPERFORMS_RANDOM" in text
        assert "conclusion: MSS_OUTPERFORMS_TECHNICAL" in text
