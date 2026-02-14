#!/usr/bin/env python3
"""
Governance consistency checks for system-overview / steering / capability docs.

Goal:
- Detect drift across SoT navigation, 6A closure clauses, and governance wording.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Expectation:
    rule_id: str
    path: str
    pattern: str
    note: str


EXPECTATIONS: tuple[Expectation, ...] = (
    # System overview navigation and wording
    Expectation(
        "overview_closure",
        "docs/system-overview.md",
        r"run/test/artifact/review/sync",
        "System overview must state five-piece closure wording",
    ),
    Expectation(
        "overview_closure",
        "docs/system-overview.md",
        r"每圈只允许\s*1\s*个主目标",
        "System overview must keep one-primary-objective rule",
    ),
    Expectation(
        "overview_closure",
        "docs/system-overview.md",
        r"1-3\s*个能力包切片",
        "System overview must keep 1-3 slice rule",
    ),
    Expectation(
        "overview_sot",
        "docs/system-overview.md",
        r"Governance/steering/TRD\.md",
        "System overview navigation must include TRD",
    ),
    Expectation(
        "overview_sot",
        "docs/system-overview.md",
        r"Governance/steering/GOVERNANCE-STRUCTURE\.md",
        "System overview navigation must include governance SoT matrix",
    ),
    Expectation(
        "overview_a_share_precision",
        "docs/system-overview.md",
        r"Governance/steering/系统铁律\.md",
        "A-share precision note should link to iron rules",
    ),
    Expectation(
        "overview_track_disambiguation",
        "docs/system-overview.md",
        r"研究主选",
        "System overview should explicitly mention research track",
    ),
    Expectation(
        "overview_track_disambiguation",
        "docs/system-overview.md",
        r"收口主线",
        "System overview should explicitly mention delivery baseline track",
    ),
    # TRD alignment
    Expectation(
        "trd_track_disambiguation",
        "Governance/steering/TRD.md",
        r"回测主线",
        "TRD must define delivery baseline track",
    ),
    Expectation(
        "trd_track_disambiguation",
        "Governance/steering/TRD.md",
        r"回测研究",
        "TRD must define research track",
    ),
    Expectation(
        "trd_sot_link",
        "Governance/steering/TRD.md",
        r"docs/system-overview\.md",
        "TRD should keep link to system overview",
    ),
    # 6A and CP closure clauses
    Expectation(
        "workflow_closure",
        "Governance/steering/6A-WORKFLOW.md",
        r"run/test/artifact/review/sync",
        "6A workflow must preserve five-piece closure wording",
    ),
    Expectation(
        "workflow_sync_set",
        "Governance/steering/6A-WORKFLOW.md",
        r"Governance/specs/spiral-s\{N\}/final\.md",
        "6A workflow must include final.md sync target",
    ),
    Expectation(
        "workflow_sync_set",
        "Governance/steering/6A-WORKFLOW.md",
        r"Governance/Capability/SPIRAL-CP-OVERVIEW\.md",
        "6A workflow must include roadmap sync target",
    ),
    Expectation(
        "cp_closure",
        "Governance/Capability/SPIRAL-CP-OVERVIEW.md",
        r"run\s*\+\s*test\s*\+\s*artifact\s*\+\s*review\s*\+\s*sync",
        "SPIRAL-CP-OVERVIEW must preserve five-piece closure wording",
    ),
    # SoT matrix
    Expectation(
        "sot_matrix",
        "Governance/steering/GOVERNANCE-STRUCTURE.md",
        r"Governance/steering/TRD\.md",
        "SoT matrix must include TRD",
    ),
    Expectation(
        "sot_matrix",
        "Governance/steering/GOVERNANCE-STRUCTURE.md",
        r"docs/system-overview\.md",
        "SoT matrix must include system overview",
    ),
    Expectation(
        "sot_matrix",
        "Governance/steering/GOVERNANCE-STRUCTURE.md",
        r"CROSS-DOC-CHANGE-LINKAGE-TEMPLATE\.md",
        "SoT matrix should include cross-doc linkage template",
    ),
    # A-share precision wording in governing docs
    Expectation(
        "a_share_precision",
        "Governance/steering/系统铁律.md",
        r"主板10%.*20%.*ST 5%",
        "Iron rules must preserve board-specific limit precision",
    ),
    Expectation(
        "a_share_precision",
        "Governance/steering/CORE-PRINCIPLES.md",
        r"主板10%.*20%.*ST 5%",
        "Core principles must preserve board-specific limit precision",
    ),
)


def run_expectations(
    root: Path,
    expectations: tuple[Expectation, ...] = EXPECTATIONS,
) -> list[str]:
    violations: list[str] = []
    cache: dict[str, str] = {}

    for exp in expectations:
        text = cache.get(exp.path)
        if text is None:
            target = root / exp.path
            if not target.exists():
                violations.append(f"[{exp.rule_id}] missing file: {exp.path}")
                continue
            text = target.read_text(encoding="utf-8")
            cache[exp.path] = text

        if re.search(exp.pattern, text, flags=re.MULTILINE) is None:
            violations.append(
                f"[{exp.rule_id}] {exp.path}: missing pattern /{exp.pattern}/ ({exp.note})"
            )

    return violations


def check_governance_consistency(root: Path = PROJECT_ROOT) -> int:
    violations = run_expectations(root)
    if not violations:
        print(f"[governance] pass ({len(EXPECTATIONS)} checks)")
        return 0

    print(f"[governance] failed ({len(violations)} violations)")
    for item in violations:
        print(f"  - {item}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check governance/system-overview consistency in SoT docs."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root to scan (default: repository root)",
    )
    args = parser.parse_args()
    return check_governance_consistency(args.root.resolve())


if __name__ == "__main__":
    sys.exit(main())
