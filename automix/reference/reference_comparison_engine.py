from __future__ import annotations

from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import clamp, mean, write_json
from automix.reference.genre_target_profiles import get_target_profile, max_excess, target_gap


def _avg(analyses: list[dict[str, Any]], section: str, key: str) -> float:
    values = [float(item.get(section, {}).get(key, 0.0)) for item in analyses if item.get(section)]
    return mean(values)


def average_reference_features(reference_analyses: list[dict[str, Any]], role: str | None = None) -> dict[str, dict[str, float]]:
    selected = [item for item in reference_analyses if not role or item.get("role") == role]
    if not selected:
        selected = reference_analyses
    sections = {
        "loudness_profile": ["integrated_lufs", "true_peak_dbTP", "lra", "crest_factor", "peak_density_score", "limiter_pressure_risk"],
        "tonal_profile": ["sub_20_60", "bass_60_120", "low_mid_120_350", "mid_350_1k", "presence_1k_4k", "harshness_2k5_6k", "sibilance_5k_10k", "air_10k_16k"],
        "energy_profile": ["drum_energy", "808_energy", "transient_punch", "rhythmic_density", "hook_energy"],
        "vocal_profile": ["vocal_forwardness", "vocal_clarity", "vocal_body", "vocal_presence", "vocal_air", "vocal_sibilance"],
        "melody_profile": ["lead_melody_prominence", "mid_high_melodic_density", "hook_melody_stability"],
        "stereo_profile": ["stereo_width_score", "mid_energy_score", "side_energy_score", "mono_compatibility_risk", "phase_correlation", "low_end_stereo_risk"],
        "artifact_profile": ["metallic_harshness_risk", "high_fizz_risk", "sibilance_splatter_risk", "vocal_thinness_risk"],
    }
    return {section: {key: round(_avg(selected, section, key), 6) for key in keys} for section, keys in sections.items()}


def _score_gap(gap: float, scale: float = 0.35) -> float:
    return round(clamp(1.0 - abs(gap) / scale), 6)


def compare_current_to_reference_and_target(
    *,
    project_name: str,
    current_analysis: dict[str, Any],
    reference_analyses: list[dict[str, Any]],
    target_profile_name: str,
    safety_constraints: dict[str, Any] | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    target = get_target_profile(target_profile_name)
    ref = average_reference_features(reference_analyses) if reference_analyses else {}
    cur_loud = current_analysis.get("loudness_profile", {})
    cur_tonal = current_analysis.get("tonal_profile", {})
    cur_energy = current_analysis.get("energy_profile", {})
    cur_vocal = current_analysis.get("vocal_profile", {})
    cur_melody = current_analysis.get("melody_profile", {})
    cur_stereo = current_analysis.get("stereo_profile", {})
    cur_art = current_analysis.get("artifact_profile", {})

    reference_lufs = ref.get("loudness_profile", {}).get("integrated_lufs", target["loudness_target_lufs_range"][0])
    target_lufs_mid = mean(target["loudness_target_lufs_range"])
    loudness_target = reference_lufs if reference_analyses else target_lufs_mid
    differences = {
        "vocal_too_low": target_gap(cur_vocal.get("vocal_forwardness", 0.0), target["vocal_forwardness_target"]),
        "vocal_too_harsh": max_excess(cur_tonal.get("harshness_2k5_6k", 0.0), target["harshness_max"]),
        "vocal_too_thin": target_gap(cur_vocal.get("vocal_body", 0.0), 0.45),
        "lead_melody_too_low": target_gap(cur_melody.get("lead_melody_prominence", 0.0), target["lead_melody_prominence_target"]),
        "drums_too_soft": target_gap(cur_energy.get("drum_energy", 0.0), target["drum_energy_target"]),
        "808_too_weak": target_gap(cur_energy.get("808_energy", 0.0), target["808_energy_target"]),
        "low_end_too_muddy": max_excess(cur_tonal.get("low_mid_120_350", 0.0) + cur_stereo.get("low_end_stereo_risk", 0.0) * 0.35, 0.55),
        "presence_too_masked": target_gap(cur_tonal.get("presence_1k_4k", 0.0), target["presence_clarity_target"]),
        "air_too_fizzy": max_excess(cur_art.get("high_fizz_risk", 0.0), target["ai_artifact_exposure_max"]),
        "stereo_too_wide": max_excess(cur_stereo.get("stereo_width_score", 0.0), target["stereo_width_target"] + 0.15),
        "stereo_too_narrow": target_gap(cur_stereo.get("stereo_width_score", 0.0), target["stereo_width_target"]),
        "mix_too_limited": max_excess(cur_loud.get("limiter_pressure_risk", 0.0), 0.55),
        "mix_not_loud_enough": round(clamp((loudness_target - float(cur_loud.get("integrated_lufs", -99.0))) / 6.0), 6),
        "ai_artifacts_too_exposed": max_excess(max(cur_art.get("high_fizz_risk", 0.0), cur_art.get("metallic_harshness_risk", 0.0), cur_art.get("sibilance_splatter_risk", 0.0)), target["ai_artifact_exposure_max"]),
    }
    unsafe: list[str] = []
    safe_priorities: list[str] = []
    warnings: list[str] = []
    if differences["air_too_fizzy"] > 0.0 or differences["ai_artifacts_too_exposed"] > 0.0:
        unsafe.append("high_shelf_boost_blocked_ai_fizz_risk")
        unsafe.append("loudness_push_blocked_until_artifact_safe")
    if differences["mix_too_limited"] > 0.0:
        unsafe.append("more_limiting_blocked_current_mix_already_limited")
    if cur_stereo.get("mono_compatibility_risk", 0.0) > 0.55:
        unsafe.append("master_widening_blocked_mono_risk")
    if differences["808_too_weak"] > 0.0 and differences["low_end_too_muddy"] > 0.0:
        unsafe.append("808_boost_blocked_until_low_end_controlled")
        safe_priorities.append("low_end_control")
    for key, priority in (
        ("vocal_too_low", "vocal_forward_space"),
        ("lead_melody_too_low", "lead_melody_space"),
        ("drums_too_soft", "drum_energy_support"),
        ("808_too_weak", "808_support"),
        ("vocal_too_harsh", "harshness_guard"),
        ("air_too_fizzy", "high_fizz_guard"),
        ("stereo_too_narrow", "stereo_safety"),
        ("mix_not_loud_enough", "safe_loudness"),
    ):
        if differences[key] > 0.08 and priority not in safe_priorities:
            safe_priorities.append(priority)
    artifact_score = round(clamp(1.0 - differences["ai_artifacts_too_exposed"]), 6)
    summary = {
        "overall_match_score": round(mean([_score_gap(value) for value in differences.values()]), 6),
        "safe_match_score": round(mean([_score_gap(value) for key, value in differences.items() if key not in {"mix_not_loud_enough", "stereo_too_narrow"}] + [artifact_score]), 6),
        "vocal_match_score": _score_gap(differences["vocal_too_low"]),
        "low_end_match_score": _score_gap(max(differences["808_too_weak"], differences["low_end_too_muddy"])),
        "drum_energy_match_score": _score_gap(differences["drums_too_soft"]),
        "melody_prominence_match_score": _score_gap(differences["lead_melody_too_low"]),
        "stereo_match_score": _score_gap(max(differences["stereo_too_wide"], differences["stereo_too_narrow"])),
        "loudness_match_score": _score_gap(max(differences["mix_not_loud_enough"], differences["mix_too_limited"])),
        "artifact_safety_score": artifact_score,
    }
    warnings.extend(current_analysis.get("warnings", []))
    if reference_analyses:
        warnings.extend([warning for item in reference_analyses for warning in item.get("warnings", [])])
    else:
        warnings.append("target_profile_only_used_no_reference_files")
    if safety_constraints and safety_constraints.get("premaster_rejected"):
        unsafe.append("premaster_rejected_blocks_reference_match")
    comparison = {
        "schema": "automix-reference-match-comparison-v1",
        "project_name": project_name,
        "target_profile": target_profile_name,
        "references_count": len(reference_analyses),
        "comparison_summary": summary,
        "differences": differences,
        "safe_adjustment_priorities": safe_priorities,
        "unsafe_adjustments_blocked": sorted(set(unsafe)),
        "reference_average_profile": ref,
        "target_profile_details": target,
        "warnings": sorted(set(warnings)),
    }
    if output_dir:
        write_json(output_dir / "eval_reports" / "reference_match_comparison.json", comparison)
    return comparison
