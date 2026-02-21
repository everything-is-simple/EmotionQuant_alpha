from __future__ import annotations

from src.algorithms.validation.pipeline import _decay_proxy_from_ic


def test_decay_proxy_is_monotonic_with_absolute_ic_strength() -> None:
    low = _decay_proxy_from_ic(0.10)
    mid = _decay_proxy_from_ic(0.35)
    high = _decay_proxy_from_ic(0.70)

    assert 0.0 <= low <= 1.0
    assert 0.0 <= mid <= 1.0
    assert 0.0 <= high <= 1.0
    assert low < mid < high
    assert high >= 0.70
