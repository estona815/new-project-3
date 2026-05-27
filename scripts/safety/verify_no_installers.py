#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

INSTALLER_EXTENSIONS = {
    ".dmg", ".pkg", ".mpkg", ".exe", ".msi", ".zip", ".7z", ".rar",
    ".vst", ".vst3", ".component", ".aaxplugin", ".clap",
}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__"}


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    offenders: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
            continue
        if path.suffix.lower() in INSTALLER_EXTENSIONS:
            offenders.append(path.relative_to(root))
    if offenders:
        print("[fail] Installers, archives, or plugin binaries are not allowed:")
        for item in offenders:
            print(f"- {item}")
        return 1
    print("[ok] No installers, archives, or plugin binaries found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

