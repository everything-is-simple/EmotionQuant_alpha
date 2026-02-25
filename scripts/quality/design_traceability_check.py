#!/usr/bin/env python3
"""
Design-to-code traceability check.

Goal:
- Ensure key execution modules explicitly declare DESIGN_TRACE markers.
- Prevent silent drift where implementation cannot be mapped to design sources.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_TRACE_MARKERS: dict[str, list[str]] = {
    "src/algorithms/irs/pipeline.py": [
        "DESIGN_TRACE",
        "docs/design/core-algorithms/irs/irs-algorithm.md",
    ],
    "src/algorithms/pas/pipeline.py": [
        "DESIGN_TRACE",
        "docs/design/core-algorithms/pas/pas-algorithm.md",
    ],
    "src/algorithms/mss/engine.py": [
        "DESIGN_TRACE",
        "docs/design/core-algorithms/mss/mss-algorithm.md",
    ],
    "src/algorithms/mss/pipeline.py": [
        "DESIGN_TRACE",
        "docs/design/core-algorithms/mss/mss-algorithm.md",
    ],
    "src/algorithms/mss/probe.py": [
        "DESIGN_TRACE",
        "Governance/SpiralRoadmap/execution-cards/S1B-EXECUTION-CARD.md",
    ],
    "src/algorithms/validation/pipeline.py": [
        "DESIGN_TRACE",
        "docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md",
    ],
    "src/integration/pipeline.py": [
        "DESIGN_TRACE",
        "docs/design/core-algorithms/integration/integration-algorithm.md",
    ],
    "src/pipeline/recommend.py": [
        "DESIGN_TRACE",
        "Governance/SpiralRoadmap/execution-cards/S2C-EXECUTION-CARD.md",
    ],
    "src/pipeline/main.py": [
        "DESIGN_TRACE",
        "Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md",
    ],
    "src/backtest/pipeline.py": [
        "DESIGN_TRACE",
        "docs/design/core-infrastructure/backtest/backtest-algorithm.md",
    ],
    "src/trading/pipeline.py": [
        "DESIGN_TRACE",
        "docs/design/core-infrastructure/trading/trading-algorithm.md",
    ],
}


def check_design_traceability() -> int:
    violations: list[str] = []
    checked = 0

    for rel_path, expected_markers in REQUIRED_TRACE_MARKERS.items():
        file_path = PROJECT_ROOT / rel_path
        if not file_path.exists():
            violations.append(f"{rel_path}: file_not_found")
            continue

        checked += 1
        text = file_path.read_text(encoding="utf-8", errors="replace")
        for marker in expected_markers:
            if marker not in text:
                violations.append(f"{rel_path}: missing_marker={marker}")

    if violations:
        print("[traceability] fail")
        for item in violations:
            print(f"  - {item}")
        return 1

    print(f"[traceability] pass ({checked} files)")
    return 0
