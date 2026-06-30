from __future__ import annotations

from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import clamp_semantic_value, control_is_write_safe, now_utc, slugify, write_json


PRESET_SAFETY_VERSION = "automix-generated-preset-safety-v1"

ALLOWED_PRESET_TYPES = {
    "stock_fallback",
    "detected_but_unvalidated",
    "safe_draft",
    "manual_review",
    "do_not_autoload",
}


def generate_safe_preset(
    *,
    plugin_name: str,
    adapter: dict[str, Any],
    preset_type: str,
    semantic_controls: dict[str, Any],
    workflow_stage: str,
    output_dir: Path,
    min_confidence: float = 0.85,
) -> dict[str, Any]:
    if preset_type not in ALLOWED_PRESET_TYPES:
        preset_type = "manual_review"

    controls = adapter.get("semantic_controls", {}) if isinstance(adapter, dict) else {}
    values: dict[str, Any] = {}
    skipped: dict[str, Any] = {}
    for semantic, value in semantic_controls.items():
        control = controls.get(semantic)
        if not isinstance(control, dict):
            skipped[semantic] = {"value": value, "reason": "UNKNOWN_PLUGIN_PARAMETER"}
            continue
        if not control_is_write_safe(control, min_confidence):
            skipped[semantic] = {"value": value, "reason": "SEMANTIC_CONTROL_NOT_WRITE_ALLOWED"}
            continue
        values[semantic] = clamp_semantic_value(adapter, semantic, value)["clamped_value"]

    preset = {
        "schema": PRESET_SAFETY_VERSION,
        "created_at": now_utc(),
        "plugin_name": plugin_name,
        "adapter_id": adapter.get("adapter_id") if isinstance(adapter, dict) else None,
        "preset_type": preset_type,
        "workflow_stage": workflow_stage,
        "generated_only": True,
        "user_preset_overwrite_allowed": False,
        "autoload_allowed": preset_type == "safe_draft" and bool(values) and not skipped,
        "semantic_values": values,
        "skipped_controls": skipped,
        "notes": [
            "Generated under automix/plugins/generated_presets only.",
            "Do not copy into user preset folders or autoload unless a later REAPER validation pass approves it.",
        ],
    }
    path = output_dir / "plugins" / "generated_presets" / f"{slugify(plugin_name)}_{slugify(workflow_stage)}_{slugify(preset_type)}.json"
    write_json(path, preset)
    preset["path"] = str(path)
    return preset
