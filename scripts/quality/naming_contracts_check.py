#!/usr/bin/env python3
"""
Naming / contracts consistency checks for design docs.

Goal:
- Detect drift for critical enum names, thresholds, and bridge contracts.
- Provide a lightweight gate that can be used in local checks / CI.
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
    # Trend / naming base
    Expectation(
        "trend_sideways",
        "docs/naming-conventions.md",
        r"sideways",
        "Trend enum must include sideways",
    ),
    Expectation(
        "trend_sideways",
        "docs/naming-conventions.md",
        r"不使用\s*`?flat`?",
        "Naming spec must forbid flat as trend enum",
    ),
    Expectation(
        "trend_sideways",
        "docs/design/core-algorithms/mss/mss-algorithm.md",
        r'trend取值:\s*"up"\s*\|\s*"down"\s*\|\s*"sideways"',
        "MSS trend enum must be up/down/sideways",
    ),
    # unknown fallback
    Expectation(
        "unknown_fallback",
        "docs/naming-conventions.md",
        r"\bunknown\b",
        "Naming spec must define unknown fallback",
    ),
    Expectation(
        "unknown_fallback",
        "docs/design/core-algorithms/mss/mss-api.md",
        r"unknown",
        "MSS API must expose unknown",
    ),
    Expectation(
        "unknown_fallback",
        "docs/design/core-algorithms/mss/mss-api.md",
        r"合法降级",
        "MSS API must describe unknown as legal degradation",
    ),
    # risk_reward_ratio naming and threshold alignment
    Expectation(
        "rr_name",
        "docs/naming-conventions.md",
        r"risk_reward_ratio",
        "Canonical RR field name must exist",
    ),
    Expectation(
        "rr_name",
        "docs/naming-conventions.md",
        r"rr_ratio",
        "Non-canonical rr_ratio must be documented as forbidden alias",
    ),
    Expectation(
        "rr_threshold",
        "docs/design/core-algorithms/pas/pas-algorithm.md",
        r"risk_reward_ratio[^\n]*(?:>=|≥)\s*1\.0",
        "PAS algorithm must use RR >= 1.0",
    ),
    Expectation(
        "rr_threshold",
        "docs/design/core-algorithms/pas/pas-data-models.md",
        r"risk_reward_ratio[^\n]*(?:>=|≥)\s*1\.0",
        "PAS data model must use RR >= 1.0",
    ),
    Expectation(
        "rr_threshold",
        "docs/design/core-infrastructure/trading/trading-algorithm.md",
        r"risk_reward_ratio\s*<\s*1\.0",
        "Trading execution must filter RR < 1.0",
    ),
    Expectation(
        "rr_threshold",
        "docs/design/core-infrastructure/backtest/backtest-algorithm.md",
        r"risk_reward_ratio\s*<\s*1\.0",
        "Backtest execution must filter RR < 1.0",
    ),
    # STRONG_BUY threshold alignment
    Expectation(
        "strong_buy_75",
        "docs/naming-conventions.md",
        r"(?:STRONG_BUY[^\n]*75|75[^\n]*STRONG_BUY)",
        "Naming spec must align STRONG_BUY threshold with 75",
    ),
    Expectation(
        "strong_buy_75",
        "docs/design/core-algorithms/integration/integration-algorithm.md",
        r"(?:STRONG_BUY[^\n]*75|75[^\n]*STRONG_BUY)",
        "Integration must align STRONG_BUY threshold with 75",
    ),
    Expectation(
        "strong_buy_75",
        "docs/design/core-infrastructure/data-layer/data-layer-data-models.md",
        r"(?:STRONG_BUY[^\n]*75|75[^\n]*STRONG_BUY)",
        "Data layer models must align STRONG_BUY threshold with 75",
    ),
    Expectation(
        "strong_buy_75",
        "docs/design/core-infrastructure/gui/gui-algorithm.md",
        r"final_score\s*>=\s*75",
        "GUI display rules must align STRONG_BUY threshold with 75",
    ),
    # BUY threshold 70 alignment
    Expectation(
        "buy_70",
        "docs/naming-conventions.md",
        r"(?:BUY[^\n]*70|70[^\n]*BUY)",
        "Naming spec must align BUY threshold with 70",
    ),
    Expectation(
        "buy_70",
        "docs/design/core-algorithms/integration/integration-algorithm.md",
        r"(?:BUY[^\n]*70|70[^\n]*BUY)",
        "Integration must align BUY threshold with 70",
    ),
    # PAS grade B threshold 55 alignment
    Expectation(
        "pas_b_55",
        "docs/naming-conventions.md",
        r"\[55,\s*70\)",
        "Naming spec must align PAS grade-B threshold with 55",
    ),
    Expectation(
        "pas_b_55",
        "docs/design/core-algorithms/pas/pas-algorithm.md",
        r"\[55,\s*70\)",
        "PAS algorithm must align grade-B threshold with 55",
    ),
    Expectation(
        "pas_b_55",
        "docs/design/core-algorithms/pas/pas-data-models.md",
        r"\[55,\s*70\)",
        "PAS data models must align grade-B threshold with 55",
    ),
    # RR threshold 1.0 boundary
    Expectation(
        "rr_threshold",
        "docs/naming-conventions.md",
        r"1\.0",
        "Naming spec must explicitly carry RR threshold 1.0",
    ),
    # stock_code / ts_code boundary
    Expectation(
        "code_boundary",
        "docs/naming-conventions.md",
        r"stock_code",
        "Naming spec must define stock_code",
    ),
    Expectation(
        "code_boundary",
        "docs/naming-conventions.md",
        r"ts_code",
        "Naming spec must define ts_code",
    ),
    Expectation(
        "code_boundary",
        "docs/design/core-infrastructure/data-layer/data-layer-api.md",
        r"L1 数据落库",
        "Data layer API must document L1 code boundary",
    ),
    Expectation(
        "code_boundary",
        "docs/design/core-infrastructure/data-layer/data-layer-api.md",
        r"保持 `ts_code`",
        "L1 boundary must keep ts_code",
    ),
    Expectation(
        "code_boundary",
        "docs/design/core-infrastructure/data-layer/data-layer-api.md",
        r"L2\+ 内部使用",
        "L2+ boundary must be explicitly documented",
    ),
    Expectation(
        "code_boundary",
        "docs/design/core-infrastructure/data-layer/data-layer-api.md",
        r"stock_code",
        "L2+ boundary must use stock_code",
    ),
    # Gate PASS/WARN/FAIL
    Expectation(
        "gate_triplet",
        "docs/design/core-algorithms/validation/factor-weight-validation-data-models.md",
        r"final_gate",
        "Validation models must define final_gate",
    ),
    Expectation(
        "gate_triplet",
        "docs/design/core-algorithms/validation/factor-weight-validation-data-models.md",
        r"PASS/WARN/FAIL",
        "Validation models must preserve PASS/WARN/FAIL triplet",
    ),
    Expectation(
        "gate_triplet",
        "docs/design/core-algorithms/integration/integration-algorithm.md",
        r"final_gate",
        "Integration must consume final_gate",
    ),
    Expectation(
        "gate_triplet",
        "docs/design/core-algorithms/integration/integration-algorithm.md",
        r"PASS/WARN/FAIL",
        "Integration must preserve PASS/WARN/FAIL triplet",
    ),
    # Contract version checks (Integration/Trading/Backtest)
    Expectation(
        "contract_version",
        "docs/design/core-algorithms/integration/integration-algorithm.md",
        r"contract_version",
        "Integration must define contract_version compatibility check",
    ),
    Expectation(
        "contract_version",
        "docs/design/core-algorithms/integration/integration-algorithm.md",
        r"nc-v1",
        "Integration must bind to canonical contract version nc-v1",
    ),
    Expectation(
        "contract_version",
        "docs/design/core-infrastructure/trading/trading-algorithm.md",
        r"contract_version",
        "Trading must define contract_version compatibility check",
    ),
    Expectation(
        "contract_version",
        "docs/design/core-infrastructure/backtest/backtest-algorithm.md",
        r"contract_version",
        "Backtest must define contract_version compatibility check",
    ),
    Expectation(
        "contract_version_api",
        "docs/design/core-algorithms/integration/integration-api.md",
        r"contract_version",
        "Integration API must expose contract_version compatibility input",
    ),
    Expectation(
        "contract_version_api",
        "docs/design/core-algorithms/integration/integration-api.md",
        r"nc-v1",
        "Integration API must bind contract_version to nc-v1",
    ),
    Expectation(
        "contract_version_api",
        "docs/design/core-infrastructure/trading/trading-api.md",
        r"contract_version",
        "Trading API must define contract_version compatibility check",
    ),
    Expectation(
        "contract_version_api",
        "docs/design/core-infrastructure/trading/trading-api.md",
        r"blocked_contract_mismatch",
        "Trading API must expose blocked_contract_mismatch state",
    ),
    Expectation(
        "contract_version_api",
        "docs/design/core-infrastructure/backtest/backtest-api.md",
        r"contract_version",
        "Backtest API must define contract_version compatibility check",
    ),
    Expectation(
        "contract_version_api",
        "docs/design/core-infrastructure/backtest/backtest-api.md",
        r"blocked_contract_mismatch",
        "Backtest API must expose blocked_contract_mismatch state",
    ),
    # Schema-first source
    Expectation(
        "schema_first",
        "docs/naming-contracts.schema.json",
        r"\"schema_version\"\s*:\s*\"nc-v1\"",
        "Schema file must define nc-v1 contract version",
    ),
    Expectation(
        "schema_first",
        "docs/naming-contracts.schema.json",
        r"\"strong_buy_min\"\s*:\s*75",
        "Schema file must define strong_buy_min=75",
    ),
    Expectation(
        "schema_first",
        "docs/naming-contracts.schema.json",
        r"\"buy_min\"\s*:\s*70",
        "Schema file must define buy_min=70",
    ),
    Expectation(
        "schema_first",
        "docs/naming-contracts.schema.json",
        r"\"pas_grade_b_min\"\s*:\s*55",
        "Schema file must define pas_grade_b_min=55",
    ),
    Expectation(
        "schema_first",
        "docs/naming-contracts.schema.json",
        r"\"min\"\s*:\s*1\.0",
        "Schema file must define RR min=1.0",
    ),
    # Glossary / change template
    Expectation(
        "glossary_template",
        "docs/naming-contracts-glossary.md",
        r"contract_version",
        "Glossary must include contract_version term",
    ),
    Expectation(
        "glossary_template",
        "Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md",
        r"联动文档清单",
        "Naming-contract template must include linkage checklist",
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


def check_naming_contracts(root: Path = PROJECT_ROOT) -> int:
    violations = run_expectations(root)
    if not violations:
        print(f"[contracts] pass ({len(EXPECTATIONS)} checks)")
        return 0

    print(f"[contracts] failed ({len(violations)} violations)")
    for item in violations:
        print(f"  - {item}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check naming/contracts consistency in core design docs."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root to scan (default: repository root)",
    )
    args = parser.parse_args()
    return check_naming_contracts(args.root.resolve())


if __name__ == "__main__":
    sys.exit(main())
