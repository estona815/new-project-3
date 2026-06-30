from __future__ import annotations

from typing import Any

from automix.orchestrator.stage_dependency_graph import APPLIED_STAGES
from automix.orchestrator.stage_status import StageStatus


SAFETY_CONTROLLER_VERSION = "automix-global-safety-controller-v1"

HARD_BLOCKERS = {
    "plugin_mapping_required_for_requested_effect",
    "original_track_modified_unexpectedly",
    "original_master_modified_unexpectedly",
    "rollback_validation_failed",
    "full_mix_detected_for_pitch_correction",
    "rejected_recovery_but_pitch_requested",
    "rejected_placement_but_premaster_requested",
    "premaster_rejected_but_final_export_requested",
    "missing_ab_render_for_applied_processing",
    "final_approval_missing",
    "qc_failure_for_final_delivery",
    "render_failure",
    "unsafe_override_without_explicit_mode",
}


def blockers_from_stage_results(stage_results: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for result in stage_results:
        stage = result.get("stage", "")
        status = result.get("status")
        if status == StageStatus.REQUIRES_PLUGIN_MAPPING.value:
            blockers.append("plugin_mapping_required_for_requested_effect")
        if status == StageStatus.REQUIRES_STEM.value:
            blockers.append("stem_required_for_requested_processing")
        if status == StageStatus.REQUIRES_APPROVAL.value:
            blockers.append("final_approval_missing")
        if status == StageStatus.FAILED.value:
            blockers.append(f"{stage}_failed")
        if status == StageStatus.BLOCKED.value:
            blockers.extend(result.get("blockers", []) or [f"{stage}_blocked"])
        blockers.extend(result.get("blockers", []))
    return sorted(set(blockers))


def applied_stages_without_ab(stage_results: list[dict[str, Any]], *, require_ab: bool) -> list[str]:
    if not require_ab:
        return []
    missing: list[str] = []
    for result in stage_results:
        stage = result.get("stage")
        if stage not in APPLIED_STAGES or result.get("status") not in {StageStatus.PASSED.value, StageStatus.PASSED_WITH_WARNINGS.value}:
            continue
        if stage == "deliverable_package":
            continue
        outputs = " ".join(result.get("outputs", []) + result.get("reports", []))
        if "ab" not in outputs.lower() and stage != "final_export":
            missing.append(stage)
    return missing


def evaluate_workflow_continuation(
    *,
    mode: str,
    stage_results: list[dict[str, Any]],
    config: dict[str, Any],
    current_stage: str | None = None,
) -> dict[str, Any]:
    blockers = blockers_from_stage_results(stage_results)
    missing_ab = applied_stages_without_ab(stage_results, require_ab=bool(config.get("require_ab_eval_for_applied_stages", True)))
    if missing_ab:
        blockers.append("missing_ab_render_for_applied_processing")
    if config.get("original_track_modified_unexpectedly"):
        blockers.append("original_track_modified_unexpectedly")
    if config.get("original_master_modified_unexpectedly"):
        blockers.append("original_master_modified_unexpectedly")

    final_requested = mode == "final_delivery" or config.get("allow_final_export")
    if final_requested and not config.get("final_approval_explicit"):
        blockers.append("final_approval_missing")
    if mode == "diagnostic_continue" and current_stage in APPLIED_STAGES:
        blockers.append("diagnostic_continue_cannot_apply_processing")

    hard = sorted(set(blockers))
    if mode == "scan_only":
        can_continue = True
        can_apply_processing = False
    elif mode == "diagnostic_continue":
        can_continue = True
        can_apply_processing = False
    elif mode == "final_delivery":
        can_continue = not hard
        can_apply_processing = not hard
    else:
        can_continue = not hard or not config.get("stop_on_safety_failure", True)
        can_apply_processing = not hard

    return {
        "schema": SAFETY_CONTROLLER_VERSION,
        "mode": mode,
        "current_stage": current_stage,
        "hard_blockers": hard,
        "can_continue": can_continue,
        "can_apply_processing": can_apply_processing,
        "analysis_only": mode in {"scan_only", "diagnostic_continue"},
    }


def global_status_from_results(mode: str, stage_results: list[dict[str, Any]], safe_to_export: bool = False) -> str:
    blockers = blockers_from_stage_results(stage_results)
    statuses = {result.get("status") for result in stage_results}
    if mode == "scan_only" and not any(status == StageStatus.FAILED.value for status in statuses):
        return "scan_complete"
    if "plugin_mapping_required_for_requested_effect" in blockers:
        return "blocked_plugin_mapping_required"
    if "stem_required_for_requested_processing" in blockers:
        return "blocked_stem_required"
    if any(status == StageStatus.REQUIRES_MANUAL_REVIEW.value for status in statuses):
        return "blocked_manual_review_required"
    if mode == "final_delivery":
        if safe_to_export and not blockers:
            return "final_delivery_created"
        return "final_delivery_failed"
    if any(result.get("stage", "").endswith("_draft") and result.get("status") in {StageStatus.PASSED.value, StageStatus.PASSED_WITH_WARNINGS.value} for result in stage_results):
        return "drafts_created_review_required"
    if blockers:
        return "blocked_safety_failure"
    return "scan_complete"


def next_actions_from_results(stage_results: list[dict[str, Any]], blockers: list[str]) -> list[str]:
    actions: list[str] = []
    if "plugin_mapping_required_for_requested_effect" in blockers:
        actions.append("Validate plugin adapter mappings before applying FX.")
    if "stem_required_for_requested_processing" in blockers:
        actions.append("Provide isolated lead vocal stem.")
    if "final_approval_missing" in blockers:
        actions.append("Approve final export and acknowledge warnings before final delivery.")
    if "missing_ab_render_for_applied_processing" in blockers:
        actions.append("Render and review A/B previews for applied stages.")
    for result in stage_results:
        action = result.get("manual_action_type")
        if action == "manual_mix_revision":
            actions.append("Perform manual mix revision before continuing.")
        elif action == "manual_mastering_required":
            actions.append("Perform manual mastering review before final delivery.")
        elif action == "review_recovery_drafts":
            actions.append("Review recovery drafts against originals before allowing placement or pitch triage.")
        elif action == "acknowledge_warnings":
            actions.append("Acknowledge warnings before final export.")
    return sorted(set(actions or ["Review generated AutoMix reports before applying processing."]))
