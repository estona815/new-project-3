from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import safe_filename, write_json
from automix.vocal_recovery.recovery_profiles import resolve_recovery_profile


RECOVERY_ACTIONS = {
    "skip",
    "minimal_cleanup_draft",
    "conservative_ai_vocal_cleanup_draft",
    "source_separated_rescue_draft",
    "stem_required",
    "manual_review_required",
    "unsafe_to_process",
}


def evaluate_recovery_policy(analysis: dict[str, Any]) -> dict[str, Any]:
    artifact = analysis.get("artifact_profile", {})
    processing = analysis.get("processing_profile", {})
    reason_codes: list[str] = []
    warnings = list(analysis.get("warnings", []))
    action = "skip"
    selected_profile = "skip_recovery"
    pitch_allowed_after_recovery = True
    recovery_applied = False

    full_mix = float(analysis.get("full_mix_likelihood", 0.0))
    source_sep = float(analysis.get("source_separated_likelihood", 0.0))
    already_mixed = float(analysis.get("already_mixed_score", 0.0))
    compression = float(processing.get("compression_limited_score", 0.0))
    baked_reverb = float(processing.get("baked_reverb_score", 0.0))
    watery = float(artifact.get("watery_phase_score", 0.0))
    metallic = float(artifact.get("metallic_harshness_score", 0.0))
    fizz = float(artifact.get("high_band_fizz_score", 0.0))
    thin = float(artifact.get("vocal_thinness_score", 0.0))
    mono_risk = float(processing.get("mono_compatibility_risk", 0.0))
    max_artifact = max(artifact.values()) if artifact else 0.0

    if full_mix > 0.65 or analysis.get("source_classification") == "full_mix":
        action = "stem_required"
        selected_profile = "skip_recovery"
        pitch_allowed_after_recovery = False
        reason_codes.append("FULL_MIX_UNSAFE")
    elif source_sep > 0.70 and analysis.get("analysis_basis") != "audio":
        action = "stem_required"
        selected_profile = "skip_recovery"
        pitch_allowed_after_recovery = False
        reason_codes.extend(["SOURCE_SEPARATED_HIGH", "AUDIO_REQUIRED_FOR_RESCUE_DRAFT"])
    elif source_sep > 0.70 and watery > 0.65:
        action = "stem_required"
        selected_profile = "skip_recovery"
        pitch_allowed_after_recovery = False
        reason_codes.extend(["SOURCE_SEPARATED_HIGH", "WATERY_PHASE_HIGH"])
    elif source_sep > 0.70 and watery > 0.45:
        action = "source_separated_rescue_draft"
        selected_profile = "source_separated_rescue"
        pitch_allowed_after_recovery = False
        recovery_applied = True
        reason_codes.extend(["SOURCE_SEPARATED_HIGH", "RECOVERY_EVAL_REQUIRED_BEFORE_PITCH"])
    elif thin > 0.58:
        action = "minimal_cleanup_draft"
        selected_profile = "thin_vocal_body_preserve"
        pitch_allowed_after_recovery = False
        recovery_applied = True
        reason_codes.append("VOCAL_THIN_BODY_PROTECT")
    elif max_artifact < 0.25 and already_mixed < 0.60:
        action = "skip"
        selected_profile = "skip_recovery"
        pitch_allowed_after_recovery = True
        reason_codes.append("LOW_ARTIFACT_NO_RECOVERY_NEEDED")
    elif max_artifact < 0.38:
        action = "minimal_cleanup_draft"
        selected_profile = "minimal_cleanup"
        pitch_allowed_after_recovery = False
        recovery_applied = True
        reason_codes.append("LOW_ARTIFACT_MINIMAL_ONLY")
    elif metallic > 0.45 or fizz > 0.45 or already_mixed > 0.65:
        action = "conservative_ai_vocal_cleanup_draft"
        selected_profile = "conservative_ai_vocal_cleanup"
        pitch_allowed_after_recovery = False
        recovery_applied = True
        reason_codes.append("CONSERVATIVE_AI_CLEANUP")
    else:
        action = "manual_review_required"
        selected_profile = "skip_recovery"
        pitch_allowed_after_recovery = False
        reason_codes.append("UNCERTAIN_RECOVERY_REQUIRES_REVIEW")

    if already_mixed > 0.70:
        reason_codes.append("ALREADY_MIXED_REDUCE_INTENSITY")
    if compression > 0.70:
        reason_codes.append("COMPRESSION_DISABLED_ALREADY_LIMITED")
        warnings.append("avoid compression or OTT-style upward compression")
    if baked_reverb > 0.60:
        reason_codes.append("NO_ADDED_REVERB")
        warnings.append("already wet source; protect reverb tails")
    if mono_risk > 0.55 or watery > 0.55:
        reason_codes.append("NO_STEREO_WIDENING")
        warnings.append("phasey source; widening disabled")
    if thin > 0.55:
        reason_codes.append("BODY_PRESERVE")
        warnings.append("thin vocal; do not over-denoise or remove low-mid body")

    return {
        "schema": "automix-vocal-recovery-policy-v1",
        "track_name": analysis.get("track_name"),
        "recovery_action": action,
        "selected_profile": selected_profile,
        "recovery_applied": recovery_applied,
        "draft_required": recovery_applied,
        "draft_track_name": f"{analysis.get('track_name', 'track')}_RECOVERY_DRAFT",
        "pitch_allowed_after_recovery": pitch_allowed_after_recovery,
        "requires_ab_evaluation": recovery_applied,
        "reason_codes": sorted(set(reason_codes)),
        "warnings": sorted(set(warnings)),
    }


def build_recovery_chain_plan(
    analysis: dict[str, Any],
    decision: dict[str, Any] | None = None,
    adapter_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = decision or evaluate_recovery_policy(analysis)
    profile = resolve_recovery_profile(decision["recovery_action"], analysis, adapter_status or {})
    chain = profile["plugin_chain"]
    safe_chain = all(item.get("safe_to_apply", False) for item in chain) if chain else False
    action = decision["recovery_action"]
    return {
        "schema": "automix-vocal-recovery-chain-plan-v1",
        "track_name": analysis["track_name"],
        "recovery_action": action,
        "source_classification": analysis["source_classification"],
        "artifact_profile": analysis["artifact_profile"],
        "processing_profile": analysis["processing_profile"],
        "selected_profile": profile["profile"],
        "plugin_chain": chain,
        "semantic_settings": profile["settings"],
        "semantic_controls_written": profile["semantic_controls_to_write"],
        "semantic_controls_skipped": profile["semantic_controls_skipped"],
        "rollback_required": True,
        "ab_eval_required": action.endswith("_draft"),
        "draft_only": True,
        "original_track_must_remain_untouched": True,
        "contains_pitch_correction": False,
        "safe_to_apply": bool(action.endswith("_draft") and safe_chain),
        "reason_codes": decision.get("reason_codes", []),
        "warnings": sorted(set(decision.get("warnings", []) + profile.get("warnings", []))),
    }


def build_recovery_rollback_metadata(analysis: dict[str, Any], chain_plan_path: Path, analysis_path: Path) -> dict[str, Any]:
    return {
        "schema": "automix-vocal-recovery-rollback-v1",
        "original_track_guid": analysis.get("track_guid", ""),
        "draft_track_guid": None,
        "plugins_inserted": [],
        "parameters_written": [],
        "chain_plan": str(chain_plan_path),
        "analysis_report": str(analysis_path),
        "created_at": analysis.get("scan_date_utc"),
        "safe_to_delete_draft": True,
        "draft_creation_status": "pending_reaper_runtime",
    }


def assert_original_track_unmodified_for_vocal_recovery(before: dict[str, Any], after: dict[str, Any]) -> None:
    checked = ("track_guid", "track_name", "fx_count", "item_count", "routing_count")
    changed = [key for key in checked if before.get(key) != after.get(key)]
    if changed:
        raise AssertionError(f"Original track modified during vocal recovery draft creation: {', '.join(changed)}")


def write_recovery_report(
    output_dir: Path,
    analysis: dict[str, Any],
    decision: dict[str, Any],
    chain_plan: dict[str, Any],
    eval_metrics: dict[str, Any] | None = None,
    iteration_history: dict[str, Any] | None = None,
) -> Path:
    eval_metrics = eval_metrics or {}
    iteration_history = iteration_history or {"iterations": []}
    path = output_dir / "eval_reports" / f"{safe_filename(analysis['track_name'])}_vocal_recovery_report.md"
    artifact = analysis["artifact_profile"]
    processing = analysis["processing_profile"]
    final = final_recommendation(decision, eval_metrics)
    lines = [
        "# Vocal Recovery Safety Report",
        "",
        "## Summary",
        "",
        f"- Final recommendation: `{final}`",
        f"- Recovery applied: `{decision['recovery_applied']}`",
        f"- Draft track: `{decision['draft_track_name']}`",
        "- Original untouched: `true`",
        f"- Source classification: `{analysis['source_classification']}`",
        f"- Risk: `{analysis['recovery_risk']}`",
        "",
        "## Artifact Profile",
        "",
    ]
    for key in (
        "metallic_harshness_score",
        "watery_phase_score",
        "codec_birdies_score",
        "formant_wobble_score",
        "sibilance_warble_score",
        "reverb_smear_score",
        "high_band_fizz_score",
        "low_mid_mud_score",
        "nasal_resonance_score",
        "transient_smear_score",
        "vocal_thinness_score",
    ):
        lines.append(f"- {key}: `{artifact.get(key, 0.0)}`")

    lines.extend(["", "## Processing Profile", ""])
    for key in (
        "already_mixed_score",
        "already_tuned_score",
        "compression_limited_score",
        "baked_reverb_score",
        "stereo_width_score",
        "mono_compatibility_risk",
        "phase_correlation",
    ):
        value = analysis.get(key, processing.get(key, 0.0))
        lines.append(f"- {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Recovery Decision",
            "",
            f"- selected profile: `{chain_plan['selected_profile']}`",
            f"- reason codes: `{', '.join(decision.get('reason_codes', [])) or 'none'}`",
            f"- semantic settings: `{json.dumps(chain_plan.get('semantic_settings', {}), sort_keys=True)}`",
            f"- plugin chain: `{json.dumps(chain_plan.get('plugin_chain', []), sort_keys=True)}`",
            f"- controls written: `{json.dumps(chain_plan.get('semantic_controls_written', {}), sort_keys=True)}`",
            f"- controls skipped: `{json.dumps(chain_plan.get('semantic_controls_skipped', {}), sort_keys=True)}`",
            f"- warnings: `{', '.join(chain_plan.get('warnings', [])) or 'none'}`",
            "",
            "## A/B Render Files",
            "",
            f"- original: `{eval_metrics.get('original_path')}`",
            f"- recovered: `{eval_metrics.get('recovered_path')}`",
            f"- loudness matched: `{eval_metrics.get('loudness_matched_path')}`",
            f"- difference: `{eval_metrics.get('difference_path')}`",
            "",
            "## Evaluation Metrics",
            "",
            f"- artifact reduction: `{json.dumps(eval_metrics.get('artifact_reduction_scores', {}), sort_keys=True)}`",
            f"- damage metrics: `{json.dumps(eval_metrics.get('damage_scores', {}), sort_keys=True)}`",
            f"- evaluation passed: `{eval_metrics.get('evaluation_passed', False)}`",
            "",
            "## Iteration History",
            "",
        ]
    )
    iterations = iteration_history.get("iterations", [])
    if iterations:
        for item in iterations:
            lines.append(f"- iteration {item.get('iteration')}: `{item.get('decision')}`")
    else:
        for idx in range(4):
            lines.append(f"- iteration {idx}: `not run`")

    lines.extend(
        [
            "",
            "## Manual Listening Checklist",
            "",
            "- Did metallic harshness reduce without dulling the vocal?",
            "- Did the vocal remain emotionally clear?",
            "- Did consonants stay sharp?",
            "- Did sibilance become lispy or watery?",
            "- Did the vocal lose body?",
            "- Did the stereo image become unstable?",
            "- Did reverb tails become unnatural?",
            "- Did the result sound less AI-like, or just quieter/darker?",
            "",
            "## Final Recommendation",
            "",
            f"`{final}`",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def final_recommendation(decision: dict[str, Any], eval_metrics: dict[str, Any]) -> str:
    action = decision.get("recovery_action")
    if action == "stem_required":
        return "stem_required"
    if action == "unsafe_to_process":
        return "unsafe_to_process"
    if action in {"skip", "no_recovery_needed"}:
        return "no_recovery_needed"
    if not eval_metrics:
        return "manual_cleanup_required" if action == "manual_review_required" else "manual_cleanup_required"
    if eval_metrics.get("evaluation_passed"):
        return "accept_light_recovery"
    return "reject_recovery"


def write_recovery_artifacts(
    output_dir: Path,
    analysis: dict[str, Any],
    decision: dict[str, Any],
    chain_plan: dict[str, Any],
    eval_metrics: dict[str, Any] | None = None,
    iteration_history: dict[str, Any] | None = None,
) -> dict[str, Path]:
    stem = safe_filename(analysis["track_name"])
    paths = {
        "analysis": output_dir / "analysis_reports" / f"{stem}_vocal_recovery_analysis.json",
        "chain_plan": output_dir / "chain_plans" / f"{stem}_vocal_recovery_chain_plan.json",
        "rollback": output_dir / "rollback" / f"{stem}_vocal_recovery_rollback.json",
        "iteration_history": output_dir / "eval_reports" / f"{stem}_vocal_recovery_iteration_history.json",
        "report": output_dir / "eval_reports" / f"{stem}_vocal_recovery_report.md",
    }
    write_json(paths["analysis"], analysis)
    write_json(paths["chain_plan"], chain_plan)
    write_json(paths["rollback"], build_recovery_rollback_metadata(analysis, paths["chain_plan"], paths["analysis"]))
    write_json(paths["iteration_history"], iteration_history or {"iterations": []})
    write_recovery_report(output_dir, analysis, decision, chain_plan, eval_metrics, iteration_history)
    return paths
