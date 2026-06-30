from __future__ import annotations

import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ADAPTER_SCHEMA_VERSION = "automix-plugin-adapter-v1"

PLUGIN_FORMAT_PREFIX_RE = re.compile(r"^\s*(?:VST3?|AU|AUi|JS|CLAP|DX|LV2)\s*:\s*", re.IGNORECASE)

PITCH_CONTROLS = [
    "correction_amount",
    "amount",
    "speed",
    "depth",
    "formant_preserve",
    "humanize",
    "vibrato_preserve",
    "dry_wet",
    "output_gain",
]

EQ_CONTROLS = [
    "low_cut_hz",
    "high_cut_hz",
    "low_cut_slope",
    "band",
    "frequency_hz",
    "gain_db",
    "q",
    "clean_eq_amount",
    "dynamic_eq_amount",
    "mud_dynamic_cut_amount",
    "nasal_dynamic_cut_amount",
    "harshness_guard_amount",
    "harshness_dynamic_cut_amount",
    "high_fizz_control_amount",
    "presence_duck_amount_db",
    "low_mid_duck_amount_db",
    "sibilance_conflict_duck_db",
]

DYNAMICS_CONTROLS = [
    "threshold_db",
    "ratio",
    "attack_ms",
    "release_ms",
    "duck_attack_ms",
    "duck_release_ms",
    "duck_ratio",
    "bus_compressor_gain_reduction_db",
    "bus_compressor_attack_ms",
    "bus_compressor_release_ms",
    "instrumental_duck_amount_db",
    "backing_duck_amount_db",
    "send_duck_amount_db",
    "send_duck_release_ms",
    "deesser_amount",
    "sibilance_control_amount",
    "max_reduction_db",
]

SATURATION_CONTROLS = [
    "drive",
    "saturation_amount",
    "harmonic_amount",
    "clipper_drive_db",
    "mix",
    "output_trim_db",
]

REVERB_DELAY_CONTROLS = [
    "wet",
    "dry_wet",
    "decay",
    "decay_ms",
    "pre_delay_ms",
    "feedback",
    "delay_time_ms",
    "low_cut_hz",
    "high_cut_hz",
]

LIMITER_CLIPPER_CONTROLS = [
    "limiter_ceiling_dbTP",
    "limiter_max_gain_db",
    "limiter_release_ms",
    "target_lufs",
    "ceiling_dbTP",
    "true_peak_enable",
]

MS_STEREO_CONTROLS = [
    "low_end_mono_hz",
    "ms_mid_eq_amount",
    "ms_side_gain_db",
    "ms_mid_cleanup_amount",
    "ms_side_cleanup_amount",
    "side_gain_db",
    "side_noise_reduction_amount",
    "stereo_width_change",
]

UTILITY_CONTROLS = [
    "input_trim_db",
    "output_gain_db",
    "vocal_gain_db",
    "max_vocal_gain_db",
    "gain_db",
    "polarity",
    "bypass",
]

SEMANTIC_CONTROL_CATEGORIES: dict[str, str] = {}
for _category, _controls in {
    "pitch": PITCH_CONTROLS,
    "eq": EQ_CONTROLS,
    "dynamics": DYNAMICS_CONTROLS,
    "saturation": SATURATION_CONTROLS,
    "reverb_delay": REVERB_DELAY_CONTROLS,
    "limiter_clipper": LIMITER_CLIPPER_CONTROLS,
    "ms_stereo": MS_STEREO_CONTROLS,
    "utility": UTILITY_CONTROLS,
}.items():
    for _control in _controls:
        SEMANTIC_CONTROL_CATEGORIES.setdefault(_control, _category)

REQUIRED_CONTROL_FIELDS = {
    "semantic",
    "category",
    "target_name",
    "confidence",
    "write_allowed",
    "safe_min",
    "safe_max",
    "validated",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_plugin_name(name: str | None) -> str:
    value = PLUGIN_FORMAT_PREFIX_RE.sub("", str(name or "")).strip()
    value = re.sub(r"\s+", " ", value)
    return value


def compact_plugin_name(name: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_plugin_name(name).lower())


def slugify(name: str | None) -> str:
    value = normalize_plugin_name(name)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-").lower()
    slug = re.sub(r"_+", "_", slug)
    return slug or "unknown_plugin"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def clamp(value: Any, low: float, high: float) -> float:
    val = safe_float(value, low)
    return max(low, min(high, val))


def safe_range_for_semantic(semantic: str) -> tuple[float, float, float]:
    if semantic.endswith("_dbTP"):
        return -24.0, 0.0, -1.0
    if semantic.endswith("_db") or semantic in {"gain_db", "output_gain", "output_trim_db", "side_gain_db"}:
        return -24.0, 24.0, 0.0
    if semantic.endswith("_hz") or semantic in {"frequency_hz", "low_end_mono_hz"}:
        return 20.0, 20000.0, 1000.0
    if semantic.endswith("_ms") or semantic in {"decay_ms", "delay_time_ms"}:
        return 0.1, 5000.0, 100.0
    if semantic in {"ratio", "duck_ratio"}:
        return 1.0, 20.0, 1.0
    if semantic in {"band"}:
        return 0.0, 1.0, 0.0
    if semantic in {"bypass", "polarity", "true_peak_enable"}:
        return 0.0, 1.0, 0.0
    return 0.0, 1.0, 0.0


def default_semantic_control(
    semantic: str,
    *,
    target_name: str | None = None,
    parameter_index: int | None = None,
    confidence: float = 0.0,
    write_allowed: bool = False,
    validated: bool = False,
    safe_min: float | None = None,
    safe_max: float | None = None,
    default: float | None = None,
    validation_notes: str = "not validated",
) -> dict[str, Any]:
    low, high, default_value = safe_range_for_semantic(semantic)
    if safe_min is not None:
        low = float(safe_min)
    if safe_max is not None:
        high = float(safe_max)
    if default is not None:
        default_value = float(default)
    if low > high:
        low, high = high, low
    conf = clamp(confidence, 0.0, 1.0)
    return {
        "semantic": semantic,
        "category": SEMANTIC_CONTROL_CATEGORIES.get(semantic, "unknown"),
        "target_name": target_name,
        "parameter_index": parameter_index,
        "normalization": "plugin_native_or_normalized",
        "safe_min": low,
        "safe_max": high,
        "default": clamp(default_value, low, high),
        "confidence": conf,
        "write_allowed": bool(write_allowed and validated and conf >= 0.85),
        "writable": bool(write_allowed and validated and conf >= 0.85),
        "validated": bool(validated),
        "validation_notes": validation_notes,
    }


def create_adapter(
    *,
    adapter_id: str | None = None,
    plugin_name_patterns: list[str] | None = None,
    plugin_type: str = "unknown",
    manufacturer: str = "unknown",
    version: str = "unknown",
    platform: str | None = None,
    semantic_controls: dict[str, dict[str, Any]] | None = None,
    confidence: float = 0.0,
    safe_for_automix: bool = False,
    warnings: list[str] | None = None,
    source: str = "manual_or_generated",
) -> dict[str, Any]:
    patterns = plugin_name_patterns or [adapter_id or "unknown plugin"]
    aid = adapter_id or slugify(patterns[0])
    controls = semantic_controls or {}
    normalized_controls: dict[str, dict[str, Any]] = {}
    for semantic, control in controls.items():
        merged = default_semantic_control(semantic)
        merged.update(control or {})
        merged["semantic"] = semantic
        merged["category"] = merged.get("category") or SEMANTIC_CONTROL_CATEGORIES.get(semantic, "unknown")
        merged["confidence"] = clamp(merged.get("confidence", 0.0), 0.0, 1.0)
        merged["safe_min"] = safe_float(merged.get("safe_min"), 0.0)
        merged["safe_max"] = safe_float(merged.get("safe_max"), 1.0)
        if merged["safe_min"] > merged["safe_max"]:
            merged["safe_min"], merged["safe_max"] = merged["safe_max"], merged["safe_min"]
        merged["validated"] = bool(merged.get("validated", False))
        merged["write_allowed"] = bool(merged.get("write_allowed", False) and merged["validated"] and merged["confidence"] >= 0.85)
        merged["writable"] = merged["write_allowed"]
        normalized_controls[semantic] = merged

    adapter_confidence = clamp(confidence, 0.0, 1.0)
    has_validated_controls = any(control.get("write_allowed") and control.get("validated") for control in normalized_controls.values())
    return {
        "schema": ADAPTER_SCHEMA_VERSION,
        "adapter_id": aid,
        "plugin_name_patterns": patterns,
        "normalized_plugin_name_patterns": [compact_plugin_name(p) for p in patterns],
        "plugin_type": plugin_type,
        "manufacturer": manufacturer,
        "version": version,
        "platform": platform or sys.platform,
        "source": source,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "confidence": adapter_confidence,
        "safe_for_automix": bool(safe_for_automix and adapter_confidence >= 0.85 and has_validated_controls),
        "semantic_controls": normalized_controls,
        "unknown_parameters": [],
        "do_not_touch_parameters": [],
        "validation": {
            "status": "not_validated",
            "last_validated_at": None,
            "validated_by": None,
            "notes": "Adapter cannot write parameters until validation passes.",
        },
        "safety": {
            "no_fixed_parameter_indexes_required": True,
            "unknown_parameters_are_skipped": True,
            "requires_semantic_control_confidence": True,
            "requires_validation_before_write": True,
        },
        "warnings": warnings or [],
    }


def validate_adapter_schema(adapter: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if adapter.get("schema") != ADAPTER_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if not adapter.get("adapter_id"):
        errors.append("missing_adapter_id")
    if not isinstance(adapter.get("plugin_name_patterns"), list) or not adapter.get("plugin_name_patterns"):
        errors.append("missing_plugin_name_patterns")
    controls = adapter.get("semantic_controls")
    if not isinstance(controls, dict):
        errors.append("semantic_controls_not_mapping")
        return errors
    for semantic, control in controls.items():
        if not isinstance(control, dict):
            errors.append(f"{semantic}:control_not_mapping")
            continue
        missing = REQUIRED_CONTROL_FIELDS - set(control)
        for key in sorted(missing):
            errors.append(f"{semantic}:missing_{key}")
        conf = safe_float(control.get("confidence"), -1.0)
        if not 0.0 <= conf <= 1.0:
            errors.append(f"{semantic}:confidence_out_of_range")
        low = safe_float(control.get("safe_min"), 0.0)
        high = safe_float(control.get("safe_max"), 1.0)
        if low > high:
            errors.append(f"{semantic}:safe_range_reversed")
        if control.get("write_allowed") and (conf < 0.85 or not control.get("validated", False)):
            errors.append(f"{semantic}:write_allowed_without_validation")
    if adapter.get("safe_for_automix") and adapter.get("validation", {}).get("status") != "passed":
        errors.append("safe_for_automix_without_passed_validation")
    return errors


def control_is_write_safe(control: dict[str, Any], min_confidence: float = 0.85) -> bool:
    return bool(
        control
        and control.get("write_allowed", False)
        and control.get("validated", False)
        and safe_float(control.get("confidence"), 0.0) >= min_confidence
    )


def clamp_semantic_value(adapter: dict[str, Any], semantic: str, value: Any) -> dict[str, Any]:
    controls = adapter.get("semantic_controls", {}) if isinstance(adapter, dict) else {}
    control = controls.get(semantic)
    if not isinstance(control, dict):
        return {
            "allowed": False,
            "semantic": semantic,
            "input_value": value,
            "clamped_value": None,
            "reason": "UNKNOWN_PLUGIN_PARAMETER",
        }
    low = safe_float(control.get("safe_min"), 0.0)
    high = safe_float(control.get("safe_max"), 1.0)
    return {
        "allowed": True,
        "semantic": semantic,
        "target_name": control.get("target_name"),
        "input_value": value,
        "clamped_value": clamp(value, low, high),
        "safe_min": low,
        "safe_max": high,
        "confidence": safe_float(control.get("confidence"), 0.0),
    }


def adapter_matches_plugin(adapter: dict[str, Any], plugin_name: str) -> bool:
    needle = compact_plugin_name(plugin_name)
    patterns = adapter.get("normalized_plugin_name_patterns") or [
        compact_plugin_name(p) for p in adapter.get("plugin_name_patterns", [])
    ]
    return any(pattern and (pattern in needle or needle in pattern) for pattern in patterns)


def write_json(path: Path, data: Any) -> Path:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path
