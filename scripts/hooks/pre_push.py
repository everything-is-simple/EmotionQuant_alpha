#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_live(args: list[str]) -> int:
    print(f"[pre-push] > {' '.join(args)}")
    return subprocess.call(args, cwd=PROJECT_ROOT)


def main() -> int:
    skip = os.environ.get("EQ_SKIP_PRE_PUSH", "").lower() in {"1", "true", "yes"}
    if skip:
        print("[pre-push] skipped by EQ_SKIP_PRE_PUSH.")
        return 0

    checks = [
        [sys.executable, "-m", "scripts.quality.local_quality_check", "--contracts", "--governance"],
        ["pytest"],
    ]

    for cmd in checks:
        if run_live(cmd) != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
