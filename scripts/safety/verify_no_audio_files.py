#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".aiff", ".aif", ".m4a", ".ogg"}
SPECIAL_SUFFIXES = (".stem.mp4",)
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__"}


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    offenders: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
            continue
        lower = path.name.lower()
        if path.suffix.lower() in AUDIO_EXTENSIONS or lower.endswith(SPECIAL_SUFFIXES):
            offenders.append(path.relative_to(root))
    if offenders:
        print("[fail] Audio files are not allowed:")
        for item in offenders:
            print(f"- {item}")
        return 1
    print("[ok] No blocked audio files found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

