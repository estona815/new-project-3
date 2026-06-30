from __future__ import annotations

from typing import Any

from automix.orchestrator.stage_status import StageStatus


STAGE_ORDER = [
    "plugin_intelligence",
    "github_integration_smoke",
    "project_scan",
    "track_role_detection",
    "source_classification",
    "intent_classification",
    "vocal_recovery_analysis",
    "vocal_recovery_draft",
    "vocal_recovery_eval",
    "recovery_review_gate",
    "final_vocal_space_finish",
    "final_placement_adapter_validation",
    "pitch_triage",
    "pitch_draft",
    "pitch_eval",
    "vocal_placement_analysis",
    "vocal_placement_draft",
    "vocal_placement_eval",
    "reference_match_analysis",
    "reference_match_draft",
    "reference_match_eval",
    "premaster_analysis",
    "premaster_draft",
    "premaster_eval",
    "translation_check",
    "final_export_state_resolver",
    "final_export",
    "final_qc",
    "deliverable_package",
    "professional_readiness_audit",
]

DEPENDENCIES: dict[str, list[str]] = {
    "github_integration_smoke": ["plugin_intelligence"],
    "project_scan": ["github_integration_smoke"],
    "track_role_detection": ["project_scan"],
    "source_classification": ["track_role_detection"],
    "intent_classification": ["source_classification"],
    "vocal_recovery_analysis": ["intent_classification"],
    "vocal_recovery_draft": ["vocal_recovery_analysis"],
    "vocal_recovery_eval": ["vocal_recovery_draft"],
    "recovery_review_gate": ["vocal_recovery_eval"],
    "final_vocal_space_finish": ["recovery_review_gate"],
    "final_placement_adapter_validation": ["final_vocal_space_finish"],
    "pitch_triage": ["intent_classification"],
    "pitch_draft": ["pitch_triage"],
    "pitch_eval": ["pitch_draft"],
    "vocal_placement_analysis": ["intent_classification"],
    "vocal_placement_draft": ["vocal_placement_analysis"],
    "vocal_placement_eval": ["vocal_placement_draft"],
    "reference_match_analysis": ["intent_classification"],
    "reference_match_draft": ["reference_match_analysis"],
    "reference_match_eval": ["reference_match_draft"],
    "premaster_analysis": ["intent_classification"],
    "premaster_draft": ["premaster_analysis"],
    "premaster_eval": ["premaster_draft"],
    "translation_check": ["premaster_eval"],
    "final_export_state_resolver": ["translation_check"],
    "final_export": ["final_export_state_resolver"],
    "final_qc": ["final_export"],
    "deliverable_package": ["final_qc"],
}

APPLIED_STAGES = {
    "vocal_recovery_draft",
    "pitch_draft",
    "vocal_placement_draft",
    "reference_match_draft",
    "premaster_draft",
    "final_export",
    "deliverable_package",
}

ANALYSIS_ONLY_STAGES = set(STAGE_ORDER) - APPLIED_STAGES

BLOCKING_STATUSES = {
    StageStatus.BLOCKED.value,
    StageStatus.FAILED.value,
    StageStatus.REQUIRES_STEM.value,
    StageStatus.REQUIRES_PLUGIN_MAPPING.value,
    StageStatus.REQUIRES_APPROVAL.value,
}


def stage_index(stage: str) -> int:
    return STAGE_ORDER.index(stage)


def dependency_failures(stage: str, stage_results: dict[str, dict[str, Any]], *, diagnostic_continue: bool = False) -> list[str]:
    failures: list[str] = []
    for dep in DEPENDENCIES.get(stage, []):
        result = stage_results.get(dep)
        if not result:
            failures.append(f"{dep}_not_run")
            continue
        status = result.get("status")
        if status in BLOCKING_STATUSES and not diagnostic_continue:
            failures.append(f"{dep}_{status}")
    if stage == "pitch_triage" and "source_classification" not in stage_results:
        failures.append("pitch_triage_requires_source_classification")
    if stage == "pitch_draft":
        pitch_triage = stage_results.get("pitch_triage", {})
        if pitch_triage.get("status") in {StageStatus.BLOCKED.value, StageStatus.REQUIRES_STEM.value} and not diagnostic_continue:
            failures.append("pitch_draft_requires_pitch_safety_gate_approval")
    if stage == "premaster_draft":
        placement = stage_results.get("vocal_placement_eval") or stage_results.get("vocal_placement_draft") or {}
        if placement.get("status") == StageStatus.FAILED.value and not diagnostic_continue:
            failures.append("premaster_cannot_run_from_rejected_placement")
    if stage in {"final_export", "deliverable_package"}:
        resolver = stage_results.get("final_export_state_resolver", {})
        if resolver.get("status") in BLOCKING_STATUSES and not diagnostic_continue:
            failures.append("final_export_requires_approval_and_safe_source")
    return sorted(set(failures))


def can_run_stage(stage: str, stage_results: dict[str, dict[str, Any]], *, mode: str) -> tuple[bool, list[str]]:
    diagnostic = mode in {"diagnostic_continue", "scan_only", "real_project_scan_only"}
    failures = dependency_failures(stage, stage_results, diagnostic_continue=diagnostic)
    return not failures, failures


def reference_change_requires_premaster_rerun(reference_plan: dict[str, Any]) -> bool:
    return bool(reference_plan.get("adjustments"))
