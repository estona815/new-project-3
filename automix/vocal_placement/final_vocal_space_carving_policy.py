from __future__ import annotations

from copy import deepcopy
from typing import Any


PROFILE_VERSION = "automix-final-vocal-space-carving-policy-v1"

PLACEMENT_PROFILES: dict[str, dict[str, Any]] = {
    "fragile_ai_vocal_space": {
        "vocal_gain_db": 0.0,
        "max_vocal_gain_db": 0.5,
        "instrumental_duck_db": -0.6,
        "presence_duck_db": -0.8,
        "low_mid_duck_db": -0.5,
        "sibilance_conflict_duck_db": -0.3,
        "backing_vocal_duck_db": -1.0,
        "send_duck_db": -0.7,
        "duck_attack_ms": 30,
        "duck_release_ms": 220,
        "ms_mid_cleanup": 0.05,
        "ms_side_cleanup": 0.04,
        "vocal_harshness_guard": 0.10,
        "vocal_sibilance_guard": 0.08,
        "no_widening": True,
        "no_pitch": True,
        "no_heavy_compression": True,
    },
    "vocal_forward_space_carve": {
        "vocal_gain_db": 0.3,
        "max_vocal_gain_db": 1.0,
        "instrumental_duck_db": -0.9,
        "presence_duck_db": -1.2,
        "low_mid_duck_db": -0.7,
        "sibilance_conflict_duck_db": -0.5,
        "backing_vocal_duck_db": -1.3,
        "send_duck_db": -1.0,
        "duck_attack_ms": 20,
        "duck_release_ms": 180,
        "ms_mid_cleanup": 0.10,
        "ms_side_cleanup": 0.06,
        "vocal_harshness_guard": 0.12,
        "vocal_sibilance_guard": 0.10,
        "no_widening": True,
        "no_pitch": True,
    },
    "melody_and_vocal_balance": {
        "vocal_gain_db": 0.2,
        "max_vocal_gain_db": 0.8,
        "melody_duck_db": -0.5,
        "instrumental_duck_db": -0.7,
        "presence_duck_db": -0.8,
        "low_mid_duck_db": -0.5,
        "backing_vocal_duck_db": -1.0,
        "send_duck_db": -0.8,
        "duck_attack_ms": 25,
        "duck_release_ms": 200,
        "preserve_lead_melody": True,
        "avoid_hook_damage": True,
        "no_pitch": True,
    },
    "minimal_space_fix": {
        "vocal_gain_db": 0.2,
        "max_vocal_gain_db": 0.5,
        "instrumental_duck_db": -0.4,
        "presence_duck_db": -0.5,
        "low_mid_duck_db": -0.3,
        "backing_vocal_duck_db": -0.7,
        "send_duck_db": -0.5,
        "duck_attack_ms": 30,
        "duck_release_ms": 250,
        "no_pitch": True,
    },
}

PROFILE_CHAIN_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "fragile_ai_vocal_space": [
        ("instrumental_bus", "sidechain_dynamic_eq"),
        ("instrumental_bus", "ms_cleanup"),
        ("backing_vocals", "sidechain_ducker"),
        ("send_returns", "send_return_ducker"),
        ("lead_vocal", "harshness_guard"),
        ("lead_vocal", "output_gain"),
    ],
    "vocal_forward_space_carve": [
        ("lead_vocal", "utility_gain"),
        ("instrumental_bus", "sidechain_dynamic_eq"),
        ("instrumental_bus", "multiband_ducker"),
        ("instrumental_bus", "ms_cleanup"),
        ("backing_vocals", "sidechain_ducker"),
        ("send_returns", "send_return_ducker"),
        ("lead_vocal", "harshness_guard"),
        ("lead_vocal", "output_gain"),
    ],
    "melody_and_vocal_balance": [
        ("lead_vocal", "utility_gain"),
        ("instrumental_bus", "sidechain_dynamic_eq"),
        ("melody_tracks", "narrow_melody_duck"),
        ("backing_vocals", "sidechain_ducker"),
        ("send_returns", "send_return_ducker"),
        ("lead_vocal", "output_gain"),
    ],
    "minimal_space_fix": [
        ("lead_vocal", "utility_gain"),
        ("instrumental_bus", "sidechain_dynamic_eq"),
        ("backing_vocals", "sidechain_ducker"),
        ("send_returns", "send_return_ducker"),
        ("lead_vocal", "output_gain"),
    ],
}

CATEGORY_CONTROLS: dict[str, list[str]] = {
    "utility_gain": ["vocal_gain_db", "max_vocal_gain_db"],
    "sidechain_dynamic_eq": [
        "instrumental_duck_db",
        "presence_duck_db",
        "low_mid_duck_db",
        "sibilance_conflict_duck_db",
        "duck_attack_ms",
        "duck_release_ms",
    ],
    "multiband_ducker": ["instrumental_duck_db", "duck_attack_ms", "duck_release_ms"],
    "ms_cleanup": ["ms_mid_cleanup", "ms_side_cleanup"],
    "sidechain_ducker": ["backing_vocal_duck_db", "duck_attack_ms", "duck_release_ms"],
    "send_return_ducker": ["send_duck_db", "duck_attack_ms", "duck_release_ms"],
    "narrow_melody_duck": ["melody_duck_db", "presence_duck_db", "duck_attack_ms", "duck_release_ms"],
    "harshness_guard": ["vocal_harshness_guard", "vocal_sibilance_guard"],
    "output_gain": ["vocal_gain_db"],
}

SAFE_CATEGORY_FALLBACKS = {
    "utility_gain": "REAPER utility gain on draft bus only",
    "sidechain_dynamic_eq": "validated ReaEQ/ReaXcomp/TDR Nova-style dynamic EQ adapter",
    "multiband_ducker": "validated ReaXcomp sidechain draft adapter",
    "ms_cleanup": "validated JS M/S utility adapter",
    "sidechain_ducker": "validated ReaComp/ReaXcomp sidechain adapter",
    "send_return_ducker": "validated ReaComp send-return ducking adapter",
    "narrow_melody_duck": "validated narrow dynamic EQ adapter",
    "harshness_guard": "validated dynamic EQ/de-esser adapter",
    "output_gain": "REAPER utility gain on draft bus only",
}


def clamp_float(value: Any, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = low
    return max(low, min(high, parsed))


def reduce_profile_intensity(settings: dict[str, Any], factor: float) -> dict[str, Any]:
    reduced = deepcopy(settings)
    for key, value in list(reduced.items()):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        if key.endswith("_db") and value < 0.0:
            reduced[key] = round(float(value) * factor, 6)
        elif key in {"vocal_gain_db", "ms_mid_cleanup", "ms_side_cleanup", "vocal_harshness_guard", "vocal_sibilance_guard"}:
            reduced[key] = round(float(value) * factor, 6)
    return reduced


def select_final_vocal_space_profile(
    vocal_space_analysis: dict[str, Any],
    target_resolution: dict[str, Any],
    accepted_source: dict[str, Any] | None,
) -> dict[str, Any]:
    warnings = list(vocal_space_analysis.get("warnings", []))
    fragile = bool(
        vocal_space_analysis.get("fragile_source")
        or (accepted_source or {}).get("fragile_source")
        or (accepted_source or {}).get("decision") == "accepted_light"
        or vocal_space_analysis.get("ai_artifact_exposure_risk", 0.0) > 0.55
    )
    melody_tracks = target_resolution.get("synth_sample_lead_tracks", []) + target_resolution.get("guitar_tracks", []) + target_resolution.get("piano_tracks", [])
    if fragile:
        profile = "fragile_ai_vocal_space"
        warnings.append("fragile source profile selected; gain, ducking, widening, saturation, and pitch are constrained")
    elif melody_tracks and vocal_space_analysis.get("instrumental_masking_score", 0.0) > 0.35:
        profile = "melody_and_vocal_balance"
    elif vocal_space_analysis.get("vocal_forwardness", 0.0) > 0.58 and vocal_space_analysis.get("instrumental_masking_score", 0.0) < 0.40:
        profile = "minimal_space_fix"
    else:
        profile = "vocal_forward_space_carve"
    return {
        "schema": PROFILE_VERSION,
        "selected_profile": profile,
        "settings": deepcopy(PLACEMENT_PROFILES[profile]),
        "warnings": sorted(set(warnings)),
    }


def _adapter_category_available(plugin_readiness: dict[str, Any], category: str) -> tuple[bool, str, float]:
    safe_adapters = int(plugin_readiness.get("safe_adapters_count", 0) or 0)
    can_place = bool(plugin_readiness.get("can_run_vocal_placement_safely") or plugin_readiness.get("safe_draft_plugin_ready"))
    if safe_adapters > 0 and can_place:
        return True, f"validated_adapter_for_{category}", 0.90
    return False, SAFE_CATEGORY_FALLBACKS.get(category, "unmapped"), 0.0


def build_final_vocal_space_chain_plan(
    *,
    project_name: str,
    target_resolution: dict[str, Any],
    vocal_space_analysis: dict[str, Any],
    profile_decision: dict[str, Any],
    plugin_readiness: dict[str, Any],
    apply_placement_draft: bool = False,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    profile = profile_decision["selected_profile"]
    settings = deepcopy(profile_decision["settings"])
    blockers = blockers or []
    fragile = bool(vocal_space_analysis.get("fragile_source"))
    if fragile:
        settings = reduce_profile_intensity(settings, 0.85)
        settings["vocal_gain_db"] = min(float(settings.get("vocal_gain_db", 0.0)), 0.0)
        settings["no_pitch"] = True
        settings["no_widening"] = True
        settings["no_heavy_compression"] = True

    plugin_chain = []
    controls_written: dict[str, Any] = {}
    controls_skipped: dict[str, Any] = {}
    for target_role, category in PROFILE_CHAIN_CATEGORIES.get(profile, []):
        available, plugin, confidence = _adapter_category_available(plugin_readiness, category)
        semantic_settings = {key: settings[key] for key in CATEGORY_CONTROLS.get(category, []) if key in settings}
        safe_to_apply = bool(apply_placement_draft and available and not blockers and semantic_settings)
        item = {
            "target_role": target_role,
            "category": category,
            "plugin": plugin,
            "semantic_settings": semantic_settings,
            "adapter_confidence": confidence,
            "safe_to_apply": safe_to_apply,
            "requires_parameter_discovery": not available,
            "adapter_confidence_gate_enforced": True,
            "no_fixed_parameter_indexes": True,
        }
        plugin_chain.append(item)
        for semantic, value in semantic_settings.items():
            if safe_to_apply:
                controls_written[semantic] = {
                    "value": value,
                    "target_role": target_role,
                    "category": category,
                    "plugin": plugin,
                    "mapping_confidence": confidence,
                }
            else:
                controls_skipped.setdefault(
                    semantic,
                    {
                        "value": value,
                        "reason": "draft_not_applied_or_adapter_unavailable",
                        "category": category,
                    },
                )

    safe_to_apply_all = bool(apply_placement_draft and plugin_chain and all(item["safe_to_apply"] for item in plugin_chain) and not blockers)
    return {
        "schema": "automix-final-vocal-space-carving-chain-plan-v1",
        "project_name": project_name,
        "accepted_lead_vocal": target_resolution.get("accepted_lead_vocal_recovery_draft"),
        "original_lead_vocal_reference": target_resolution.get("original_lead_vocal_reference"),
        "selected_profile": profile,
        "fragile_source": fragile,
        "semantic_settings": settings,
        "plugin_chain": plugin_chain,
        "semantic_controls_written": controls_written,
        "semantic_controls_skipped": controls_skipped,
        "blocked_adjustments": [
            "pitch_correction",
            "full_mix_pitch_experiment",
            "robotic_autotune",
            "stereo_widening_on_vocal",
            "heavy_compression",
            "ott",
            "aggressive_saturation",
            "master_limiter_on_original_master",
            "final_delivery_export",
        ],
        "draft_only": True,
        "safe_to_apply": safe_to_apply_all,
        "apply_requested": bool(apply_placement_draft),
        "original_tracks_must_remain_untouched": True,
        "accepted_recovery_draft_must_remain_untouched": True,
        "contains_pitch_correction": False,
        "contains_master_limiter": False,
        "warnings": sorted(set(profile_decision.get("warnings", []) + blockers)),
    }


def build_final_vocal_space_iteration_history(chain_plan: dict[str, Any], eval_metrics: dict[str, Any]) -> dict[str, Any]:
    settings = deepcopy(chain_plan.get("semantic_settings", {}))
    iterations = []
    current = deepcopy(settings)
    for iteration in range(0, 3):
        if iteration == 0:
            decision = "initial_review_required"
        elif iteration == 1:
            decision = "reduce_ducking_gain_release_ms_cleanup"
            current = reduce_profile_intensity(current, 0.70)
            if "vocal_gain_db" in current:
                current["vocal_gain_db"] = round(float(current["vocal_gain_db"]) * 0.50, 6)
            if "duck_release_ms" in current:
                current["duck_release_ms"] = round(float(current["duck_release_ms"]) * 1.20, 6)
        else:
            decision = "switch_to_fragile_or_minimal_disable_problem_blocks"
            if chain_plan.get("selected_profile") not in {"fragile_ai_vocal_space", "minimal_space_fix"}:
                current["switch_profile"] = "fragile_ai_vocal_space"
            current["disable_send_ducking_if_pumping"] = True
            current["disable_ms_cleanup_if_stereo_shift"] = True
            current["preserve_lead_melody_if_damaged"] = True
        iterations.append(
            {
                "iteration": iteration,
                "settings": deepcopy(current),
                "metrics": eval_metrics if iteration == 0 else {},
                "decision": decision,
                "stop_if_still_failing": iteration == 2,
            }
        )
    return {
        "schema": "automix-final-vocal-space-iteration-history-v1",
        "max_iterations": 2,
        "iterations": iterations,
        "final_fallback": "bypass_placement_fx_and_mark_manual_mix_required",
        "never_intensify_after_damage": True,
    }
