"""EmotionQuant 系统级异常定义。"""

from __future__ import annotations


class DataNotReadyError(RuntimeError):
    """依赖数据未就绪（stale_days 超过阈值），阻断主流程。

    设计基线: docs/design/core-algorithms/mss/mss-algorithm.md §10.5
    """

    def __init__(self, message: str = "data_not_ready", *, stale_days: int = 0) -> None:
        self.stale_days = stale_days
        super().__init__(message)
