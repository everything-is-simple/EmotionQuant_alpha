# MSS - Market Sentiment System
"""Market temperature, cycle analysis, and position recommendations."""

from src.algorithms.mss.engine import (
    MssInputSnapshot,
    MssPanorama,
    calculate_mss_score,
    detect_cycle,
    detect_trend,
)
from src.algorithms.mss.pipeline import MssRunResult, run_mss_scoring
from src.algorithms.mss.probe import MssProbeResult, run_mss_probe

# 向后兼容别名（TD-DA-003：正式名称为 MssPanorama）
MssScoreResult = MssPanorama

__all__ = [
    "MssInputSnapshot",
    "MssPanorama",
    "MssProbeResult",
    "MssRunResult",
    "MssScoreResult",
    "calculate_mss_score",
    "detect_cycle",
    "detect_trend",
    "run_mss_probe",
    "run_mss_scoring",
]
