#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys
import locale
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.quality.local_quality_check import UNIX_ABS_RE, WINDOWS_ABS_RE

PATH_SCAN_EXTS = {".py", ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".ps1"}
TODO_RE = re.compile(r"\b(TODO|FIXME|HACK)\b", re.IGNORECASE)
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36}\b"), "GitHub PAT"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "OpenAI key-like token"),
    (
        re.compile(
            r"(?i)\b(?:api[_-]?key|token|secret|password|passwd)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"
        ),
        "generic secret assignment",
    ),
]

CONTRACT_SENSITIVE_PREFIXES = (
    "Governance/steering/",
    "Governance/SpiralRoadmap/planA/",
)
CONTRACT_SENSITIVE_FILES = {
    "AGENTS.md",
    "docs/system-overview.md",
    "docs/module-index.md",
    "docs/naming-conventions.md",
    "docs/naming-contracts.schema.json",
    "docs/naming-contracts-glossary.md",
}


def _decode_output(payload: bytes | str | None) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload

    candidates = [
        "utf-8",
        locale.getpreferredencoding(False),
        "gbk",
    ]
    tried: set[str] = set()
    for encoding in candidates:
        normalized = (encoding or "").strip()
        if not normalized or normalized in tried:
            continue
        tried.add(normalized)
        try:
            return payload.decode(normalized)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def run_cmd(args: list[str], capture: bool = True) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        capture_output=capture,
        text=False,
        check=False,
    )
    if capture:
        return proc.returncode, _decode_output(proc.stdout).strip()
    return proc.returncode, ""


def get_staged_files() -> list[str]:
    rc, output = run_cmd(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    if rc != 0:
        print("[pre-commit] unable to read staged files")
        return []
    files = [line.strip().replace(chr(92), "/") for line in output.splitlines() if line.strip()]
    return files


def get_added_lines(path: str) -> list[tuple[int, str]]:
    rc, diff = run_cmd(["git", "diff", "--cached", "--unified=0", "--", path])
    if rc != 0:
        return []

    result: list[tuple[int, str]] = []
    current_line: int | None = None
    for raw in diff.splitlines():
        if raw.startswith("@@"):
            match = HUNK_RE.match(raw)
            current_line = int(match.group(1)) if match else None
            continue
        if current_line is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            result.append((current_line, raw[1:]))
            current_line += 1
            continue
        if raw.startswith("-") and not raw.startswith("---"):
            continue
        if raw.startswith(" "):
            current_line += 1
    return result


def is_path_scan_target(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    if suffix not in PATH_SCAN_EXTS:
        return False
    if path.startswith("tests/"):
        return False
    return True


def needs_contract_check(staged_files: list[str]) -> bool:
    for path in staged_files:
        if path in CONTRACT_SENSITIVE_FILES:
            return True
        for prefix in CONTRACT_SENSITIVE_PREFIXES:
            if path.startswith(prefix):
                return True
    return False


def run_local_scan() -> int:
    print("[pre-commit] running local quality scan: --scan")
    return subprocess.call(
        [sys.executable, "-m", "scripts.quality.local_quality_check", "--scan"],
        cwd=PROJECT_ROOT,
    )


def run_contract_checks() -> int:
    print("[pre-commit] running contract/governance checks")
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "scripts.quality.local_quality_check",
            "--contracts",
            "--governance",
        ],
        cwd=PROJECT_ROOT,
    )


def main() -> int:
    staged_files = get_staged_files()
    if not staged_files:
        print("[pre-commit] no staged files, skip.")
        return 0

    path_hits: list[tuple[str, int, str]] = []
    secret_hits: list[tuple[str, int, str, str]] = []
    todo_hits: list[tuple[str, int, str]] = []

    for path in staged_files:
        for lineno, line in get_added_lines(path):
            if is_path_scan_target(path) and (WINDOWS_ABS_RE.search(line) or UNIX_ABS_RE.search(line)):
                path_hits.append((path, lineno, line.strip()))
            for pattern, label in SECRET_PATTERNS:
                if pattern.search(line):
                    secret_hits.append((path, lineno, label, line.strip()))
            if TODO_RE.search(line):
                todo_hits.append((path, lineno, line.strip()))

    failed = False
    if path_hits:
        failed = True
        print("[pre-commit] hardcoded absolute path detected in staged changes:")
        for path, lineno, line in path_hits:
            print(f"  - {path}:{lineno}: {line}")

    if secret_hits:
        failed = True
        print("[pre-commit] secret-like content detected in staged changes:")
        for path, lineno, label, line in secret_hits:
            print(f"  - {path}:{lineno} ({label}): {line}")

    has_debt_update = "Governance/record/debts.md" in staged_files
    allow_todo = os.environ.get("EQ_ALLOW_TODO", "").lower() in {"1", "true", "yes"}
    if todo_hits and not has_debt_update and not allow_todo:
        failed = True
        print("[pre-commit] TODO/HACK/FIXME detected but Governance/record/debts.md not staged:")
        for path, lineno, line in todo_hits:
            print(f"  - {path}:{lineno}: {line}")
        print("[pre-commit] add debt record or set EQ_ALLOW_TODO=1 to bypass this check.")

    if run_local_scan() != 0:
        failed = True

    if needs_contract_check(staged_files):
        if run_contract_checks() != 0:
            failed = True
    else:
        print("[pre-commit] contract/governance checks skipped (no contract-sensitive changes).")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
