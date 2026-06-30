from __future__ import annotations

from copy import deepcopy
from typing import Any

from automix.plugins.adapter_confidence_gate import evaluate_adapter_confidence


MIN_MAPPING_CONFIDENCE = 0.85

PREMASTER_ACTIONS = {
    "safety_only_premaster",
    "safe_streaming_premaster",
    "loud_but_safe_premaster",
    "already_mastered_safety",
    "skip_premaster",
    "mix_revision_required",
    "manual_review_required",
}

PROFILES: dict[str, dict[str, Any]] = {
    "safety_only_premaster": {
        "input_trim_db": -1.0,
        "clean_eq_amount": 0.0,
        "dynamic_eq_amount": 0.08,
        "harshness_guard_amount": 0.12,
        "deesser_amount": 0.10,
        "low_end_mono_hz": 90.0,
        "ms_mid_eq_amount": 0.0,
        "ms_side_gain_db": 0.0,
        "bus_compressor_gain_reduction_db": 0.0,
        "bus_compressor_attack_ms": 30.0,
        "bus_compressor_release_ms": 180.0,
        "saturation_amount": 0.0,
        "clipper_drive_db": 0.0,
        "limiter_ceiling_dbTP": -1.0,
        "limiter_max_gain_db": 0.5,
        "limiter_release_ms": 120.0,
        "target_lufs": -14.0,
        "output_gain_db": 0.0,
    },
    "safe_streaming_premaster": {
        "input_trim_db": -0.5,
        "clean_eq_amount": 0.08,
        "dynamic_eq_amount": 0.14,
        "harshness_guard_amount": 0.16,
        "deesser_amount": 0.12,
        "low_end_mono_hz": 95.0,
        "ms_mid_eq_amount": 0.04,
        "ms_side_gain_db": 0.0,
        "bus_compressor_gain_reduction_db": 0.7,
        "bus_compressor_attack_ms": 35.0,
        "bus_compressor_release_ms": 220.0,
        "saturation_amount": 0.04,
        "clipper_drive_db": 0.0,
        "limiter_ceiling_dbTP": -1.0,
        "limiter_max_gain_db": 1.0,
        "limiter_release_ms": 140.0,
        "target_lufs": -13.5,
        "output_gain_db": 0.0,
    },
    "loud_but_safe_premaster": {
        "input_trim_db": -0.7,
        "clean_eq_amount": 0.08,
        "dynamic_eq_amount": 0.16,
        "harshness_guard_amount": 0.18,
        "deesser_amount": 0.12,
        "low_end_mono_hz": 95.0,
        "ms_mid_eq_amount": 0.04,
        "ms_side_gain_db": 0.0,
        "bus_compressor_gain_reduction_db": 1.1,
        "bus_compressor_attack_ms": 35.0,
        "bus_compressor_release_ms": 240.0,
        "saturation_amount": 0.06,
        "clipper_drive_db": 0.25,
        "limiter_ceiling_dbTP": -1.0,
        "limiter_max_gain_db": 1.5,
        "limiter_release_ms": 160.0,
        "target_lufs": -11.5,
        "output_gain_db": 0.0,
    },
    "already_mastered_safety": {
        "input_trim_db": -1.0,
        "clean_eq_amount": 0.0,
        "dynamic_eq_amount": 0.05,
        "harshness_guard_amount": 0.10,
        "deesser_amount": 0.08,
        "low_end_mono_hz": 90.0,
        "ms_mid_eq_amount": 0.0,
        "ms_side_gain_db": 0.0,
        "bus_compressor_gain_reduction_db": 0.0,
        "bus_compressor_attack_ms": 40.0,
        "bus_compressor_release_ms": 260.0,
        "saturation_amount": 0.0,
        "clipper_drive_db": 0.0,
        "limiter_ceiling_dbTP": -1.0,
        "limiter_max_gain_db": 0.3,
        "limiter_release_ms": 180.0,
        "target_lufs": -14.0,
        "output_gain_db": 0.0,
    },
    "skip_premaster": {
        "apply": False,
    },
}

PROFILE_FOR_ACTION = {
    "safety_only_premaster": "safety_only_premaster",
    "safe_streaming_premaster": "safe_streaming_premaster",
    "loud_but_safe_premaster": "loud_but_safe_premaster",
    "already_mastered_safety": "already_mastered_safety",
    "skip_premaster": "skip_premaster",
    "mix_revision_required": "skip_premaster",
    "manual_review_required": "skip_premaster",
}

CHAIN_ORDER = {
    "safety_only_premaster": [
        "input_trim",
        "linear_or_clean_eq",
        "dynamic_eq",
        "de_esser_or_harshness_guard",
        "low_end_mono_control",
        "ms_eq",
        "true_peak_limiter",
        "loudness_meter",
        "phase_correlation_meter",
        "output_gain",
    ],
    "safe_streaming_premaster": [
        "input_trim",
        "linear_or_clean_eq",
        "dynamic_eq",
        "de_esser_or_harshness_guard",
        "low_end_mono_control",
        "ms_eq",
        "bus_compressor",
        "optional_subtle_saturation",
        "true_peak_limiter",
        "loudness_meter",
        "phase_correlation_meter",
        "output_gain",
    ],
    "loud_but_safe_premaster": [
        "input_trim",
        "linear_or_clean_eq",
        "dynamic_eq",
        "de_esser_or_harshness_guard",
        "low_end_mono_control",
        "ms_eq",
        "bus_compressor",
        "optional_subtle_saturation",
        "optional_soft_clipper",
        "true_peak_limiter",
        "loudness_meter",
        "phase_correlation_meter",
        "output_gain",
    ],
    "already_mastered_safety": [
        "input_trim",
        "dynamic_eq",
        "de_esser_or_harshness_guard",
        "low_end_mono_control",
        "true_peak_limiter",
        "loudness_meter",
        "phase_correlation_meter",
        "output_gain",
    ],
    "skip_premaster": [],
}

CATEGORY_SETTINGS = {
    "input_trim": ["input_trim_db"],
    "linear_or_clean_eq": ["clean_eq_amount"],
    "dynamic_eq": ["dynamic_eq_amount"],
    "de_esser_or_harshness_guard": ["harshness_guard_amount", "deesser_amount"],
    "low_end_mono_control": ["low_end_mono_hz"],
    "ms_eq": ["ms_mid_eq_amount", "ms_side_gain_db"],
    "bus_compressor": [
        "bus_compressor_gain_reduction_db",
        "bus_compressor_attack_ms",
        "bus_compressor_release_ms",
    ],
    "optional_subtle_saturation": ["saturation_amount"],
    "optional_soft_clipper": ["clipper_drive_db"],
    "true_peak_limiter": ["limiter_ceiling_dbTP", "limiter_max_gain_db", "limiter_release_ms", "target_lufs"],
    "loudness_meter": [],
    "phase_correlation_meter": [],
    "output_gain": ["output_gain_db"],
}

STOCK_FALLBACKS = {
    "input_trim": "REAPER track or item gain on draft premaster only",
    "linear_or_clean_eq": "ReaEQ neutral draft if mapped",
    "dynamic_eq": "TDR Nova/ReaXcomp draft if mapped",
    "de_esser_or_harshness_guard": "TDR Nova/ReaXcomp/ReaEQ narrow dynamic draft if mapped",
    "low_end_mono_control": "JS M/S utility or routing matrix if mapped",
    "ms_eq": "JS M/S utility plus ReaEQ if mapped",
    "bus_compressor": "ReaComp conservative draft if mapped",
    "optional_subtle_saturation": "JS saturation bypassed unless high-confidence mapped",
    "optional_soft_clipper": "JS soft clipper bypassed unless high-confidence mapped",
    "true_peak_limiter": "Limiter plugin only on premaster draft, never original master",
    "loudness_meter": "REAPER loudness/analyzer meter only",
    "phase_correlation_meter": "REAPER phase/analyzer meter only",
    "output_gain": "REAPER track gain on draft premaster only",
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def clamp_db(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _max_artifact_risk(analysis: dict[str, Any]) -> float:
    profile = analysis.get("ai_artifact_risk_profile", {})
    return max((float(value) for value in profile.values()), default=0.0) if isinstance(profile, dict) else 0.0


def _cap_target_lufs(requested: float | None, profile_name: str, current: float) -> float:
    if requested is None:
        return current
    caps = {
        "safety_only_premaster": -14.0,
        "safe_streaming_premaster": -13.0,
        "loud_but_safe_premaster": -11.0,
        "already_mastered_safety": -14.0,
    }
    cap = caps.get(profile_name, -14.0)
    return min(float(requested), cap)


def profile_name_for_action(action: str, analysis: dict[str, Any]) -> str:
    if action not in PREMASTER_ACTIONS:
        return "skip_premaster"
    loud = analysis.get("loudness_profile", {})
    if action == "loud_but_safe_premaster":
        if (
            analysis.get("premaster_risk") != "low"
            or float(loud.get("limiter_pressure_risk", 0.0)) > 0.35
            or _max_artifact_risk(analysis) > 0.38
        ):
            return "safe_streaming_premaster"
    if float(loud.get("limiter_pressure_risk", 0.0)) > 0.68:
        return "already_mastered_safety"
    if _max_artifact_risk(analysis) > 0.65 and action not in {"skip_premaster", "mix_revision_required", "manual_review_required"}:
        return "safety_only_premaster"
    return PROFILE_FOR_ACTION.get(action, "skip_premaster")


def _preservation_clamp_settings(settings: dict[str, Any], analysis: dict[str, Any], warnings: list[str]) -> None:
    loud = analysis.get("loudness_profile", {})
    stereo = analysis.get("stereo_profile", {})
    artifact = analysis.get("ai_artifact_risk_profile", {})
    limiter_pressure = float(loud.get("limiter_pressure_risk", 0.0))
    crest = float(loud.get("crest_factor", 99.0))
    lra = float(loud.get("lra", 99.0))
    max_artifact = max((float(value) for value in artifact.values()), default=0.0) if isinstance(artifact, dict) else 0.0

    settings["ms_side_gain_db"] = 0.0
    if float(stereo.get("mono_compatibility_risk", 0.0)) > 0.45:
        settings["low_end_mono_hz"] = max(float(settings.get("low_end_mono_hz", 90.0)), 100.0)
        warnings.append("mono risk detected; all master widening remains disabled")

    if limiter_pressure > 0.58 or crest < 7.0 or lra < 3.0:
        settings["bus_compressor_gain_reduction_db"] = 0.0
        settings["saturation_amount"] = 0.0
        settings["clipper_drive_db"] = 0.0
        settings["limiter_max_gain_db"] = min(float(settings.get("limiter_max_gain_db", 0.5)), 0.5)
        warnings.append("already limited or low dynamic range; compressor, clipper, and saturation reduced")

    if max_artifact > 0.55:
        settings["saturation_amount"] = 0.0
        settings["clipper_drive_db"] = 0.0
        settings["limiter_max_gain_db"] = min(float(settings.get("limiter_max_gain_db", 0.5)), 0.6)
        settings["harshness_guard_amount"] = min(float(settings.get("harshness_guard_amount", 0.0)), 0.18)
        warnings.append("AI artifact risk detected; no clarity, saturation, or loudness intensification")

    if "limiter_ceiling_dbTP" in settings:
        settings["limiter_ceiling_dbTP"] = clamp_db(settings["limiter_ceiling_dbTP"], -2.0, -0.8)
    if "limiter_max_gain_db" in settings:
        settings["limiter_max_gain_db"] = clamp_db(settings["limiter_max_gain_db"], 0.0, 1.5)
    if "clipper_drive_db" in settings:
        settings["clipper_drive_db"] = clamp_db(settings["clipper_drive_db"], 0.0, 0.3)
    if "saturation_amount" in settings:
        settings["saturation_amount"] = clamp(settings["saturation_amount"], 0.0, 0.08)
    if "bus_compressor_gain_reduction_db" in settings:
        settings["bus_compressor_gain_reduction_db"] = clamp_db(settings["bus_compressor_gain_reduction_db"], 0.0, 1.2)
    for key in ("clean_eq_amount", "dynamic_eq_amount", "harshness_guard_amount", "deesser_amount", "ms_mid_eq_amount"):
        if key in settings:
            settings[key] = clamp(settings[key], 0.0, 0.20)
    if "low_end_mono_hz" in settings:
        settings["low_end_mono_hz"] = clamp_db(settings["low_end_mono_hz"], 70.0, 130.0)
    if "input_trim_db" in settings:
        settings["input_trim_db"] = clamp_db(settings["input_trim_db"], -3.0, 0.0)
    if "output_gain_db" in settings:
        settings["output_gain_db"] = clamp_db(settings["output_gain_db"], -1.0, 0.0)


def resolve_premaster_profile(
    action: str,
    analysis: dict[str, Any],
    adapter_status: dict[str, Any] | None = None,
    requested_target_lufs: float | None = None,
) -> dict[str, Any]:
    profile_name = profile_name_for_action(action, analysis)
    settings = deepcopy(PROFILES[profile_name])
    warnings: list[str] = []
    if action in {"skip_premaster", "mix_revision_required", "manual_review_required"}:
        profile_name = "skip_premaster"
        settings = deepcopy(PROFILES["skip_premaster"])
    if profile_name != action and action == "loud_but_safe_premaster":
        warnings.append("loud_but_safe_premaster downgraded because the source is not low-risk enough")

    if settings.get("apply", True):
        settings["target_lufs"] = _cap_target_lufs(requested_target_lufs, profile_name, float(settings.get("target_lufs", -14.0)))
        _preservation_clamp_settings(settings, analysis, warnings)

    written, skipped = mapped_semantic_controls(settings, adapter_status or {})
    return {
        "profile": profile_name,
        "settings": settings,
        "plugin_chain": build_plugin_chain(profile_name, settings, adapter_status or {}),
        "semantic_controls_to_write": written,
        "semantic_controls_skipped": skipped,
        "warnings": sorted(set(warnings)),
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
    for category in CHAIN_ORDER.get(profile_name, []):
        plugin_info = plugins.get(category, {}) if isinstance(plugins, dict) else {}
        confidence = float(plugin_info.get("adapter_confidence", plugin_info.get("confidence", 0.0))) if isinstance(plugin_info, dict) else 0.0
        plugin_name = plugin_info.get("plugin") if isinstance(plugin_info, dict) else None
        semantic_settings = {key: settings[key] for key in CATEGORY_SETTINGS.get(category, []) if key in settings}
        meter_only = category in {"loudness_meter", "phase_correlation_meter"}
        plugin_label = plugin_name or STOCK_FALLBACKS.get(category, "unmapped")
        workflow = "premaster_limiter" if category == "true_peak_limiter" else "premaster"
        gate = evaluate_adapter_confidence(
            desired_semantic_controls=semantic_settings,
            adapter=plugin_info.get("adapter") if isinstance(plugin_info, dict) else None,
            plugin_name=plugin_label,
            plugin_detected=meter_only or plugin_name is not None,
            workflow_stage=workflow,
            fallback=STOCK_FALLBACKS.get(category, "unmapped"),
        )
        legacy_safe = bool(meter_only or confidence >= MIN_MAPPING_CONFIDENCE)
        chain.append(
            {
                "target_track": "premaster_draft",
                "category": category,
                "plugin": plugin_label,
                "semantic_settings": semantic_settings,
                "adapter_confidence": confidence,
                "safe_to_apply": bool(legacy_safe and (gate["allowed"] if strict_gate and semantic_settings else True)),
                "requires_parameter_discovery": bool((not meter_only) and (confidence < MIN_MAPPING_CONFIDENCE or (strict_gate and gate["fallback_required"]))),
                "no_fixed_parameter_indexes": True,
                "stock_fallback": STOCK_FALLBACKS.get(category, "unmapped"),
                "adapter_confidence_gate_enforced": True,
                "adapter_confidence_gate": gate,
            }
        )
    return chain
