# IRS - Industry Rotation System
"""Industry rotation tracking with 6-factor scoring."""

from src.algorithms.irs.pipeline import IrsRunResult, run_irs_daily

__all__ = [
    "IrsRunResult",
    "run_irs_daily",
]
