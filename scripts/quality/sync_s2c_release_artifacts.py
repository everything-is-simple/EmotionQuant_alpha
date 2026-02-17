#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES: tuple[str, ...] = (
    "quality_gate_report.md",
    "s2_go_nogo_decision.md",
    "integrated_recommendation_sample.parquet",
)

SYNC_FILES: tuple[str, ...] = (
    "integrated_recommendation_sample.parquet",
    "quality_gate_report.md",
    "s2_go_nogo_decision.md",
    "irs_factor_intermediate_sample.parquet",
    "pas_factor_intermediate_sample.parquet",
    "validation_factor_report_sample.parquet",
    "validation_weight_report_sample.parquet",
    "validation_weight_plan_sample.parquet",
    "validation_run_manifest_sample.json",
    "s2c_semantics_traceability_matrix.md",
    "s2c_algorithm_closeout.md",
    "error_manifest_sample.json",
)


def _extract_markdown_value(text: str, key: str) -> str:
    pattern = rf"^- {re.escape(key)}:\s*(.+)$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if match is None:
        return ""
    return match.group(1).strip()


def _validate_release_artifacts(release_dir: Path) -> list[str]:
    violations: list[str] = []
    for filename in REQUIRED_FILES:
        if not (release_dir / filename).exists():
            violations.append(f"missing required artifact: {filename}")

    quality_path = release_dir / "quality_gate_report.md"
    go_nogo_path = release_dir / "s2_go_nogo_decision.md"
    integrated_path = release_dir / "integrated_recommendation_sample.parquet"
    if violations:
        return violations

    quality_text = quality_path.read_text(encoding="utf-8")
    quality_status = _extract_markdown_value(quality_text, "status").upper()
    if quality_status not in {"PASS", "WARN"}:
        violations.append(f"quality_gate_report.status must be PASS/WARN, got: {quality_status or 'EMPTY'}")

    go_nogo_text = go_nogo_path.read_text(encoding="utf-8")
    go_nogo_decision = _extract_markdown_value(go_nogo_text, "decision").upper()
    if go_nogo_decision != "GO":
        violations.append(f"s2_go_nogo_decision.decision must be GO, got: {go_nogo_decision or 'EMPTY'}")

    try:
        integrated_count = int(len(pd.read_parquet(integrated_path)))
    except Exception as exc:  # pragma: no cover - defensive guard
        violations.append(f"failed to read integrated_recommendation_sample.parquet: {exc}")
        return violations
    if integrated_count <= 0:
        violations.append("integrated_recommendation_sample.parquet must have at least one row")

    return violations


def sync_s2c_release_artifacts(*, trade_date: str, root: Path = PROJECT_ROOT) -> int:
    root = root.resolve()
    release_dir = root / "artifacts" / "spiral-s2c" / trade_date
    spec_dir = root / "Governance" / "specs" / "spiral-s2c"

    if not release_dir.exists():
        print(f"[sync-s2c] missing release artifacts directory: {release_dir}")
        return 1

    violations = _validate_release_artifacts(release_dir)
    if violations:
        print("[sync-s2c] validation failed")
        for item in violations:
            print(f"  - {item}")
        return 1

    spec_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for filename in SYNC_FILES:
        src = release_dir / filename
        if not src.exists():
            continue
        dst = spec_dir / filename
        shutil.copy2(src, dst)
        copied.append(filename)

    print(f"[sync-s2c] synced {len(copied)} files for trade_date={trade_date}")
    for name in copied:
        print(f"  - {name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync validated S2c release artifacts to Governance/specs/spiral-s2c."
    )
    parser.add_argument("--trade-date", required=True, help="Trade date in YYYYMMDD.")
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root path (default: repository root).",
    )
    args = parser.parse_args()
    return sync_s2c_release_artifacts(trade_date=str(args.trade_date), root=args.root)


if __name__ == "__main__":
    sys.exit(main())
