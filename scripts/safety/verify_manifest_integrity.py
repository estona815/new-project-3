#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REQUIRED_KEYS = {
    "name", "group", "category", "priority", "role", "primary_use", "chain_role",
    "install_on_public_pc", "install_on_main_computer", "risk", "fallback",
    "public_pc_allowed", "main_computer_install", "requires_login", "default_enabled", "notes",
}


def parse_plugin_entries(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- id:"):
            if current:
                entries.append(current)
            current = {"id": line.split(":", 1)[1].strip()}
            continue
        if current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.strip()] = value.strip().strip('"')
    if current:
        entries.append(current)
    return entries


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    free_manifest = root / "plugin_registry" / "free_plugin_manifest.yml"
    matrix = root / "plugin_registry" / "plugin_capability_matrix.yml"
    if not free_manifest.exists():
        print("[fail] Missing plugin_registry/free_plugin_manifest.yml")
        return 1
    if not matrix.exists():
        print("[fail] Missing plugin_registry/plugin_capability_matrix.yml")
        return 1
    entries = parse_plugin_entries(matrix.read_text(encoding="utf-8"))
    if not entries:
        print("[fail] No plugin entries found in capability matrix.")
        return 1
    failed = False
    for entry in entries:
        missing = sorted(REQUIRED_KEYS - set(entry))
        if missing:
            failed = True
            print(f"[fail] {entry.get('id', '<unknown>')} missing keys: {', '.join(missing)}")
    if failed:
        return 1
    print(f"[ok] Plugin manifest integrity verified for {len(entries)} entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

