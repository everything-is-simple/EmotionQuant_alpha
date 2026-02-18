#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def _timeout_seconds() -> int | None:
    raw = os.environ.get("EQ_PRE_PUSH_TIMEOUT_SEC", "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        print(f"[pre-push] invalid EQ_PRE_PUSH_TIMEOUT_SEC={raw!r}, fallback to no timeout.")
        return None
    if value <= 0:
        return None
    return value


def run_live(args: list[str], timeout: int | None) -> int:
    print(f"[pre-push] > {' '.join(args)}")
    return subprocess.call(args, cwd=PROJECT_ROOT, env=_child_env(), timeout=timeout)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    skip = os.environ.get("EQ_SKIP_PRE_PUSH", "").lower() in {"1", "true", "yes"}
    if skip:
        print("[pre-push] skipped by EQ_SKIP_PRE_PUSH.")
        return 0

    timeout = _timeout_seconds()
    if timeout:
        print(f"[pre-push] timeout enabled: {timeout}s per command")

    checks = [
        [sys.executable, "-m", "scripts.quality.local_quality_check", "--contracts", "--governance"],
        [sys.executable, "-m", "pytest"],
    ]

    for cmd in checks:
        try:
            if run_live(cmd, timeout=timeout) != 0:
                return 1
        except subprocess.TimeoutExpired:
            print(f"[pre-push] timeout: {' '.join(cmd)}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
