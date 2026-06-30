from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.orchestrator.open_risk_register import build_open_risk_register
from automix.orchestrator.risk_root_cause_rollup import build_risk_root_cause_rollup
from automix.plugins.plugin_adapter_schema import now_utc, write_json


RISK_REMEDIATION_SCHEMA = "automix-risk-remediation-plan-v1"

PLAN_REL_PATH = Path("eval_reports/risk_remediation_plan.json")
PLAN_REPORT_REL_PATH = Path("eval_reports/risk_remediation_plan.md")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _risk_matches(risk: dict[str, Any], *needles: str) -> bool:
    text = " ".join(str(risk.get(key, "")) for key in ("code", "summary", "category", "recommended_next_action")).lower()
    return any(needle.lower() in text for needle in needles)


def _select_risks(risks: list[dict[str, Any]], *needles: str) -> list[dict[str, Any]]:
    return [risk for risk in risks if _risk_matches(risk, *needles)]


def _risk_ids(risks: list[dict[str, Any]]) -> list[str]:
    return sorted({str(risk.get("risk_id")) for risk in risks if risk.get("risk_id")})


def _risk_codes(risks: list[dict[str, Any]]) -> list[str]:
    return sorted({str(risk.get("code")) for risk in risks if risk.get("code")})


def _action(
    *,
    action_id: str,
    phase_order: int,
    phase: str,
    title: str,
    risks: list[dict[str, Any]],
    recommended_commands: list[str],
    evidence_to_collect: list[str],
    acceptance_criteria: list[str],
    prerequisites: list[str] | None = None,
    disallowed_actions: list[str] | None = None,
    requires_human_review: bool = True,
    dry_run_only: bool = True,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "phase_order": phase_order,
        "phase": phase,
        "title": title,
        "source_risk_ids": _risk_ids(risks),
        "target_risk_codes": _risk_codes(risks),
        "prerequisites": prerequisites or [],
        "recommended_commands": recommended_commands,
        "evidence_to_collect": evidence_to_collect,
        "acceptance_criteria": acceptance_criteria,
        "requires_human_review": bool(requires_human_review),
        "dry_run_only": bool(dry_run_only),
        "destructive": False,
        "disallowed_actions": disallowed_actions or [],
        "notes": notes or [],
    }


def _plugin_action(risks: list[dict[str, Any]]) -> dict[str, Any]:
    return _action(
        action_id="validate_plugin_mappings_before_drafts",
        phase_order=10,
        phase="plugin_safety",
        title="Validate or disable unsafe plugin mappings before any draft processing",
        risks=risks,
        prerequisites=["REAPER/plugin inventory must be available or the run stays report-only"],
        recommended_commands=[
            "python3 scripts/run_plugin_validation_preflight.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_semantic_validation_gate.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_validation_action_plan.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_availability_resolution_plan.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_availability_operator_decision_package.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_availability_operator_decision_firewall_gate.py --project-name project --output-dir automix --require-passed",
            "python3 scripts/run_plugin_availability_decision_gate.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_semantic_validation_collection_plan.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_semantic_validation_queue.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_semantic_validation_runtime_collection_package.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_semantic_validation_runtime_collector_package.py --project-name project --output-dir automix",
            "python3 scripts/run_reaper_runtime_collector_safety_audit.py --project-name project --output-dir automix --require-passed",
            "python3 scripts/run_reaper_runtime_collection_operator_readiness_gate.py --project-name project --output-dir automix --require-partial-ready",
            "python3 scripts/run_plugin_semantic_validation_runtime_handoff_packet_gate.py --project-name project --output-dir automix --require-partial-ready",
            "python3 scripts/run_plugin_semantic_validation_runtime_observation_gate.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_semantic_validation_runtime_observation_provenance_gate.py --project-name project --output-dir automix --require-packet-ready",
            "python3 scripts/run_plugin_semantic_validation_runtime_report_authoring_package.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_semantic_validation_runtime_report_authoring_gate.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_semantic_validation_runtime_evidence_gate.py --project-name project --output-dir automix",
            "python3 scripts/run_plugin_intelligence_audit.py --scan --report --dry-run --output-dir automix",
            "python3 scripts/run_processing_policy_audit.py --project-name project --output-dir automix",
            "python3 scripts/run_open_risk_register.py --project-name project --output-dir automix",
        ],
        evidence_to_collect=[
            "automix/analysis_reports/plugin_inventory_audit.json",
            "automix/eval_reports/plugin_validation_preflight.json",
            "automix/eval_reports/plugin_semantic_validation_gate.json",
            "automix/eval_reports/plugin_semantic_validation_collection_plan.json",
            "automix/eval_reports/plugin_validation_action_plan.json",
            "automix/eval_reports/plugin_availability_resolution_plan.json",
            "automix/eval_reports/plugin_availability_operator_decision_package.json",
            "automix/eval_reports/plugin_availability_operator_decision_firewall_gate.json",
            "automix/eval_reports/plugin_availability_operator_decision_firewall_gate.md",
            "automix/review/plugin_availability_operator_decision_checklist.md",
            "automix/review/plugin_availability_disable_manifest_candidate.json",
            "automix/eval_reports/plugin_availability_decision_gate.json",
            "automix/review/plugin_semantic_validation_collection_request.md",
            "automix/review/plugin_semantic_validation_collection_manifest_template.json",
            "automix/eval_reports/plugin_semantic_validation_queue.json",
            "automix/review/plugin_semantic_validation_queue_request.md",
            "automix/review/plugin_semantic_validation_runtime_manifest_template.json",
            "automix/eval_reports/plugin_semantic_validation_runtime_collection_package.json",
            "automix/review/plugin_semantic_validation_runtime_collection_checklist.md",
            "automix/review/plugin_semantic_validation_runtime_manifest_candidate.json",
            "automix/review/plugin_semantic_validation_runtime_report_templates/",
            "automix/eval_reports/plugin_semantic_validation_runtime_collector_package.json",
            "automix/eval_reports/reaper_runtime_collector_safety_audit.json",
            "automix/eval_reports/reaper_runtime_collection_operator_readiness.json",
            "automix/eval_reports/plugin_semantic_validation_runtime_handoff_packet_gate.json",
            "automix/eval_reports/plugin_semantic_validation_runtime_handoff_packet_gate.md",
            "automix/reaper_scripts/collect_plugin_semantic_validation_runtime.lua",
            "automix/reaper_scripts/plugin_semantic_validation_runtime_queue.json",
            "automix/eval_reports/reaper_runtime_collector_safety_audit.md",
            "automix/review/plugin_semantic_validation_runtime_collector_operator_runbook.md",
            "automix/eval_reports/plugin_semantic_validation_runtime_observation_gate.json",
            "automix/eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json",
            "automix/eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.md",
            "automix/review/plugin_semantic_validation_runtime_observation_request.md",
            "automix/review/plugin_semantic_validation_runtime_report_authoring_request.md",
            "automix/eval_reports/plugin_semantic_validation_runtime_report_authoring_package.json",
            "automix/review/plugin_semantic_validation_runtime_report_authoring_checklist.md",
            "automix/review/plugin_semantic_validation_runtime_report_authoring_templates/",
            "automix/eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.json",
            "automix/review/plugin_semantic_validation_runtime_report_authoring_candidates/",
            "automix/review/plugin_semantic_validation_runtime_report_promotion_checklist.md",
            "automix/review/plugin_semantic_validation_runtime_manifest_candidate_from_authoring.json",
            "automix/eval_reports/plugin_semantic_validation_runtime_evidence_gate.json",
            "automix/review/plugin_semantic_validation_runtime_evidence_request.md",
            "automix/review/plugin_semantic_validation_runtime_manifest.json",
            "automix/review/plugin_validation_action_request.md",
            "automix/review/plugin_availability_resolution_request.md",
            "automix/review/plugin_availability_decision_request.md",
            "automix/review/plugin_availability_disable_manifest.json",
            "automix/review/plugin_availability_disable_manifest_template.json",
            "automix/review/plugin_semantic_validation_manifest_template.json",
            "automix/eval_reports/plugin_capability_report.md",
            "automix/eval_reports/real_project_plugin_readiness.json",
            "automix/export/plugin_mapping_summary.md",
        ],
        acceptance_criteria=[
            "safe_draft_plugin_ready is true or unsafe plugins are explicitly disabled",
            "plugin_validation_preflight separates availability evidence from semantic write safety",
            "plugin_semantic_validation_gate requires passed no-fake-success validation reports with write-safe controls",
            "plugin_semantic_validation_collection_plan lists exact REAPER-observed reports to collect or confirms no open jobs",
            "plugin_semantic_validation_queue packages collectable REAPER-observed validation jobs without granting write safety",
            "plugin_semantic_validation_runtime_collection_package prepares report templates and a manifest candidate without creating passing validation evidence",
            "plugin_semantic_validation_runtime_collector_package prepares a REAPER-side raw observation collector without creating passing validation reports",
            "reaper_runtime_collector_safety_audit rejects generated collectors with parameter-write, save, render, or broad mutation APIs before operator runtime collection",
            "reaper_runtime_collection_operator_readiness separates partial collectable-job readiness from complete readiness blocked by unavailable plugin decisions",
            "plugin_semantic_validation_runtime_handoff_packet_gate verifies the operator packet files, templates, collector payload, runbook, local QC, and safety audit before running REAPER collection",
            "plugin_semantic_validation_runtime_observation_gate validates raw collector observations before manual report authoring without granting write safety",
            "plugin_semantic_validation_runtime_observation_provenance_gate verifies observation freshness, queue lineage, script version, and optional artifact hashes before manual report authoring",
            "plugin_semantic_validation_runtime_report_authoring_package prepares review-only validation report templates from accepted raw observations without writing analysis reports or granting write safety",
            "plugin_semantic_validation_runtime_report_authoring_gate validates review-only authored candidates before operator promotion without writing analysis reports or granting write safety",
            "plugin_semantic_validation_runtime_evidence_gate confirms queued REAPER-observed reports exist and pass before semantic gate rerun/write safety",
            "plugin_validation_action_plan lists no blocker plugin actions before automatic parameter writes",
            "plugin_availability_resolution_plan records install, disable, or manual-review decisions for unavailable plugins",
            "plugin_availability_operator_decision_package prepares candidate operator decisions without creating accepted evidence",
            "plugin_availability_operator_decision_firewall_gate verifies candidate manifests cannot count as accepted operator evidence",
            "plugin_availability_decision_gate is ready before unavailable plugins are treated as disabled for automatic drafts",
            "semantic controls have confidence, safe min/max bounds, and no fixed uncertain parameter indexes",
            "Suno/AI first-slot rescue plugin is traced before any final claim about that plugin",
        ],
        disallowed_actions=[
            "write low-confidence plugin parameters",
            "hard-code uncertain parameter indexes",
            "treat fallback EQ/dynamics as proof that a developed rescue plugin loaded",
        ],
        notes=["Stock or JSFX fallback can support review planning only when semantic mappings are validated."],
    )


def _source_action(risks: list[dict[str, Any]]) -> dict[str, Any]:
    track_names = sorted(
        {
            str((risk.get("context") or {}).get("track_name"))
            for risk in risks
            if (risk.get("context") or {}).get("track_name")
        }
    )
    return _action(
        action_id="resolve_source_and_stem_blockers",
        phase_order=20,
        phase="source_intake",
        title="Resolve stem/full-mix source blockers before vocal recovery, pitch, placement, or mastering",
        risks=risks,
        prerequisites=["Do not use full-mix or reference tracks as automatic processing targets"],
        recommended_commands=[
            "python3 scripts/run_source_handoff_readiness.py --project-name project --output-dir automix",
            "python3 scripts/run_source_acceptance_gate.py --project-name project --output-dir automix",
            "python3 scripts/run_real_project_scan_only.py --project \"/path/to/project.rpp\" --target-profile digicore_hyperpop_hiphop_vocal_forward --check-prompt41 --strict-read-only --dry-run",
            "python3 scripts/run_intent_classifier.py --project-name project --output-dir automix --target-profile digicore_hyperpop_hiphop_vocal_forward",
            "python3 scripts/run_open_risk_register.py --project-name project --output-dir automix",
        ],
        evidence_to_collect=[
            "automix/eval_reports/source_handoff_readiness.json",
            "automix/eval_reports/source_acceptance_gate.json",
            "automix/review/source_acceptance_manifest_template.json",
            "automix/review/source_stem_handoff_request.md",
            "isolated vocal/instrument/stem files or a note that manual review is required",
            "automix/eval_reports/real_project_source_safety_map.json",
            "automix/analysis_reports/real_project_track_audit.json",
            "updated intent_classification.json after stems are available",
        ],
        acceptance_criteria=[
            "source_handoff_readiness distinguishes current file presence from accepted export source evidence",
            "source_acceptance_gate records explicit human acceptance before a source is used for final export packaging",
            "full_mix_unsafe_tracks is zero for automatic vocal/pitch processing targets",
            "stem_required_tracks is zero or every required stem has an explicit manual-review plan",
            "reference/full-mix tracks remain muted by default and outside PREMASTER BUS",
        ],
        disallowed_actions=[
            "pitch-correct the full mix",
            "use reference audio as premaster source",
            "apply vocal rescue to source tracks classified as unsafe full mix",
        ],
        notes=[f"High-risk tracks currently named: {', '.join(track_names)}"] if track_names else [],
    )


def _intent_action(risks: list[dict[str, Any]]) -> dict[str, Any]:
    return _action(
        action_id="rerun_intent_after_safety_evidence",
        phase_order=30,
        phase="intent_routing",
        title="Rerun intent classification only after plugin and source evidence improve",
        risks=risks,
        prerequisites=["Plugin readiness and source/stem blockers should be resolved or explicitly waived for manual review"],
        recommended_commands=[
            "python3 scripts/run_artifact_evidence_gate.py --project-name project --output-dir automix",
            "python3 scripts/run_artifact_signal_audit.py --project-name project --output-dir automix",
            "python3 scripts/run_intent_classifier.py --project-name project --output-dir automix --target-profile digicore_hyperpop_hiphop_vocal_forward",
            "python3 scripts/run_open_risk_register.py --project-name project --output-dir automix",
        ],
        evidence_to_collect=[
            "automix/eval_reports/artifact_signal_audit.json",
            "automix/eval_reports/artifact_evidence_gate.json",
            "automix/review/artifact_evidence_manifest_template.json",
            "automix/eval_reports/intent_classification.json",
            "safe_draft_intents list",
            "safe_next_mode and per-intent risk scores",
        ],
        acceptance_criteria=[
            "artifact_signal_audit establishes source, metric, or user-feedback signal before artifact-focused work",
            "artifact_evidence_gate separates report-only metrics from measured render/QC evidence",
            "safe_next_mode is no longer validate_plugin_mappings unless that remains the safest route",
            "any safe draft intent is dry-run only and carries human_review_required",
            "aggressive_creative_enhancement remains disabled unless explicitly requested and preview-reviewed",
        ],
        disallowed_actions=[
            "force aggressive creative enhancement to clear a blocker",
            "mark artifact_signal_not_established as resolved without source or feedback evidence",
        ],
    )


def _feedback_action(risks: list[dict[str, Any]]) -> dict[str, Any]:
    return _action(
        action_id="record_or_resolve_user_feedback_evidence",
        phase_order=40,
        phase="feedback",
        title="Create feedback memory only when user listening feedback exists, then resolve with evidence",
        risks=risks,
        prerequisites=["Actual user listening feedback text is needed before creating a real feedback entry"],
        recommended_commands=[
            "python3 scripts/run_feedback_revision_loop.py --output-dir automix --project-name project --pass-id v01 --track-name \"Lead Vocal\" --feedback \"<user feedback here>\"",
            "python3 scripts/run_open_risk_register.py --project-name project --output-dir automix",
        ],
        evidence_to_collect=[
            "automix/review/user_feedback_revision_memory.json",
            "automix/eval_reports/user_feedback_qc_integration.json",
            "measured QC evidence path",
            "loudness-matched A/B review evidence",
        ],
        acceptance_criteria=[
            "feedback actions are dry-run only until evidence is available",
            "resolution records measured_qc_passed, loudness_matched_ab_reviewed, and human_reviewed",
            "remaining risks are explicitly documented",
        ],
        disallowed_actions=[
            "invent user feedback",
            "mark feedback resolved without existing evidence files",
            "do not claim total artifact removal from feedback resolution",
        ],
    )


def _export_action(risks: list[dict[str, Any]]) -> dict[str, Any]:
    return _action(
        action_id="build_reviewed_export_source_before_delivery",
        phase_order=50,
        phase="final_export",
        title="Create or select an accepted reviewed source before final export",
        risks=risks,
        prerequisites=[
            "Plugin, source, intent, QC, A/B, rollback, and human review gates should be clear enough for a reviewed draft",
            "Unsafe override may create review copies only",
        ],
        recommended_commands=[
            "python3 scripts/run_recovery_review_gate.py --project \"/path/to/project.rpp\" --generate-form",
            "python3 scripts/run_approval_export_readiness.py --project-name project --output-dir automix",
            "python3 scripts/run_final_export_packager.py --project \"/path/to/project.rpp\" --source-stage accepted_premaster_draft --source-audio /path/to/accepted.wav --original-mix /path/to/original.wav --profile professional_master_delivery --render --make-ab-preview --qc --zip",
            "python3 scripts/run_final_render_evidence_gate.py --project-name project --output-dir automix --require-ready",
            "python3 scripts/run_final_qc_evidence_gate.py --project-name project --output-dir automix --require-ready",
            "python3 scripts/run_ab_preview_evidence_gate.py --project-name project --output-dir automix --require-ready",
            "python3 scripts/run_final_approval_evidence_gate.py --project-name project --output-dir automix --require-ready",
            "python3 scripts/run_rollback_evidence_gate.py --project-name project --output-dir automix --require-ready",
            "python3 scripts/run_deliverable_package_evidence_gate.py --project-name project --output-dir automix --require-ready",
            "python3 scripts/run_final_delivery_consistency_gate.py --project-name project --output-dir automix --require-ready",
            "python3 scripts/run_professional_readiness_audit.py --project-name project --output-dir automix --final-delivery-requested",
            "python3 scripts/run_risk_root_cause_rollup.py --project-name project --output-dir automix",
        ],
        evidence_to_collect=[
            "accepted reviewed draft source",
            "automix/eval_reports/approval_export_readiness.json",
            "automix/review/final_approval_request.md",
            "automix/export/final_export_state.json",
            "automix/export/final_render_manifest.json",
            "automix/eval_reports/final_render_evidence_gate.json",
            "automix/review/final_render_evidence_manifest_template.json",
            "automix/eval_reports/final_qc_metrics.json",
            "automix/eval_reports/final_qc_evidence_gate.json",
            "automix/review/final_qc_evidence_manifest_template.json",
            "automix/eval_reports/final_ab_preview_manifest.json",
            "automix/eval_reports/ab_preview_evidence_gate.json",
            "automix/review/ab_preview_review_manifest_template.json",
            "automix/review/final_human_approval.json",
            "automix/eval_reports/final_approval_evidence_gate.json",
            "automix/review/final_approval_evidence_manifest_template.json",
            "automix/export/deliverable_package_manifest.json",
            "automix/eval_reports/deliverable_package_evidence_gate.json",
            "automix/review/deliverable_package_evidence_manifest_template.json",
            "automix/eval_reports/final_delivery_consistency_gate.json",
            "automix/review/final_delivery_consistency_manifest_template.json",
            "automix/eval_reports/risk_root_cause_rollup.json",
            "automix/eval_reports/final_qc_metrics.json",
            "automix/review/final_human_approval.json",
            "automix/rollback/global_rollback_registry.json",
            "automix/eval_reports/rollback_evidence_gate.json",
            "automix/review/rollback_evidence_manifest_template.json",
        ],
        acceptance_criteria=[
            "final_export_state.safe_to_export is true",
            "approval_export_readiness has no blockers except final_human_approval_missing before requesting approval",
            "primary WAV render exists and is nonzero",
            "final_render_evidence_gate confirms the primary WAV is a real non-diagnostic render",
            "final_qc_evidence_gate confirms final QC metrics pass and match the primary WAV render evidence",
            "A/B preview is created with measured loudness-match metrics and source/render links",
            "rollback_evidence_gate confirms original protection and rollback file integrity",
            "final_approval_evidence_gate confirms the approval record references matched-loudness A/B and final QC evidence",
            "deliverable_package_evidence_gate confirms the ZIP opens cleanly, package size matches, and required evidence files are present",
            "final_delivery_consistency_gate confirms render, QC, A/B, approval, and package reports point to the same final audio and preview evidence",
            "human approval and warning acknowledgment are recorded",
            "open risk register has no delivery blockers",
            "risk root-cause rollup has no blocker root causes",
        ],
        disallowed_actions=[
            "name a diagnostic or unsafe review copy FINAL_SAFE",
            "deliver MP3 as the only final format",
            "skip rollback validation or human approval",
        ],
    )


def _verification_action(risks: list[dict[str, Any]]) -> dict[str, Any]:
    return _action(
        action_id="rerun_professional_audits_after_remediation",
        phase_order=60,
        phase="verification",
        title="Rerun the professional evidence audits after each remediation pass",
        risks=risks,
        requires_human_review=False,
        recommended_commands=[
            "python3 scripts/run_fixture_coverage_audit.py --project-name project --output-dir automix",
            "python3 scripts/run_requirements_traceability_audit.py --project-name project --output-dir automix",
            "python3 scripts/run_open_risk_register.py --project-name project --output-dir automix",
            "python3 scripts/run_risk_root_cause_rollup.py --project-name project --output-dir automix",
            "python3 scripts/run_professional_readiness_audit.py --project-name project --output-dir automix",
        ],
        evidence_to_collect=[
            "automix/eval_reports/fixture_coverage_audit.json",
            "automix/eval_reports/requirements_traceability_audit.json",
            "automix/eval_reports/open_risk_register.json",
            "automix/eval_reports/risk_root_cause_rollup.json",
            "automix/eval_reports/professional_readiness_audit.json",
        ],
        acceptance_criteria=[
            "traceability blockers remain empty",
            "risk register blockers trend down or are intentionally carried as manual-review risks",
            "professional readiness diagnostic mode has no unexpected blockers",
        ],
        disallowed_actions=["treat green static audits as proof of listening approval"],
        notes=["This verification is report-level evidence only."],
    )


def _build_actions(risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    plugin = _select_risks(
        risks,
        "validated_plugin_mapping",
        "safe_draft_plugin_ready_false",
        "missing_or_unsafe_plugin_mapping",
        "no_validated_safe_plugin_adapters",
        "plugin_semantic_validation",
        "plugin_validation_preflight",
        "semantic_parameter_validation_required",
        "validation_report_missing",
        "semantic_validation_collection",
        "semantic_validation_queue",
        "semantic_validation_runtime",
        "plugin_availability_decision",
    )
    source = _select_risks(risks, "isolated_stems_required", "stems_not_ready", "stem_required", "full_mix_unsafe", "high_risk_track")
    intent = _select_risks(risks, "safe_next_mode", "no_safe_draft_intents", "artifact_signal_not_established", "aggressive_creative_enhancement", "explicit_rebeat", "explicit_user_approval")
    feedback = _select_risks(risks, "feedback", "feedback_revision_memory", "user_feedback_qc_integration")
    export = _select_risks(risks, "no_accepted_export_source", "final_export", "render", "approval", "final_delivery", "ab_preview", "final_qc", "qc_evidence", "matched_loudness")
    if plugin:
        actions.append(_plugin_action(plugin))
    if source:
        actions.append(_source_action(source))
    if intent:
        actions.append(_intent_action(intent))
    if feedback:
        actions.append(_feedback_action(feedback))
    if export:
        actions.append(_export_action(export))
    actions.append(_verification_action(risks))
    return sorted(actions, key=lambda item: item["phase_order"])


def build_risk_remediation_plan(
    *,
    project_name: str,
    output_dir: Path,
    register: dict[str, Any] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    register = register or _load_json(output_dir / "eval_reports" / "open_risk_register.json")
    if not register:
        register = build_open_risk_register(project_name=project_name, output_dir=output_dir)
    risks = [risk for risk in register.get("open_risks", []) if isinstance(risk, dict)]
    root_cause_rollup = build_risk_root_cause_rollup(project_name=project_name, output_dir=output_dir, register=register)
    actions = _build_actions(risks)
    blockers = [
        "risk_remediation_plan_has_no_actions"
    ] if risks and not actions else []
    plan = {
        "schema": RISK_REMEDIATION_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "source_register": str(output_dir / "eval_reports" / "open_risk_register.json"),
        "source_root_cause_rollup": str(output_dir / "eval_reports" / "risk_root_cause_rollup.json"),
        "open_risk_counts": register.get("risk_counts", {}),
        "open_risk_total": len(risks),
        "root_cause_total": int(root_cause_rollup.get("root_cause_total", 0) or 0),
        "next_root_cause": root_cause_rollup.get("next_root_cause", {}),
        "actions": actions,
        "actions_total": len(actions),
        "status": "no_open_risks_to_remediate" if not risks else "remediation_plan_ready",
        "dry_run_only": True,
        "destructive": False,
        "requires_human_review": any(action.get("requires_human_review") for action in actions),
        "blockers": blockers,
        "warnings": [
            "remediation_plan_is_not_audio_approval",
            "commands_with_placeholder_paths_require_operator_substitution",
        ],
        "limits": [
            "This plan sequences safe next actions. It does not apply FX or prove audio improvement.",
            "Human listening review is required before accepting any rendered candidate.",
        ],
    }
    target = output_path or output_dir / PLAN_REL_PATH
    write_json(target, plan)
    write_risk_remediation_report(plan, output_dir)
    return plan


def write_risk_remediation_report(plan: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Risk Remediation Plan",
        "",
        f"- Project: `{plan.get('project_name')}`",
        f"- Created UTC: `{plan.get('created_at')}`",
        f"- Status: `{plan.get('status')}`",
        f"- Open risks: `{plan.get('open_risk_total')}`",
        f"- Root causes: `{plan.get('root_cause_total')}`",
        f"- Actions: `{plan.get('actions_total')}`",
        f"- Dry-run only: `{plan.get('dry_run_only')}`",
        "",
        "This plan converts open report risks into safe next actions. It does not apply processing, approve audio, or replace human listening review.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in plan.get("blockers", [])] or ["- none"])
    next_cause = plan.get("next_root_cause", {})
    lines.extend(["", "## Next Root Cause", ""])
    if next_cause:
        lines.append(f"- `{next_cause.get('cause_id')}`: {next_cause.get('title')}")
        lines.append(f"- Recommended next action: {next_cause.get('recommended_next_action')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Actions", ""])
    if not plan.get("actions"):
        lines.append("- none")
    for action in plan.get("actions", []):
        lines.extend(
            [
                f"### {action.get('phase_order')}. {action.get('title')}",
                "",
                f"- Phase: `{action.get('phase')}`",
                f"- Risk IDs: `{action.get('source_risk_ids', [])}`",
                f"- Dry-run only: `{action.get('dry_run_only')}`",
                f"- Requires human review: `{action.get('requires_human_review')}`",
                "- Recommended commands:",
            ]
        )
        lines.extend([f"  - `{cmd}`" for cmd in action.get("recommended_commands", [])] or ["  - none"])
        lines.append("- Evidence to collect:")
        lines.extend([f"  - `{item}`" for item in action.get("evidence_to_collect", [])] or ["  - none"])
        lines.append("- Acceptance criteria:")
        lines.extend([f"  - {item}" for item in action.get("acceptance_criteria", [])] or ["  - none"])
        lines.append("- Disallowed actions:")
        lines.extend([f"  - {item}" for item in action.get("disallowed_actions", [])] or ["  - none"])
        lines.append("")
    path = Path(output_dir) / PLAN_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
