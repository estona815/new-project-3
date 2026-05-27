#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__"}
SKIP_SUFFIXES = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}
PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
    re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
]


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    findings: list[str] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in PATTERNS:
            if pattern.search(text):
                findings.append(str(path.relative_to(root)))
                break
    if findings:
        print("[fail] Potential secrets found:")
        for item in findings:
            print(f"- {item}")
        return 1
    print("[ok] No obvious secrets found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

