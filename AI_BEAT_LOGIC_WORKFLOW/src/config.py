from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paths import PROJECT_ROOT


DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "defaults.json"


def load_defaults(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Default config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        defaults = json.load(config_file)

    required_keys = {
        "length_mode",
        "vocal_mode",
        "melody_focus",
        "drum_808",
        "export_format",
        "save_logic_project",
    }
    missing_keys = sorted(required_keys - defaults.keys())
    if missing_keys:
        joined = ", ".join(missing_keys)
        raise ValueError(f"Default config is missing required keys: {joined}")

    return defaults

