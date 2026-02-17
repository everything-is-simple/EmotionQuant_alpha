#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_PATTERN = re.compile(r"\b(?:spiral-s\d+[a-z]?|CP-\d{2})\b", re.IGNORECASE)
ALLOW_PREFIXES = ("Merge ", "Revert ", "fixup! ", "squash! ")


def extract_subject(message_path: Path) -> str:
    text = message_path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        if line.strip() and not line.startswith("#"):
            return line.strip()
    return ""


def main() -> int:
    if len(sys.argv) != 2:
        print("[commit-msg] usage: commit_msg.py <commit_message_file>")
        return 2

    message_path = Path(sys.argv[1])
    if not message_path.exists():
        print(f"[commit-msg] file not found: {message_path}")
        return 2

    subject = extract_subject(message_path)
    if not subject:
        print("[commit-msg] empty commit message.")
        return 1

    if any(subject.startswith(prefix) for prefix in ALLOW_PREFIXES):
        return 0

    if REQUIRED_PATTERN.search(subject):
        return 0

    print("[commit-msg] commit message must include spiral id or CP id.")
    print("[commit-msg] required pattern: spiral-s{N} or CP-xx")
    print("[commit-msg] examples:")
    print("  - feat(spiral-s2c): bridge validation weight plan")
    print("  - docs(CP-05): sync integration contract notes")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
