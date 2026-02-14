from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

ALLOWED_QUALITY_STATES = {"normal", "stale", "cold_start"}

STATUS_READY = "ready"
STATUS_DEGRADED = "degraded"
STATUS_BLOCKED = "blocked"


@dataclass(frozen=True)
class DataGateDecision:
    trade_date: str
    status: str
    is_ready: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    max_stale_days: int = 0
    coverage_ratio: float = 0.0
    cross_day_consistent: bool = True


def evaluate_data_quality_gate(
    *,
    trade_date: str,
    coverage_ratio: float,
    source_trade_dates: Mapping[str, str],
    quality_by_dataset: Mapping[str, str],
    stale_days_by_dataset: Mapping[str, int],
    min_coverage: float = 0.95,
    stale_hard_limit: int = 3,
) -> DataGateDecision:
    issues: list[str] = []
    warnings: list[str] = []

    if not 0 <= coverage_ratio <= 1:
        issues.append(f"invalid_coverage_ratio:{coverage_ratio}")
    elif coverage_ratio < min_coverage:
        issues.append(f"coverage_below_threshold:{coverage_ratio:.4f}<{min_coverage:.4f}")

    source_dates = set(source_trade_dates.values())
    cross_day_consistent = len(source_dates) <= 1
    if not cross_day_consistent:
        issues.append("cross_day_inconsistency")

    max_stale_days = max(stale_days_by_dataset.values(), default=0)
    if max_stale_days > stale_hard_limit:
        issues.append(f"stale_days_exceed_limit:{max_stale_days}>{stale_hard_limit}")

    for dataset, quality in quality_by_dataset.items():
        stale_days = stale_days_by_dataset.get(dataset, 0)
        if quality not in ALLOWED_QUALITY_STATES:
            issues.append(f"invalid_quality_state:{dataset}:{quality}")
            continue
        if stale_days < 0:
            issues.append(f"negative_stale_days:{dataset}:{stale_days}")
            continue
        if quality == "normal" and stale_days != 0:
            issues.append(f"normal_with_stale_days:{dataset}:{stale_days}")
        elif quality == "stale" and stale_days == 0:
            issues.append(f"stale_without_lag:{dataset}")
        elif quality == "cold_start":
            warnings.append(f"cold_start_dataset:{dataset}")

    if issues:
        status = STATUS_BLOCKED
    elif max_stale_days > 0 or warnings:
        status = STATUS_DEGRADED
    else:
        status = STATUS_READY

    return DataGateDecision(
        trade_date=trade_date,
        status=status,
        is_ready=status != STATUS_BLOCKED,
        issues=issues,
        warnings=warnings,
        max_stale_days=max_stale_days,
        coverage_ratio=coverage_ratio,
        cross_day_consistent=cross_day_consistent,
    )
