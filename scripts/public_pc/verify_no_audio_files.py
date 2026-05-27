#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

AUDIO_EXTENSIONS = {
    ".wav", ".wave", ".mp3", ".m4a", ".aac", ".flac", ".aif", ".aiff",
    ".ogg", ".opus", ".mp4", ".mov", ".mkv", ".avi",
}

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__"}


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    offenders: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            offenders.append(path.relative_to(root))
    if offenders:
        print("[fail] Audio/video files found:")
        for item in offenders:
            print(f"- {item}")
        return 1
    print("[ok] No audio/video files found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

