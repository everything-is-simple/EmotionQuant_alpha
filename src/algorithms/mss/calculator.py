"""MSS Calculator 接口抽象（TD-DA-001 试点）。

将计算逻辑从编排中解耦，便于测试替换与后续全模块推广。

DESIGN_TRACE:
- docs/design/core-algorithms/mss/mss-algorithm.md (§3-§5)
- Governance/SpiralRoadmap/execution-cards/DEBT-CARD-B-CONTRACT.md (§2 TD-DA-001)
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from src.algorithms.mss.engine import (
    MssInputSnapshot,
    MssPanorama,
    calculate_mss_score,
)

DESIGN_TRACE = {
    "mss_algorithm": "docs/design/core-algorithms/mss/mss-algorithm.md",
    "debt_card_b": "Governance/SpiralRoadmap/execution-cards/DEBT-CARD-B-CONTRACT.md",
}


@runtime_checkable
class MssCalculator(Protocol):
    """MSS 计算接口协议。

    实现者必须接受 ``MssInputSnapshot`` 和历史温度序列，返回 ``MssPanorama``。
    """

    def calculate(
        self,
        snapshot: MssInputSnapshot,
        *,
        temperature_history: Sequence[float] | None = None,
        threshold_mode: str = "adaptive",
        stale_hard_limit_days: int = 3,
    ) -> MssPanorama: ...


class DefaultMssCalculator:
    """默认 MSS 计算实现：委托给 engine.calculate_mss_score()。"""

    def calculate(
        self,
        snapshot: MssInputSnapshot,
        *,
        temperature_history: Sequence[float] | None = None,
        threshold_mode: str = "adaptive",
        stale_hard_limit_days: int = 3,
    ) -> MssPanorama:
        return calculate_mss_score(
            snapshot,
            temperature_history=temperature_history,
            threshold_mode=threshold_mode,
            stale_hard_limit_days=stale_hard_limit_days,
        )
