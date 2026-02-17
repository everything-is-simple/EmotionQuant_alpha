# Backtest module
"""Backtesting engine with A-share rules (T+1, limit up/down)."""

from src.backtest.pipeline import BacktestRunResult, run_backtest

__all__ = ["BacktestRunResult", "run_backtest"]
