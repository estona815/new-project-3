from __future__ import annotations

from copy import deepcopy
from typing import Any

from automix.plugins.adapter_confidence_gate import evaluate_adapter_confidence


MIN_MAPPING_CONFIDENCE = 0.85

PROFILES: dict[str, dict[str, Any]] = {
    "minimal_vocal_gain_trim": {
        "vocal_gain_db": 0.8,
        "max_vocal_gain_db": 1.5,
        "instrumental_duck_amount_db": 0.0,
        "presence_duck_amount_db": 0.0,
        "low_mid_duck_amount_db": 0.0,
        "sibilance_conflict_duck_db": 0.0,
        "ms_mid_cleanup_amount": 0.0,
        "send_duck_amount_db": 0.0,
    },
    "dynamic_space_creation": {
        "vocal_gain_db": 0.3,
        "max_vocal_gain_db": 1.0,
        "instrumental_duck_amount_db": -0.8,
        "presence_duck_amount_db": -1.2,
        "low_mid_duck_amount_db": -0.7,
        "sibilance_conflict_duck_db": -0.5,
        "duck_attack_ms": 20,
        "duck_release_ms": 180,
        "duck_ratio": 1.4,
        "ms_mid_cleanup_amount": 0.12,
        "ms_side_cleanup_amount": 0.08,
        "send_duck_amount_db": -1.0,
        "send_duck_release_ms": 350,
        "output_gain_db": 0.0,
    },
    "lead_vocal_forward_clear": {
        "vocal_gain_db": 0.5,
        "max_vocal_gain_db": 1.2,
        "instrumental_duck_amount_db": -1.2,
        "presence_duck_amount_db": -1.5,
        "low_mid_duck_amount_db": -0.8,
        "sibilance_conflict_duck_db": -0.6,
        "duck_attack_ms": 15,
        "duck_release_ms": 160,
        "duck_ratio": 1.6,
        "ms_mid_cleanup_amount": 0.15,
        "send_duck_amount_db": -1.2,
        "output_gain_db": 0.0,
    },
    "fragile_ai_vocal_protect": {
        "vocal_gain_db": 0.0,
        "max_vocal_gain_db": 0.5,
        "instrumental_duck_amount_db": -0.6,
        "presence_duck_amount_db": -0.8,
        "low_mid_duck_amount_db": -0.5,
        "sibilance_conflict_duck_db": -0.4,
        "duck_attack_ms": 30,
        "duck_release_ms": 220,
        "duck_ratio": 1.2,
        "ms_mid_cleanup_amount": 0.08,
        "ms_side_cleanup_amount": 0.05,
        "send_duck_amount_db": -0.8,
        "output_gain_db": 0.0,
    },
    "backing_vocal_duck_under_lead": {
        "backing_duck_amount_db": -1.5,
        "duck_attack_ms": 20,
        "duck_release_ms": 250,
        "presence_duck_amount_db": -0.7,
        "sibilance_conflict_duck_db": -0.5,
        "stereo_width_change": 0.0,
        "output_gain_db": 0.0,
    },
    "skip_placement": {
        "apply": False,
    },
}

PROFILE_FOR_ACTION = {
    "skip_placement": "skip_placement",
    "minimal_vocal_gain_trim": "minimal_vocal_gain_trim",
    "dynamic_space_creation_draft": "dynamic_space_creation",
    "sidechain_dynamic_eq_draft": "lead_vocal_forward_clear",
    "ms_center_cleanup_draft": "dynamic_space_creation",
    "send_cleanup_draft": "dynamic_space_creation",
    "manual_mix_required": "skip_placement",
    "stem_required": "skip_placement",
}

CHAIN_ORDER = {
    "minimal_vocal_gain_trim": [
        ("lead_vocal", "utility_gain"),
        ("lead_vocal", "vocal_bus_trim"),
        ("lead_vocal", "output_gain"),
    ],
    "dynamic_space_creation": [
        ("lead_vocal", "utility_gain"),
        ("instrumental_bus", "sidechain_dynamic_eq"),
        ("instrumental_bus", "multiband_ducker"),
        ("instrumental_bus", "ms_eq"),
        ("backing_vocals", "backing_vocal_ducker"),
        ("send_tracks", "send_ducker"),
        ("send_tracks", "reverb_tail_ducker"),
        ("lead_vocal", "output_gain"),
    ],
    "lead_vocal_forward_clear": [
        ("lead_vocal", "utility_gain"),
        ("instrumental_bus", "sidechain_dynamic_eq"),
        ("instrumental_bus", "multiband_ducker"),
        ("backing_vocals", "backing_vocal_ducker"),
        ("send_tracks", "send_ducker"),
        ("lead_vocal", "output_gain"),
    ],
    "fragile_ai_vocal_protect": [
        ("instrumental_bus", "sidechain_dynamic_eq"),
        ("instrumental_bus", "ms_eq"),
        ("backing_vocals", "backing_vocal_ducker"),
        ("send_tracks", "send_ducker"),
        ("lead_vocal", "output_gain"),
    ],
    "backing_vocal_duck_under_lead": [
        ("backing_vocals", "backing_vocal_ducker"),
        ("backing_vocals", "output_gain"),
    ],
    "skip_placement": [],
}

CATEGORY_SETTINGS = {
    "utility_gain": ["vocal_gain_db", "max_vocal_gain_db"],
    "sidechain_dynamic_eq": ["presence_duck_amount_db", "low_mid_duck_amount_db", "sibilance_conflict_duck_db", "duck_attack_ms", "duck_release_ms", "duck_ratio"],
    "multiband_ducker": ["instrumental_duck_amount_db", "duck_attack_ms", "duck_release_ms", "duck_ratio"],
    "ms_eq": ["ms_mid_cleanup_amount", "ms_side_cleanup_amount"],
    "vocal_bus_trim": ["vocal_gain_db", "max_vocal_gain_db"],
    "backing_vocal_ducker": ["backing_duck_amount_db", "presence_duck_amount_db", "sibilance_conflict_duck_db", "duck_attack_ms", "duck_release_ms"],
    "send_ducker": ["send_duck_amount_db", "send_duck_release_ms"],
    "reverb_tail_ducker": ["send_duck_amount_db", "send_duck_release_ms"],
    "delay_ducker": ["send_duck_amount_db", "send_duck_release_ms"],
    "output_gain": ["output_gain_db"],
    "loudness_matcher": [],
    "phase_correlation_meter": [],
}

STOCK_FALLBACKS = {
    "utility_gain": "REAPER track gain or JS utility",
    "sidechain_dynamic_eq": "ReaEQ/ReaXcomp with sidechain if mapped",
    "multiband_ducker": "ReaXcomp sidechain draft",
    "ms_eq": "JS M/S utility if mapped",
    "vocal_bus_trim": "REAPER track gain or JS utility",
    "backing_vocal_ducker": "ReaComp/ReaXcomp sidechain draft",
    "send_ducker": "ReaComp sidechain draft",
    "reverb_tail_ducker": "ReaComp sidechain draft",
    "delay_ducker": "ReaComp sidechain draft",
    "output_gain": "REAPER track gain or JS utility",
    "loudness_matcher": "offline analyzer only",
    "phase_correlation_meter": "REAPER meter or analyzer only",
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def clamp_db(value: float, low: float = -3.0, high: float = 1.5) -> float:
    return max(low, min(high, float(value)))


def profile_name_for_action(action: str, analysis: dict[str, Any]) -> str:
    if analysis.get("role") in {"backing_vocal", "vocal_double", "adlib"}:
        return "backing_vocal_duck_under_lead"
    source = analysis.get("source_classification")
    recovery_status = analysis.get("recovery_status")
    warnings = " ".join(analysis.get("warnings", [])).lower()
    if source in {"ai_vocal_stem", "source_separated_vocal"} or recovery_status in {"failed_recovery", "missing_renders"} or "artifact" in warnings:
        if action in {"dynamic_space_creation_draft", "sidechain_dynamic_eq_draft", "ms_center_cleanup_draft", "send_cleanup_draft"}:
            return "fragile_ai_vocal_protect"
    return PROFILE_FOR_ACTION.get(action, "skip_placement")


def resolve_placement_profile(action: str, analysis: dict[str, Any], adapter_status: dict[str, Any] | None = None) -> dict[str, Any]:
    profile_name = profile_name_for_action(action, analysis)
    settings = deepcopy(PROFILES[profile_name])
    warnings: list[str] = []
    if action in {"skip_placement", "manual_mix_required", "stem_required"}:
        profile_name = "skip_placement"
        settings = deepcopy(PROFILES["skip_placement"])

    presence = analysis.get("vocal_presence_profile", {})
    masking = analysis.get("masking_profile", {})
    spatial = analysis.get("spatial_profile", {})
    if presence.get("vocal_harshness_2k5_6k", 0.0) > 0.55:
        if "vocal_gain_db" in settings:
            settings["vocal_gain_db"] = min(float(settings["vocal_gain_db"]), 0.0)
        warnings.append("vocal harshness risk; vocal gain boost reduced")
    if spatial.get("stereo_width_change_risk", 0.0) > 0.55 or spatial.get("mono_compatibility_risk", 0.0) > 0.55:
        settings["ms_side_cleanup_amount"] = min(float(settings.get("ms_side_cleanup_amount", 0.0)), 0.05)
        settings["stereo_width_change"] = 0.0
        warnings.append("stereo risk; widening disabled")
    if masking.get("masking_120_350", 0.0) < 0.35 and "low_mid_duck_amount_db" in settings:
        settings["low_mid_duck_amount_db"] = max(float(settings["low_mid_duck_amount_db"]), -0.5)

    if "vocal_gain_db" in settings:
        max_gain = float(settings.get("max_vocal_gain_db", 1.0))
        settings["vocal_gain_db"] = min(float(settings["vocal_gain_db"]), max_gain)
    for key in ("instrumental_duck_amount_db", "presence_duck_amount_db", "low_mid_duck_amount_db", "sibilance_conflict_duck_db", "send_duck_amount_db", "backing_duck_amount_db"):
        if key in settings:
            settings[key] = clamp_db(settings[key], -2.0, 0.0)
    for key in ("ms_mid_cleanup_amount", "ms_side_cleanup_amount"):
        if key in settings:
            settings[key] = clamp(settings[key], 0.0, 0.20)

    written, skipped = mapped_semantic_controls(settings, adapter_status or {})
    return {
        "profile": profile_name,
        "settings": settings,
        "plugin_chain": build_plugin_chain(profile_name, settings, adapter_status or {}),
        "semantic_controls_to_write": written,
        "semantic_controls_skipped": skipped,
        "warnings": warnings,
    }


def mapped_semantic_controls(settings: dict[str, Any], adapter_status: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    controls = adapter_status.get("semantic_controls", {}) if isinstance(adapter_status, dict) else {}
    written: dict[str, Any] = {}
    skipped: dict[str, Any] = {}
    for semantic, value in settings.items():
        if semantic == "apply":
            continue
        mapping = controls.get(semantic, {})
        if isinstance(mapping, dict) and mapping.get("confidence", 0.0) >= MIN_MAPPING_CONFIDENCE and mapping.get("writable", True):
            written[semantic] = {
                "value": value,
                "target_name": mapping.get("target_name"),
                "mapping_confidence": mapping.get("confidence"),
            }
        else:
            skipped[semantic] = {"value": value, "reason": "missing or low-confidence semantic mapping"}
    return written, skipped


def build_plugin_chain(profile_name: str, settings: dict[str, Any], adapter_status: dict[str, Any]) -> list[dict[str, Any]]:
    plugins = adapter_status.get("plugins", {}) if isinstance(adapter_status, dict) else {}
    strict_gate = bool(adapter_status.get("strict_adapter_gate", False)) if isinstance(adapter_status, dict) else False
    chain = []
    for target, category in CHAIN_ORDER.get(profile_name, []):
        plugin_info = plugins.get(category, {}) if isinstance(plugins, dict) else {}
        confidence = float(plugin_info.get("adapter_confidence", plugin_info.get("confidence", 0.0))) if isinstance(plugin_info, dict) else 0.0
        plugin_name = plugin_info.get("plugin") if isinstance(plugin_info, dict) else None
        semantic_settings = {
            key: settings[key]
            for key in CATEGORY_SETTINGS.get(category, [])
            if key in settings
        }
        plugin_label = plugin_name or STOCK_FALLBACKS.get(category, "unmapped")
        gate = evaluate_adapter_confidence(
            desired_semantic_controls=semantic_settings,
            adapter=plugin_info.get("adapter") if isinstance(plugin_info, dict) else None,
            plugin_name=plugin_label,
            plugin_detected=plugin_name is not None,
            workflow_stage="vocal_placement",
            fallback=STOCK_FALLBACKS.get(category, "unmapped"),
        )
        legacy_safe = confidence >= MIN_MAPPING_CONFIDENCE
        chain.append(
            {
                "target_track": target,
                "category": category,
                "plugin": plugin_label,
                "semantic_settings": semantic_settings,
                "adapter_confidence": confidence,
                "safe_to_apply": bool(legacy_safe and (gate["allowed"] if strict_gate and semantic_settings else True)),
                "requires_parameter_discovery": bool(confidence < MIN_MAPPING_CONFIDENCE or (strict_gate and gate["fallback_required"])),
                "adapter_confidence_gate_enforced": True,
                "adapter_confidence_gate": gate,
            }
        )
    return chain
