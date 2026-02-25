"""IRS Calculator 接口抽象（TD-DA-001 跟进）。

将行业轮动评分逻辑从编排中解耦，便于测试替换与后续推广。
当前 IRS 评分逻辑耦合于 pipeline.run_irs_daily，此处先定义接口协议，
具体实现以 Protocol + thin wrapper 方式提供。

DESIGN_TRACE:
- docs/design/core-algorithms/irs/irs-algorithm.md (§3 六因子, §5 轮动状态)
- Governance/SpiralRoadmap/execution-cards/DEBT-CARD-B-CONTRACT.md (§2 TD-DA-001)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd

DESIGN_TRACE = {
    "irs_algorithm": "docs/design/core-algorithms/irs/irs-algorithm.md",
    "debt_card_b": "Governance/SpiralRoadmap/execution-cards/DEBT-CARD-B-CONTRACT.md",
}


@runtime_checkable
class IrsCalculator(Protocol):
    """IRS 行业评分接口协议。

    输入：行业快照 DataFrame（当日 + 历史）、基线参数。
    输出：评分后的 DataFrame（含 industry_score 等字段）。
    """

    def score(
        self,
        source: pd.DataFrame,
        history: pd.DataFrame,
        *,
        trade_date: str,
        baseline_map: dict[str, tuple[float, float]] | None = None,
    ) -> pd.DataFrame:
        """对所有行业执行六因子评分，返回结果 DataFrame。"""
        ...


class DefaultIrsCalculator:
    """默认 IRS 评分实现：委托给 pipeline 内部逻辑。

    当前 IRS 评分紧耦合于 run_irs_daily，此实现通过直接调用
    pipeline 完成评分。后续可逐步将因子计算拆出。
    """

    def score(
        self,
        source: pd.DataFrame,
        history: pd.DataFrame,
        *,
        trade_date: str,
        baseline_map: dict[str, tuple[float, float]] | None = None,
    ) -> pd.DataFrame:
        # 延迟导入以避免循环依赖
        from src.algorithms.irs.pipeline import run_irs_daily
        from src.config.config import Config

        raise NotImplementedError(
            "DefaultIrsCalculator.score() 尚未解耦，"
            "当前请直接调用 run_irs_daily()。"
            "此接口为 Calculator/Repository 试点的占位定义，"
            "待后续 Spiral 拆分因子计算后启用。"
        )
