#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

BLOCKED_SUFFIXES = {".env", ".key", ".pem", ".lic", ".license", ".licensekey", ".token"}
BLOCKED_NAME_PARTS = ("license", "credential", "secret", "token")
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__"}
TEXT_SUFFIXES = {".md", ".py", ".ps1", ".sh", ".yml", ".yaml", ".json", ".lua", ".txt"}
PATTERNS = [
    re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"),
]


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    findings: list[str] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
            continue
        lower_name = path.name.lower()
        if path.suffix.lower() in BLOCKED_SUFFIXES or any(part in lower_name for part in BLOCKED_NAME_PARTS):
            if "verify_no_secrets.py" not in str(path):
                findings.append(f"blocked filename: {path.relative_to(root)}")
                continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in PATTERNS:
            if pattern.search(text):
                findings.append(f"pattern match: {path.relative_to(root)}")
                break
    if findings:
        print("[fail] Potential secrets/licenses found:")
        for item in findings:
            print(f"- {item}")
        return 1
    print("[ok] No obvious secrets or license files found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

