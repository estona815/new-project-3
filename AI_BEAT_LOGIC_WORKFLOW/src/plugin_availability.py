from __future__ import annotations

from pathlib import Path
from typing import Any


AU_PLUGIN_DIRS = (
    Path("/Library/Audio/Plug-Ins/Components"),
    Path.home() / "Library" / "Audio" / "Plug-Ins" / "Components",
)


def check_au_plugin_availability(plugin_name: str) -> dict[str, Any]:
    normalized = plugin_name.lower()
    candidates: list[Path] = []
    for folder in AU_PLUGIN_DIRS:
        try:
            if folder.exists():
                candidates.extend(path for path in folder.glob("*.component") if normalized in path.name.lower())
        except OSError:
            continue
    return {
        "plugin": plugin_name,
        "format": "AudioUnit",
        "detected": bool(candidates),
        "paths": [str(path) for path in candidates],
        "check_method": "filesystem_component_scan",
        "safe_non_destructive": True,
    }


def decapitator_availability() -> dict[str, Any]:
    detected = check_au_plugin_availability("Decapitator")
    if detected["detected"]:
        status = "detected"
        note = "Soundtoys Decapitator Audio Unit appears installed; Logic insertion still requires manual or verified automation."
    else:
        status = "not_detected"
        note = "Soundtoys Decapitator was not detected by safe AU component scan."
    return {**detected, "canonical_name": "Soundtoys Decapitator", "status": status, "note": note}
