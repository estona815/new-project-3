from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import write_json
from automix.mastering.premaster_iteration_engine import build_premaster_iteration_history
from automix.mastering.premaster_profiles import resolve_premaster_profile
from automix.mastering.premaster_safety_analyzer import build_translation_check, missing_premaster_eval_metrics


PREMASTER_POLICY_ACTIONS = {
    "safety_only_premaster",
    "safe_streaming_premaster",
    "loud_but_safe_premaster",
    "already_mastered_safety",
    "skip_premaster",
    "mix_revision_required",
    "manual_review_required",
}


def _max_value(data: dict[str, Any]) -> float:
    return max((float(value) for value in data.values()), default=0.0) if isinstance(data, dict) else 0.0


def evaluate_premaster_policy(
    analysis: dict[str, Any],
    workflow_status: dict[str, Any] | None = None,
    requested_mode: str | None = None,
    target_lufs: float | None = None,
) -> dict[str, Any]:
    workflow_status = workflow_status or {}
    requested_mode = requested_mode or analysis.get("recommended_premaster_mode", "safe_streaming_premaster")
    loud = analysis.get("loudness_profile", {})
    artifact = analysis.get("ai_artifact_risk_profile", {})
    vocal = analysis.get("vocal_preservation_profile", {})
    stereo = analysis.get("stereo_profile", {})
    translation = analysis.get("translation_profile", {})
    warnings = list(analysis.get("warnings", []))
    reason_codes: list[str] = []

    placement_result = workflow_status.get("placement_recommendation") or workflow_status.get("final_recommendation")
    placement_action = workflow_status.get("placement_action")
    placement_rejected = placement_result in {"reject_placement", "manual_mix_required", "stem_required"} or placement_action in {
        "manual_mix_required",
        "stem_required",
    }
    limiter_pressure = float(loud.get("limiter_pressure_risk", 0.0))
    true_peak = float(loud.get("true_peak_dbTP", -99.0))
    integrated_lufs = float(loud.get("integrated_lufs", -99.0))
    max_artifact = _max_value(artifact)
    vocal_forwardness = float(vocal.get("vocal_forwardness_score", 1.0))
    mono_risk = float(stereo.get("mono_compatibility_risk", 0.0))
    low_end_risk = float(translation.get("club_low_end_risk", 0.0))

    action = "safe_streaming_premaster"
    selected_profile = "safe_streaming_premaster"
    draft_required = True

    if requested_mode == "skip_premaster":
        action = "skip_premaster"
        selected_profile = "skip_premaster"
        draft_required = False
        reason_codes.append("USER_REQUESTED_SKIP")
    elif placement_rejected:
        action = "mix_revision_required"
        selected_profile = "skip_premaster"
        draft_required = False
        reason_codes.append("PLACEMENT_REJECTED_FIX_MIX_BEFORE_PREMASTER")
    elif vocal_forwardness < 0.20:
        action = "mix_revision_required"
        selected_profile = "skip_premaster"
        draft_required = False
        reason_codes.append("WEAK_VOCAL_FORWARDNESS_FIX_MIX_NOT_MASTER")
    elif limiter_pressure > 0.68 or integrated_lufs > -9.5 or true_peak > -0.6:
        action = "already_mastered_safety"
        selected_profile = "already_mastered_safety"
        reason_codes.append("ALREADY_LIMITED_OR_MASTERED_SAFETY_ONLY")
    elif max_artifact > 0.65:
        action = "safety_only_premaster"
        selected_profile = "safety_only_premaster"
        reason_codes.append("AI_ARTIFACT_RISK_NO_LOUDNESS_PUSH")
    elif low_end_risk > 0.80 and float(stereo.get("low_end_stereo_risk", 0.0)) > 0.60:
        action = "mix_revision_required"
        selected_profile = "skip_premaster"
        draft_required = False
        reason_codes.append("LOW_END_TRANSLATION_REQUIRES_MIX_REVISION")
    elif requested_mode == "loud_but_safe_premaster":
        if analysis.get("premaster_risk") == "low" and max_artifact < 0.38 and limiter_pressure < 0.35 and vocal_forwardness >= 0.32:
            action = "loud_but_safe_premaster"
            selected_profile = "loud_but_safe_premaster"
            reason_codes.append("LOW_RISK_SOURCE_ALLOWS_LIMITED_LOUD_DRAFT")
        else:
            action = "safe_streaming_premaster"
            selected_profile = "safe_streaming_premaster"
            reason_codes.append("LOUD_REQUEST_DOWNGRADED_TO_SAFE_STREAMING")
            warnings.append("loud target rejected until A/B proves no vocal or artifact damage")
    elif requested_mode in {"safety_only_premaster", "already_mastered_safety", "safe_streaming_premaster"}:
        action = requested_mode
        selected_profile = requested_mode
        reason_codes.append("REQUESTED_CONSERVATIVE_MODE")
    else:
        action = "safe_streaming_premaster"
        selected_profile = "safe_streaming_premaster"
        reason_codes.append("DEFAULT_SAFE_STREAMING")

    if mono_risk > 0.55:
        reason_codes.append("NO_MASTER_WIDENING_MONO_RISK")
        warnings.append("master widening blocked; mono compatibility risk is elevated")
    if low_end_risk > 0.65:
        reason_codes.append("LOW_END_TRANSLATION_MANUAL_CHECK")
    if max_artifact > 0.45:
        reason_codes.append("AI_ARTIFACT_GUARD_ACTIVE")
    if target_lufs is not None and target_lufs > -11.0:
        warnings.append("requested target LUFS is too loud for this safety layer and will be capped")

    if action in {"skip_premaster", "mix_revision_required", "manual_review_required"}:
        draft_required = False

    return {
        "schema": "automix-premaster-policy-v1",
        "project_name": analysis.get("project_name"),
        "premaster_action": action,
        "selected_profile": selected_profile,
        "draft_required": draft_required,
        "draft_created": False,
        "draft_bus_or_track": "PROJECT_PREMASTER_DRAFT",
        "requires_ab_evaluation": draft_required,
        "original_master_must_remain_untouched": True,
        "requested_mode": requested_mode,
        "requested_target_lufs": target_lufs,
        "reason_codes": sorted(set(reason_codes)),
        "warnings": sorted(set(warnings)),
    }


def build_premaster_chain_plan(
    analysis: dict[str, Any],
    decision: dict[str, Any] | None = None,
    adapter_status: dict[str, Any] | None = None,
    output_dir: Path | None = None,
    target_lufs: float | None = None,
) -> dict[str, Any]:
    decision = decision or evaluate_premaster_policy(analysis, target_lufs=target_lufs)
    profile = resolve_premaster_profile(decision["premaster_action"], analysis, adapter_status or {}, requested_target_lufs=target_lufs)
    chain = profile["plugin_chain"]
    safe_chain = all(item.get("safe_to_apply", False) for item in chain) if chain else False
    requires_discovery = any(item.get("requires_parameter_discovery", False) for item in chain)
    return {
        "schema": "automix-premaster-chain-plan-v1",
        "project_name": analysis.get("project_name"),
        "source_mix_path": analysis.get("source_mix_path"),
        "input_stage": analysis.get("input_stage"),
        "premaster_stage": "post_mix_safety_layer",
        "premaster_action": decision["premaster_action"],
        "selected_profile": profile["profile"],
        "loudness_profile": analysis.get("loudness_profile", {}),
        "ai_artifact_risk_profile": analysis.get("ai_artifact_risk_profile", {}),
        "vocal_preservation_profile": analysis.get("vocal_preservation_profile", {}),
        "translation_profile": analysis.get("translation_profile", {}),
        "plugin_chain": chain,
        "semantic_settings": profile["settings"],
        "semantic_controls_written": profile["semantic_controls_to_write"],
        "semantic_controls_skipped": profile["semantic_controls_skipped"],
        "rollback_required": True,
        "ab_eval_required": decision.get("requires_ab_evaluation", False),
        "draft_only": True,
        "apply_to": "premaster_draft_bus_only",
        "original_master_must_remain_untouched": True,
        "modifies_original_master": False,
        "contains_pitch_correction": False,
        "contains_master_limiter_on_original": False,
        "contains_master_widening": False,
        "no_fixed_parameter_indexes": True,
        "requires_parameter_discovery": requires_discovery,
        "safe_to_apply": bool(decision.get("draft_required") and safe_chain and not requires_discovery),
        "output_dir": str(output_dir) if output_dir else None,
        "reason_codes": decision.get("reason_codes", []),
        "warnings": sorted(set(decision.get("warnings", []) + profile.get("warnings", []))),
    }


def build_premaster_rollback_metadata(
    *,
    project_name: str,
    original_master_snapshot: dict[str, Any] | None,
    draft_tracks: list[str] | None,
    chain_plan: Path | str,
    analysis_report: Path | str,
    created_at: str,
) -> dict[str, Any]:
    return {
        "schema": "automix-premaster-rollback-v1",
        "created_at": created_at,
        "project_name": project_name,
        "original_master_snapshot": original_master_snapshot or {},
        "draft_tracks": draft_tracks or [],
        "plugins_inserted": [],
        "parameters_written": [],
        "routing_changes": [],
        "chain_plan": str(chain_plan),
        "analysis_report": str(analysis_report),
        "safe_to_delete_draft": True,
        "original_master_untouched": True,
        "contains_pitch_correction": False,
        "contains_master_limiter_on_original": False,
    }


def assert_original_master_unmodified_for_premaster(before: dict[str, Any], after: dict[str, Any]) -> None:
    keys = (
        "master_fx_count",
        "master_volume",
        "master_pan",
        "track_count",
        "routing_count",
        "media_checksum",
        "project_path",
    )
    for key in keys:
        if before.get(key) != after.get(key):
            raise AssertionError(f"original master/project changed unexpectedly: {key}")


def final_recommendation(decision: dict[str, Any], eval_metrics: dict[str, Any] | None = None) -> str:
    action = decision.get("premaster_action")
    if action == "mix_revision_required":
        return "mix_revision_required"
    if action in {"skip_premaster", "manual_review_required"}:
        return "no_premaster_applied"
    if not eval_metrics:
        return "manual_review_required"
    if eval_metrics.get("evaluation_passed"):
        return "accept_light_premaster"
    return "reject_premaster_or_reduce_processing"


def write_premaster_report(
    output_dir: Path,
    analysis: dict[str, Any],
    decision: dict[str, Any],
    chain_plan: dict[str, Any],
    eval_metrics: dict[str, Any] | None = None,
    translation_check: dict[str, Any] | None = None,
    iteration_history: dict[str, Any] | None = None,
) -> Path:
    eval_metrics = eval_metrics or {}
    translation_check = translation_check or build_translation_check(analysis, eval_metrics)
    iteration_history = iteration_history or {"iterations": []}
    path = output_dir / "eval_reports" / "project_premaster_report.md"
    final = final_recommendation(decision, eval_metrics)
    loud = analysis.get("loudness_profile", {})
    artifact = analysis.get("ai_artifact_risk_profile", {})
    vocal = analysis.get("vocal_preservation_profile", {})
    stereo = analysis.get("stereo_profile", {})
    lines = [
        "# Premaster Safety Report",
        "",
        "## Summary",
        "",
        f"- Final recommendation: `{final}`",
        f"- Premaster action: `{decision.get('premaster_action')}`",
        f"- Selected profile: `{chain_plan.get('selected_profile')}`",
        f"- Draft required: `{decision.get('draft_required')}`",
        "- Original master untouched: `true`",
        "- Pitch correction added: `false`",
        "- Master widening added: `false`",
        "",
        "## Source Metrics",
        "",
        f"- integrated_lufs: `{loud.get('integrated_lufs')}`",
        f"- true_peak_dbTP: `{loud.get('true_peak_dbTP')}`",
        f"- lra: `{loud.get('lra')}`",
        f"- crest_factor: `{loud.get('crest_factor')}`",
        f"- limiter_pressure_risk: `{loud.get('limiter_pressure_risk')}`",
        f"- max_ai_artifact_risk: `{_max_value(artifact)}`",
        f"- vocal_forwardness_score: `{vocal.get('vocal_forwardness_score')}`",
        f"- mono_compatibility_risk: `{stereo.get('mono_compatibility_risk')}`",
        "",
        "## Chain Plan",
        "",
        f"- semantic settings: `{json.dumps(chain_plan.get('semantic_settings', {}), sort_keys=True)}`",
        f"- plugin chain: `{json.dumps(chain_plan.get('plugin_chain', []), sort_keys=True)}`",
        f"- controls written: `{json.dumps(chain_plan.get('semantic_controls_written', {}), sort_keys=True)}`",
        f"- controls skipped: `{json.dumps(chain_plan.get('semantic_controls_skipped', {}), sort_keys=True)}`",
        f"- safe_to_apply: `{chain_plan.get('safe_to_apply')}`",
        f"- warnings: `{', '.join(chain_plan.get('warnings', [])) or 'none'}`",
        "",
        "## A/B Evaluation",
        "",
        f"- renders created: `{json.dumps(eval_metrics.get('renders_created', {}), sort_keys=True)}`",
        f"- loudness results: `{json.dumps(eval_metrics.get('loudness_results', {}), sort_keys=True)}`",
        f"- improvement scores: `{json.dumps(eval_metrics.get('improvement_scores', {}), sort_keys=True)}`",
        f"- damage scores: `{json.dumps(eval_metrics.get('damage_scores', {}), sort_keys=True)}`",
        f"- evaluation passed: `{eval_metrics.get('evaluation_passed', False)}`",
        f"- eval warnings: `{', '.join(eval_metrics.get('warnings', [])) or 'none'}`",
        "",
        "## Translation Check",
        "",
        f"- status: `{translation_check.get('recommended_action')}`",
        f"- warnings: `{', '.join(translation_check.get('warnings', [])) or 'none'}`",
        "",
        "## Iteration History",
        "",
    ]
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
            "- Is the premaster only slightly more controlled, not simply louder?",
            "- Did the vocal stay forward without added sibilance?",
            "- Did consonants, air, and transients survive?",
            "- Did kick and bass impact survive?",
            "- Did reverb or delay tails avoid pumping?",
            "- Does mono fold-down keep the vocal and low end intact?",
            "- Does the difference file contain mostly level/control changes, not musical damage?",
            "",
            "## Final Recommendation",
            "",
            f"`{final}`",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_premaster_artifacts(
    output_dir: Path,
    analysis: dict[str, Any],
    decision: dict[str, Any],
    chain_plan: dict[str, Any],
    eval_metrics: dict[str, Any] | None = None,
    translation_check: dict[str, Any] | None = None,
    iteration_history: dict[str, Any] | None = None,
) -> dict[str, Path]:
    paths = {
        "analysis": output_dir / "analysis_reports" / "project_premaster_safety_analysis.json",
        "chain_plan": output_dir / "chain_plans" / "project_premaster_chain_plan.json",
        "rollback": output_dir / "rollback" / "project_premaster_rollback.json",
        "eval_metrics": output_dir / "eval_reports" / "project_premaster_eval_metrics.json",
        "translation_check": output_dir / "eval_reports" / "project_translation_check.json",
        "iteration_history": output_dir / "eval_reports" / "project_premaster_iteration_history.json",
        "report": output_dir / "eval_reports" / "project_premaster_report.md",
    }
    eval_metrics = eval_metrics or missing_premaster_eval_metrics()
    translation_check = translation_check or build_translation_check(analysis, eval_metrics)
    if iteration_history is None:
        if decision.get("draft_required"):
            iteration_history = build_premaster_iteration_history(chain_plan.get("semantic_settings", {}), [eval_metrics])
        else:
            iteration_history = {
                "schema": "automix-premaster-iteration-history-v1",
                "max_iterations": 3,
                "iterations": [],
                "final_decision": decision.get("premaster_action", "manual_review_required"),
                "never_intensify_loudness_after_damage": True,
            }
    rollback = build_premaster_rollback_metadata(
        project_name=str(analysis.get("project_name", "project")),
        original_master_snapshot={
            "source_mix_path": analysis.get("source_mix_path"),
            "original_master_must_remain_untouched": True,
        },
        draft_tracks=[],
        chain_plan=paths["chain_plan"],
        analysis_report=paths["analysis"],
        created_at=analysis.get("scan_date_utc", ""),
    )
    write_json(paths["analysis"], analysis)
    write_json(paths["chain_plan"], chain_plan)
    write_json(paths["rollback"], rollback)
    write_json(paths["eval_metrics"], eval_metrics)
    write_json(paths["translation_check"], translation_check)
    write_json(paths["iteration_history"], iteration_history)
    write_premaster_report(output_dir, analysis, decision, chain_plan, eval_metrics, translation_check, iteration_history)
    return paths
