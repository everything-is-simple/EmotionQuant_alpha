"""质量监控模块（占位实现）。

当前仅定义 QualityMonitor 接口骨架，具体监控逻辑待后续迭代。
"""

from __future__ import annotations

from typing import Any


class QualityMonitor:
    """质量监控占位实现。"""

    def check(self) -> dict[str, Any]:
        raise NotImplementedError("QualityMonitor.check is not implemented")
