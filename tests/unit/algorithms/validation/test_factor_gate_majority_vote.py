from __future__ import annotations

from src.algorithms.validation.pipeline import _aggregate_factor_gate


def test_all_pass_returns_pass() -> None:
    assert _aggregate_factor_gate(["PASS", "PASS", "PASS", "PASS"]) == "PASS"


def test_all_fail_returns_fail() -> None:
    assert _aggregate_factor_gate(["FAIL", "FAIL", "FAIL", "FAIL"]) == "FAIL"


def test_majority_fail_returns_fail() -> None:
    # 3/4 FAIL → > 50% → FAIL
    assert _aggregate_factor_gate(["FAIL", "FAIL", "FAIL", "PASS"]) == "FAIL"


def test_half_fail_returns_warn() -> None:
    # 2/4 FAIL → exactly 50% → WARN (not FAIL)
    assert _aggregate_factor_gate(["FAIL", "FAIL", "PASS", "PASS"]) == "WARN"


def test_minority_fail_returns_warn() -> None:
    # 1/4 FAIL → < 50% → WARN
    assert _aggregate_factor_gate(["FAIL", "PASS", "PASS", "PASS"]) == "WARN"


def test_warn_without_fail_returns_warn() -> None:
    assert _aggregate_factor_gate(["WARN", "PASS", "PASS", "PASS"]) == "WARN"


def test_single_fail_returns_fail() -> None:
    # 1/1 FAIL → > 50% → FAIL
    assert _aggregate_factor_gate(["FAIL"]) == "FAIL"


def test_single_pass_returns_pass() -> None:
    assert _aggregate_factor_gate(["PASS"]) == "PASS"
