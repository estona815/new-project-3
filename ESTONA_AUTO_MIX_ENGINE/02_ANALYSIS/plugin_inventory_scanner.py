#!/usr/bin/env python3
"""Optional plugin inventory scanner.

This does not load paid plugins or make the pipeline depend on them. It only
records visible VST3/AU paths so future optional pedalboard experiments can
report what was available or missing.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from audio_utils import resolve_path, write_json


PLUGIN_DIRS = [
    "~/Library/Audio/Plug-Ins/VST3",
    "~/Library/Audio/Plug-Ins/Components",
    "/Library/Audio/Plug-Ins/VST3",
    "/Library/Audio/Plug-Ins/Components",
    "C:/Program Files/Common Files/VST3",
    "C:/Program Files/Common Files/Audio/Plug-Ins/VST3",
]


def scan_plugins() -> dict:
    items = []
    for raw in PLUGIN_DIRS:
        folder = Path(os.path.expanduser(raw))
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*")):
            if path.suffix.lower() in {".vst3", ".component"} or path.is_dir() and path.name.lower().endswith((".vst3", ".component")):
                items.append({
                    "path": str(path),
                    "name": path.name,
                    "format": "AU" if path.name.lower().endswith(".component") else "VST3",
                    "load_status": "not_loaded_inventory_only",
                })
    result = {
        "status": "ok",
        "policy": "Optional inventory only; no commercial plugin dependency and no automatic paid-plugin loading.",
        "pedalboard_optional": "spotify/pedalboard is GPL-3.0 in the audited repo, so direct integration requires license review.",
        "plugins": items,
    }
    write_json(resolve_path("06_OUTPUTS", "logs", "plugin_inventory.json"), result)
    return result


if __name__ == "__main__":
    print(f"plugin inventory entries: {len(scan_plugins().get('plugins', []))}")
