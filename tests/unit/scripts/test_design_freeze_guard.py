"""S6 设计冻结守卫测试。

验证核心模块的 DESIGN_TRACE 标记存在性，
确保设计-代码溯源链完整。
"""

from __future__ import annotations

from pathlib import Path

from scripts.quality.design_traceability_check import (
    PROJECT_ROOT,
    REQUIRED_TRACE_MARKERS,
    check_design_traceability,
)

# S6 新增模块必须有 DESIGN_TRACE
S6_MODULES = (
    "src/pipeline/consistency.py",
    "src/pipeline/main.py",
)


def test_s6_modules_have_design_trace_marker() -> None:
    """S6 模块必须含 DESIGN_TRACE 变量声明。"""
    for rel_path in S6_MODULES:
        file_path = PROJECT_ROOT / rel_path
        assert file_path.exists(), f"{rel_path} not found"
        text = file_path.read_text(encoding="utf-8", errors="replace")
        assert "DESIGN_TRACE" in text, f"{rel_path} missing DESIGN_TRACE marker"


def test_consistency_module_traces_to_enhancement_plan() -> None:
    """consistency.py 必须溯源到 ENH-08 改进行动计划。"""
    text = (PROJECT_ROOT / "src/pipeline/consistency.py").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "eq-improvement-plan-core-frozen.md" in text


def test_consistency_module_traces_to_s6_execution_card() -> None:
    """consistency.py 必须溯源到 S6 执行卡。"""
    text = (PROJECT_ROOT / "src/pipeline/consistency.py").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "S6-EXECUTION-CARD.md" in text


def test_main_pipeline_traces_to_roadmap() -> None:
    """main.py 必须溯源到 Spiral 路线。"""
    text = (PROJECT_ROOT / "src/pipeline/main.py").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md" in text


def test_required_trace_markers_covers_core_modules() -> None:
    """REQUIRED_TRACE_MARKERS 应覆盖所有核心执行模块。"""
    core_modules = {
        "src/algorithms/mss/pipeline.py",
        "src/algorithms/irs/pipeline.py",
        "src/algorithms/pas/pipeline.py",
        "src/algorithms/validation/pipeline.py",
        "src/integration/pipeline.py",
        "src/pipeline/main.py",
    }
    registered = set(REQUIRED_TRACE_MARKERS.keys())
    missing = core_modules - registered
    assert not missing, f"Core modules not registered in traceability check: {missing}"


def test_design_traceability_check_passes_on_repository() -> None:
    """在当前仓库运行设计溯源检查应通过。"""
    assert check_design_traceability() == 0


def test_all_registered_files_exist() -> None:
    """REQUIRED_TRACE_MARKERS 中的所有文件必须在仓库中存在。"""
    missing = []
    for rel_path in REQUIRED_TRACE_MARKERS:
        if not (PROJECT_ROOT / rel_path).exists():
            missing.append(rel_path)
    assert not missing, f"Registered files not found: {missing}"
