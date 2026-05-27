#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi"}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__"}


def is_allowed_doc_screenshot(path: Path) -> bool:
    parts = tuple(part.lower() for part in path.parts)
    return "docs" in parts and "screenshots" in parts


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    offenders: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
            continue
        if path.suffix.lower() in VIDEO_EXTENSIONS and not is_allowed_doc_screenshot(path):
            offenders.append(path.relative_to(root))
    if offenders:
        print("[fail] Video files are not allowed outside docs/screenshots:")
        for item in offenders:
            print(f"- {item}")
        return 1
    print("[ok] No blocked video files found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

