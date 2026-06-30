from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FACTORY_PRESETS_PATH = ROOT / "presets" / "factory_presets_safe_defaults.json"
RELEASE_POLICY_PATH = ROOT / "presets" / "release_candidate_policy.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_factory_presets(path: Path = FACTORY_PRESETS_PATH) -> dict[str, Any]:
    return load_json(path)


def load_release_policy(path: Path = RELEASE_POLICY_PATH) -> dict[str, Any]:
    return load_json(path)


def preset_by_name(policy: dict[str, Any], name: str) -> dict[str, Any]:
    for preset in policy.get("presets", []):
        if preset.get("name") == name:
            return preset
    raise KeyError(f"unknown preset: {name}")


def parameter_definitions(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        key: value
        for key, value in policy.get("parameter_definitions", {}).items()
        if key.startswith("slider")
    }


def fresh_default_values(policy: dict[str, Any]) -> dict[str, float]:
    default_name = policy["default_preset"]
    return dict(preset_by_name(policy, default_name)["jsfx_sliders"])


def _as_float(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if math.isfinite(number) else fallback


def clamp_value(value: Any, definition: dict[str, Any]) -> float:
    fallback = float(definition["default"])
    number = _as_float(value, fallback)
    return max(float(definition["min"]), min(float(definition["max"]), number))


def sanitize_preset_values(values: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, float]:
    """Apply Prompt 8 legacy-preset behavior.

    Missing parameters use safe defaults, invalid values are finite-clamped, and
    old slider values remain loadable when they stay inside the absolute range.
    """
    policy = policy or load_factory_presets()
    clean: dict[str, float] = {}
    for key, definition in parameter_definitions(policy).items():
        clean[key] = clamp_value(values.get(key, definition["default"]), definition)
    return clean


def validate_factory_presets(policy: dict[str, Any] | None = None) -> list[str]:
    policy = policy or load_factory_presets()
    errors: list[str] = []
    definitions = parameter_definitions(policy)
    default_preset = policy.get("default_preset")

    if default_preset != "Preserve":
        errors.append("fresh default preset must be Preserve")

    preset_names = [preset.get("name") for preset in policy.get("presets", [])]
    if len(preset_names) != len(set(preset_names)):
        errors.append("preset names must be unique")
    if "Strong Test / Repair" == default_preset:
        errors.append("Strong Test / Repair cannot be the fresh default")

    for preset in policy.get("presets", []):
        name = str(preset.get("name", ""))
        sliders = preset.get("jsfx_sliders", {})
        missing = sorted(set(definitions) - set(sliders))
        extra = sorted(set(sliders) - set(definitions))
        if missing:
            errors.append(f"{name}: missing sliders {', '.join(missing)}")
        if extra:
            errors.append(f"{name}: unknown sliders {', '.join(extra)}")
        for key, definition in definitions.items():
            if key not in sliders:
                continue
            original = sliders[key]
            clamped = clamp_value(original, definition)
            try:
                number = float(original)
            except (TypeError, ValueError):
                errors.append(f"{name}: {key} is not numeric")
                continue
            if not math.isfinite(number):
                errors.append(f"{name}: {key} is not finite")
            elif clamped != number:
                errors.append(f"{name}: {key}={number} outside range {definition['min']}..{definition['max']}")
        if preset.get("strong_mode") and preset.get("release_default_allowed"):
            errors.append(f"{name}: strong preset cannot be release default")
        if name == default_preset and preset.get("strong_mode"):
            errors.append(f"{name}: default preset cannot be strong")

    return errors
