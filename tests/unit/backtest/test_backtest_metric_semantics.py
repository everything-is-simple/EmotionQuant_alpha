from __future__ import annotations

import pytest

from src.backtest.pipeline import _compute_max_drawdown


def test_max_drawdown_uses_running_peak_instead_of_global_range() -> None:
    equity_curve = [100.0, 120.0, 110.0, 130.0]
    expected = (120.0 - 110.0) / 120.0
    assert _compute_max_drawdown(equity_curve) == pytest.approx(expected, abs=1e-8)


def test_max_drawdown_is_zero_for_monotonic_increase() -> None:
    assert _compute_max_drawdown([100.0, 101.0, 103.0, 106.0]) == 0.0
