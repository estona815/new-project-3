from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import clamp, read_wav, rms, safe_db, write_json, write_wav
from automix.reference.reference_analyzer import analyze_reference_audio
from automix.reference.reference_comparison_engine import compare_current_to_reference_and_target


def missing_reference_match_eval(paths: dict[str, str | None] | None = None) -> dict[str, Any]:
    paths = paths or {}
    return {
        "schema": "automix-reference-match-eval-v1",
        "renders_created": {
            "current_mix": bool(paths.get("current_mix")),
            "reference_match_draft": bool(paths.get("reference_match_draft")),
            "loudness_matched": False,
            "difference": False,
        },
        "match_improvement_scores": {
            "overall_safe_match_delta": 0.0,
            "vocal_forwardness_delta": 0.0,
            "lead_melody_prominence_delta": 0.0,
            "low_end_control_delta": 0.0,
            "drum_energy_delta": 0.0,
            "808_translation_delta": 0.0,
            "stereo_match_delta": 0.0,
            "phone_translation_delta": 0.0,
        },
        "damage_scores": {
            "vocal_harshness_increase": 0.0,
            "sibilance_splatter_increase": 0.0,
            "metallic_artifact_increase": 0.0,
            "ai_fizz_increase": 0.0,
            "vocal_forwardness_loss": 0.0,
            "lead_melody_masking_increase": 0.0,
            "beat_impact_loss": 0.0,
            "low_end_mud_increase": 0.0,
            "phase_correlation_worsening": 0.0,
            "stereo_width_shift": 0.0,
            "limiter_pressure_increase": 0.0,
        },
        "evaluation_passed": False,
        "recommended_action": "manual_review_required",
        "warnings": ["missing reference match A/B renders"],
    }


def evaluate_reference_match_ab(
    *,
    current_mix_path: Path,
    reference_match_draft_path: Path,
    reference_analyses: list[dict[str, Any]],
    target_profile: str,
    project_name: str,
    output_dir: Path,
) -> dict[str, Any]:
    if not current_mix_path.exists() or not reference_match_draft_path.exists():
        metrics = missing_reference_match_eval(
            {
                "current_mix": str(current_mix_path) if current_mix_path.exists() else None,
                "reference_match_draft": str(reference_match_draft_path) if reference_match_draft_path.exists() else None,
            }
        )
        write_json(output_dir / "eval_reports" / "reference_match_eval_metrics.json", metrics)
        return metrics
    current = read_wav(current_mix_path, max_seconds=None)
    draft = read_wav(reference_match_draft_path, max_seconds=None)
    count = min(len(current.frames), len(draft.frames))
    if count <= 0:
        metrics = missing_reference_match_eval()
        write_json(output_dir / "eval_reports" / "reference_match_eval_metrics.json", metrics)
        return metrics
    match_gain = max(0.25, min(4.0, rms(current.mono[:count]) / max(rms(draft.mono[:count]), 1.0e-9)))
    matched_frames = [[clamp(value * match_gain, -1.0, 1.0) for value in frame[: current.channels]] for frame in draft.frames[:count]]
    matched_path = output_dir / "eval_reports" / "reference_match_loudness_matched.wav"
    write_wav(matched_path, current, matched_frames)
    diff_frames = [[current.frames[i][ch] - matched_frames[i][ch] for ch in range(min(current.channels, len(matched_frames[i])))] for i in range(count)]
    diff_path = output_dir / "eval_reports" / "reference_match_difference.wav"
    write_wav(diff_path, current, diff_frames)

    cur_analysis = analyze_reference_audio(current, reference_name=project_name, role="current_mix", path=str(current_mix_path))
    draft_analysis = analyze_reference_audio(draft, reference_name=project_name + "_draft", role="reference_match_draft", path=str(reference_match_draft_path))
    cur_comp = compare_current_to_reference_and_target(project_name=project_name, current_analysis=cur_analysis, reference_analyses=reference_analyses, target_profile_name=target_profile)
    draft_comp = compare_current_to_reference_and_target(project_name=project_name, current_analysis=draft_analysis, reference_analyses=reference_analyses, target_profile_name=target_profile)
    c = cur_comp["comparison_summary"]
    d = draft_comp["comparison_summary"]
    cv = cur_analysis["vocal_profile"]
    dv = draft_analysis["vocal_profile"]
    ca = cur_analysis["artifact_profile"]
    da = draft_analysis["artifact_profile"]
    cs = cur_analysis["stereo_profile"]
    ds = draft_analysis["stereo_profile"]
    ce = cur_analysis["energy_profile"]
    de = draft_analysis["energy_profile"]
    ct = cur_analysis["tonal_profile"]
    dt = draft_analysis["tonal_profile"]
    damage = {
        "vocal_harshness_increase": round(max(0.0, dt["harshness_2k5_6k"] - ct["harshness_2k5_6k"]), 6),
        "sibilance_splatter_increase": round(max(0.0, da["sibilance_splatter_risk"] - ca["sibilance_splatter_risk"]), 6),
        "metallic_artifact_increase": round(max(0.0, da["metallic_harshness_risk"] - ca["metallic_harshness_risk"]), 6),
        "ai_fizz_increase": round(max(0.0, da["high_fizz_risk"] - ca["high_fizz_risk"]), 6),
        "vocal_forwardness_loss": round(max(0.0, cv["vocal_forwardness"] - dv["vocal_forwardness"]), 6),
        "lead_melody_masking_increase": round(max(0.0, dv["vocal_forwardness"] - draft_analysis["melody_profile"]["lead_melody_prominence"]) * 0.25, 6),
        "beat_impact_loss": round(max(0.0, ce["transient_punch"] - de["transient_punch"]), 6),
        "low_end_mud_increase": round(max(0.0, dt["low_mid_120_350"] - ct["low_mid_120_350"]), 6),
        "phase_correlation_worsening": round(max(0.0, cs["phase_correlation"] - ds["phase_correlation"]), 6),
        "stereo_width_shift": round(abs(ds["stereo_width_score"] - cs["stereo_width_score"]), 6),
        "limiter_pressure_increase": round(max(0.0, draft_analysis["loudness_profile"]["limiter_pressure_risk"] - cur_analysis["loudness_profile"]["limiter_pressure_risk"]), 6),
    }
    improvement = {
        "overall_safe_match_delta": round(max(0.0, d["safe_match_score"] - c["safe_match_score"]), 6),
        "vocal_forwardness_delta": round(max(0.0, dv["vocal_forwardness"] - cv["vocal_forwardness"]), 6),
        "lead_melody_prominence_delta": round(max(0.0, draft_analysis["melody_profile"]["lead_melody_prominence"] - cur_analysis["melody_profile"]["lead_melody_prominence"]), 6),
        "low_end_control_delta": round(max(0.0, c["low_end_match_score"] - d["low_end_match_score"]), 6),
        "drum_energy_delta": round(max(0.0, de["drum_energy"] - ce["drum_energy"]), 6),
        "808_translation_delta": round(max(0.0, de["808_energy"] - ce["808_energy"]), 6),
        "stereo_match_delta": round(max(0.0, d["stereo_match_score"] - c["stereo_match_score"]), 6),
        "phone_translation_delta": round(max(0.0, dv["vocal_clarity"] - cv["vocal_clarity"]), 6),
    }
    warnings: list[str] = []
    if damage["ai_fizz_increase"] > 0.10 or damage["metallic_artifact_increase"] > 0.10:
        warnings.append("ai_artifact_exposure_reject")
    if damage["vocal_harshness_increase"] > 0.10 or damage["sibilance_splatter_increase"] > 0.10:
        warnings.append("vocal_harshness_or_sibilance_reject")
    if damage["phase_correlation_worsening"] > 0.18 or damage["stereo_width_shift"] > 0.25:
        warnings.append("phase_or_stereo_shift_reject")
    if damage["beat_impact_loss"] > 0.20:
        warnings.append("beat_impact_loss_reject")
    if damage["low_end_mud_increase"] > 0.15:
        warnings.append("low_end_mud_increase_reject")
    evaluation_passed = not warnings and improvement["overall_safe_match_delta"] > 0.03
    metrics = {
        "schema": "automix-reference-match-eval-v1",
        "renders_created": {
            "current_mix": True,
            "reference_match_draft": True,
            "loudness_matched": matched_path.exists(),
            "difference": diff_path.exists(),
        },
        "current_mix_path": str(current_mix_path),
        "reference_match_draft_path": str(reference_match_draft_path),
        "loudness_matched_path": str(matched_path),
        "difference_path": str(diff_path),
        "match_improvement_scores": improvement,
        "damage_scores": damage,
        "evaluation_passed": evaluation_passed,
        "recommended_action": "accept_light_reference_match" if evaluation_passed else "manual_review_required",
        "warnings": warnings,
    }
    write_json(output_dir / "eval_reports" / "reference_match_eval_metrics.json", metrics)
    return metrics


def final_reference_recommendation(comparison: dict[str, Any], plan: dict[str, Any], eval_metrics: dict[str, Any] | None = None) -> str:
    if not comparison.get("references_count") and not plan.get("adjustments"):
        return "target_profile_only_used"
    if not plan.get("adjustments") and plan.get("blocked_adjustments"):
        return "unsafe_to_match"
    if not plan.get("adjustments"):
        return "no_reference_match_needed"
    if not eval_metrics:
        return "manual_mix_revision_required"
    if eval_metrics.get("evaluation_passed"):
        return "accept_light_reference_match"
    return "reject_reference_match"


def build_reference_match_matrix(project_name: str, comparison: dict[str, Any], plan: dict[str, Any], eval_metrics: dict[str, Any] | None, output_dir: Path) -> dict[str, Any]:
    summary = comparison.get("comparison_summary", {})
    matrix = {
        "schema": "automix-project-reference-match-matrix-v1",
        "project_name": project_name,
        "target_profile": comparison.get("target_profile"),
        "references_count": comparison.get("references_count", 0),
        "overall_match_score": summary.get("overall_match_score", 0.0),
        "safe_match_score": summary.get("safe_match_score", 0.0),
        "top_gaps": sorted(comparison.get("differences", {}).items(), key=lambda item: item[1], reverse=True)[:5],
        "safe_adjustments": [item.get("adjustment_type") for item in plan.get("adjustments", [])],
        "blocked_adjustments": plan.get("blocked_adjustments", []),
        "draft_created": False,
        "evaluation_status": (
            "not_required"
            if not plan.get("adjustments")
            else ("passed" if eval_metrics and eval_metrics.get("evaluation_passed") else ("failed" if eval_metrics else "not_run"))
        ),
        "final_recommendation": final_reference_recommendation(comparison, plan, eval_metrics),
    }
    write_json(output_dir / "eval_reports" / "project_reference_match_matrix.json", matrix)
    return matrix
