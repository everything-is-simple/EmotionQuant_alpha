from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from scripts.quality.governance_consistency_check import (
    Expectation,
    PROJECT_ROOT,
    check_governance_consistency,
    run_expectations,
)


def test_run_expectations_reports_missing_file() -> None:
    tmp_path = PROJECT_ROOT / ".reports" / ".tmp-test-artifacts" / f"gcc-missing-{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=False)
    try:
        expectations = (
            Expectation(
                rule_id="missing_file",
                path="docs/not-exists.md",
                pattern=r"anything",
                note="missing file should be reported",
            ),
        )
        violations = run_expectations(tmp_path, expectations)
        assert len(violations) == 1
        assert "missing file" in violations[0]
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_run_expectations_reports_missing_pattern() -> None:
    tmp_path = PROJECT_ROOT / ".reports" / ".tmp-test-artifacts" / f"gcc-pattern-{uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=False)
    try:
        target = tmp_path / "docs" / "sample.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("alpha beta gamma\n", encoding="utf-8")

        expectations = (
            Expectation(
                rule_id="missing_pattern",
                path="docs/sample.md",
                pattern=r"delta",
                note="pattern should be reported when absent",
            ),
        )
        violations = run_expectations(tmp_path, expectations)
        assert len(violations) == 1
        assert "missing pattern" in violations[0]
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_check_governance_consistency_passes_on_repository_baseline() -> None:
    assert check_governance_consistency(PROJECT_ROOT) == 0


def test_run_expectations_accepts_explicit_root_type_hint_only() -> None:
    expectations = (
        Expectation(
            rule_id="noop",
            path="docs/system-overview.md",
            pattern=r"EmotionQuant",
            note="sanity check",
        ),
    )
    assert run_expectations(Path(PROJECT_ROOT), expectations) == []
