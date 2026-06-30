from __future__ import annotations

from copy import deepcopy
from typing import Any

from automix.plugins.adapter_confidence_gate import evaluate_adapter_confidence


MIN_MAPPING_CONFIDENCE = 0.85

PROFILES: dict[str, dict[str, Any]] = {
    "minimal_cleanup": {
        "utility_gain_db": 0.0,
        "low_cut_hz": 70,
        "low_cut_slope": "gentle",
        "mud_dynamic_cut_amount": 0.10,
        "harshness_dynamic_cut_amount": 0.10,
        "sibilance_control_amount": 0.10,
        "high_fizz_control_amount": 0.08,
        "side_noise_reduction_amount": 0.05,
        "compression_amount": 0.00,
        "saturation_amount": 0.00,
        "stereo_width_change": 0.00,
        "output_gain_db": 0.0,
    },
    "conservative_ai_vocal_cleanup": {
        "utility_gain_db": -1.0,
        "low_cut_hz": 80,
        "low_cut_slope": "gentle",
        "mud_dynamic_cut_amount": 0.18,
        "nasal_dynamic_cut_amount": 0.12,
        "harshness_dynamic_cut_amount": 0.22,
        "sibilance_control_amount": 0.18,
        "high_fizz_control_amount": 0.20,
        "side_noise_reduction_amount": 0.15,
        "formant_protection": 1.0,
        "transient_preserve": 0.85,
        "body_preserve": 0.80,
        "compression_amount": 0.00,
        "saturation_amount": 0.05,
        "stereo_width_change": -0.05,
        "output_gain_db": 0.0,
    },
    "source_separated_rescue": {
        "utility_gain_db": -1.5,
        "low_cut_hz": 90,
        "low_cut_slope": "gentle",
        "bleed_reduction_amount": 0.18,
        "watery_phase_control_amount": 0.22,
        "side_noise_reduction_amount": 0.25,
        "harshness_dynamic_cut_amount": 0.18,
        "sibilance_control_amount": 0.12,
        "high_fizz_control_amount": 0.16,
        "reverb_smear_control_amount": 0.20,
        "formant_protection": 1.0,
        "transient_preserve": 0.90,
        "body_preserve": 0.85,
        "compression_amount": 0.00,
        "saturation_amount": 0.00,
        "stereo_width_change": -0.10,
        "output_gain_db": 0.0,
    },
    "thin_vocal_body_preserve": {
        "utility_gain_db": -1.0,
        "low_cut_hz": 60,
        "low_cut_slope": "very_gentle",
        "mud_dynamic_cut_amount": 0.06,
        "harshness_dynamic_cut_amount": 0.16,
        "sibilance_control_amount": 0.14,
        "high_fizz_control_amount": 0.14,
        "body_preserve": 1.0,
        "body_recovery_amount": 0.08,
        "compression_amount": 0.00,
        "saturation_amount": 0.03,
        "stereo_width_change": 0.00,
        "output_gain_db": 0.0,
    },
    "skip_recovery": {
        "apply": False,
    },
}

PROFILE_FOR_ACTION = {
    "skip": "skip_recovery",
    "no_recovery_needed": "skip_recovery",
    "minimal_cleanup_draft": "minimal_cleanup",
    "conservative_ai_vocal_cleanup_draft": "conservative_ai_vocal_cleanup",
    "source_separated_rescue_draft": "source_separated_rescue",
    "stem_required": "skip_recovery",
    "manual_review_required": "skip_recovery",
    "unsafe_to_process": "skip_recovery",
}

CHAIN_ORDER = {
    "minimal_cleanup": [
        "utility_gain",
        "cleanup_eq",
        "dynamic_eq",
        "de_esser",
        "high_fizz_control",
        "side_cleanup",
        "output_gain",
    ],
    "conservative_ai_vocal_cleanup": [
        "utility_gain",
        "cleanup_eq",
        "dynamic_eq",
        "resonance_suppressor",
        "de_esser",
        "high_fizz_control",
        "side_cleanup",
        "optional_subtle_saturation",
        "output_gain",
    ],
    "source_separated_rescue": [
        "utility_gain",
        "side_cleanup",
        "phase_correlation_guard",
        "artifact_suppressor",
        "dynamic_eq",
        "resonance_suppressor",
        "de_esser",
        "high_fizz_control",
        "output_gain",
    ],
    "thin_vocal_body_preserve": [
        "utility_gain",
        "cleanup_eq",
        "dynamic_eq",
        "de_esser",
        "high_fizz_control",
        "artifact_suppressor",
        "output_gain",
    ],
    "skip_recovery": [],
}

CATEGORY_SETTINGS = {
    "utility_gain": ["utility_gain_db"],
    "cleanup_eq": ["low_cut_hz", "low_cut_slope", "mud_dynamic_cut_amount"],
    "dynamic_eq": ["mud_dynamic_cut_amount", "nasal_dynamic_cut_amount", "harshness_dynamic_cut_amount"],
    "resonance_suppressor": ["nasal_dynamic_cut_amount", "harshness_dynamic_cut_amount"],
    "de_esser": ["sibilance_control_amount"],
    "high_fizz_control": ["high_fizz_control_amount"],
    "side_cleanup": ["side_noise_reduction_amount", "stereo_width_change"],
    "phase_correlation_guard": ["watery_phase_control_amount", "stereo_width_change"],
    "artifact_suppressor": ["bleed_reduction_amount", "watery_phase_control_amount", "reverb_smear_control_amount", "body_recovery_amount"],
    "optional_subtle_saturation": ["saturation_amount"],
    "output_gain": ["output_gain_db"],
}

STOCK_FALLBACKS = {
    "utility_gain": "REAPER track gain or JS utility",
    "cleanup_eq": "ReaEQ",
    "dynamic_eq": "ReaXcomp or mapped dynamic EQ",
    "de_esser": "ReaXcomp or mapped de-esser",
    "resonance_suppressor": "mapped dynamic EQ or TDR Nova if detected",
    "high_fizz_control": "mapped dynamic EQ or gentle ReaXcomp band",
    "side_cleanup": "JS M/S utility if mapped",
    "phase_correlation_guard": "JS M/S utility if mapped",
    "artifact_suppressor": "mapped project JSFX only",
    "optional_subtle_saturation": "mapped saturator only",
    "output_gain": "REAPER track gain or JS utility",
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _intensity_scale(analysis: dict[str, Any]) -> float:
    already_mixed = float(analysis.get("already_mixed_score", 0.0))
    if already_mixed > 0.85:
        return 0.60
    if already_mixed > 0.70:
        return 0.75
    return 1.0


def profile_name_for_action(action: str, analysis: dict[str, Any] | None = None) -> str:
    analysis = analysis or {}
    artifact = analysis.get("artifact_profile", {})
    if action in {"minimal_cleanup_draft", "conservative_ai_vocal_cleanup_draft"} and artifact.get("vocal_thinness_score", 0.0) > 0.58:
        return "thin_vocal_body_preserve"
    return PROFILE_FOR_ACTION.get(action, "skip_recovery")


def resolve_recovery_profile(action: str, analysis: dict[str, Any], adapter_status: dict[str, Any] | None = None) -> dict[str, Any]:
    profile_name = profile_name_for_action(action, analysis)
    settings = deepcopy(PROFILES[profile_name])
    processing = analysis.get("processing_profile", {})
    artifact = analysis.get("artifact_profile", {})
    source_class = analysis.get("source_classification", "unknown")
    warnings: list[str] = []

    if source_class == "full_mix" or action in {"stem_required", "unsafe_to_process", "manual_review_required", "skip", "no_recovery_needed"}:
        profile_name = "skip_recovery"
        settings = deepcopy(PROFILES["skip_recovery"])

    scale = _intensity_scale(analysis)
    for key, value in list(settings.items()):
        if key.endswith("_amount") and isinstance(value, (int, float)):
            settings[key] = round(clamp(float(value) * scale), 6)

    if processing.get("compression_limited_score", 0.0) > 0.70:
        settings["compression_amount"] = 0.0
        warnings.append("source already appears compressed; compression disabled")
    if processing.get("baked_reverb_score", 0.0) > 0.60:
        settings["added_reverb_amount"] = 0.0
        warnings.append("baked reverb detected; no added reverb")
    if processing.get("mono_compatibility_risk", 0.0) > 0.55 or artifact.get("watery_phase_score", 0.0) > 0.55:
        settings["stereo_width_change"] = min(float(settings.get("stereo_width_change", 0.0)), 0.0)
        warnings.append("phase risk detected; widening disabled")
    if artifact.get("vocal_thinness_score", 0.0) > 0.55:
        for key in ("mud_dynamic_cut_amount", "high_fizz_control_amount", "side_noise_reduction_amount"):
            if key in settings:
                settings[key] = round(float(settings[key]) * 0.70, 6)
        settings["body_preserve"] = max(float(settings.get("body_preserve", 0.0)), 1.0)
        warnings.append("thin vocal detected; body preservation prioritized")

    write_set, skipped = mapped_semantic_controls(settings, adapter_status or {})
    return {
        "profile": profile_name,
        "settings": settings,
        "plugin_chain": build_plugin_chain(profile_name, settings, adapter_status or {}),
        "semantic_controls_to_write": write_set,
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
                "value": clamp(value, -24.0, 24.0) if semantic.endswith("_db") else value,
                "target_name": mapping.get("target_name"),
                "mapping_confidence": mapping.get("confidence"),
            }
        else:
            skipped[semantic] = {
                "value": value,
                "reason": "missing or low-confidence semantic mapping",
            }
    return written, skipped


def build_plugin_chain(profile_name: str, settings: dict[str, Any], adapter_status: dict[str, Any]) -> list[dict[str, Any]]:
    categories = CHAIN_ORDER.get(profile_name, [])
    plugins = adapter_status.get("plugins", {}) if isinstance(adapter_status, dict) else {}
    strict_gate = bool(adapter_status.get("strict_adapter_gate", False)) if isinstance(adapter_status, dict) else False
    chain = []
    for slot, category in enumerate(categories, start=1):
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
            workflow_stage="vocal_recovery",
            fallback=STOCK_FALLBACKS.get(category, "unmapped"),
        )
        legacy_safe = confidence >= MIN_MAPPING_CONFIDENCE
        chain.append(
            {
                "slot": slot,
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
