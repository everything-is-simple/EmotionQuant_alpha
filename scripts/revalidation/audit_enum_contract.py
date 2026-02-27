"""枚举契约审计脚本（TD-DA-009 关账证据）。

审计目标：
- 校验 src/models/enums.py 与 docs/naming-contracts.schema.json 的关键枚举集合一致。
- 产出机器可读审计结果，供 debts.md / review 同步引用。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.enums import GateDecision, MssCycle, PasDirection, RotationStatus, Trend


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    schema_path = project_root / "docs" / "naming-contracts.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    runtime = {
        "trend": sorted([e.value for e in Trend]),
        "mss_cycle": sorted([e.value for e in MssCycle]),
        "pas_direction": sorted([e.value for e in PasDirection]),
        "rotation_status": sorted([e.value for e in RotationStatus]),
        "validation_gate": sorted([e.value for e in GateDecision]),
    }
    expected = {k: sorted(v) for k, v in schema.get("enums", {}).items()}

    checks: dict[str, dict[str, object]] = {}
    all_passed = True
    for key in sorted(expected.keys()):
        got = runtime.get(key, [])
        want = expected.get(key, [])
        passed = got == want
        all_passed = all_passed and passed
        checks[key] = {
            "passed": passed,
            "expected": want,
            "runtime": got,
        }

    out_dir = project_root / "artifacts" / "spiral-s0s2" / "revalidation" / "20260227_104537"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "enum_contract_audit.json"
    out_path.write_text(
        json.dumps(
            {
                "status": "PASS" if all_passed else "FAIL",
                "checks": checks,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(str(out_path))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
