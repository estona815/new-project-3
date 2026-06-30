from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.feedback.revision_memory import summarize_feedback_memory
from automix.orchestrator.claim_language_guard import run_claim_language_guard
from automix.plugins.plugin_adapter_schema import now_utc, write_json


PROFESSIONAL_READINESS_SCHEMA = "automix-professional-readiness-audit-v1"

REQUIRED_ROOT_DOCS = [
    "README.md",
    "QUICKSTART.md",
    "PIPELINE_ARCHITECTURE.md",
    "AUDIO_ENGINEERING_NOTES.md",
    "SUNO_AI_ARTIFACT_STRATEGY.md",
    "VOCAL_FIRST_MIXING_STRATEGY.md",
    "MASTERING_QC_STANDARD.md",
    "USER_FEEDBACK_REVISION_LOOP.md",
    "TESTING_AND_HARNESS.md",
    "PLUGIN_FALLBACKS.md",
    "TROUBLESHOOTING.md",
    "CHANGELOG.md",
]

REQUIRED_DETAIL_DOCS = [
    "docs/automix_runbook.md",
    "docs/final_export_and_delivery.md",
    "docs/user_feedback_revision_loop.md",
]

REQUIRED_SCRIPTS = [
    "scripts/run_automix_orchestrator.py",
    "scripts/run_prompt41_smoke_validation.py",
    "scripts/run_fixture_coverage_audit.py",
    "scripts/run_requirements_traceability_audit.py",
    "scripts/run_open_risk_register.py",
    "scripts/run_risk_root_cause_rollup.py",
    "scripts/run_risk_remediation_plan.py",
    "scripts/run_path_hygiene_audit.py",
    "scripts/run_ab_preview_evidence_gate.py",
    "scripts/run_final_render_evidence_gate.py",
    "scripts/run_final_qc_evidence_gate.py",
    "scripts/run_final_approval_evidence_gate.py",
    "scripts/run_deliverable_package_evidence_gate.py",
    "scripts/run_final_delivery_consistency_gate.py",
    "scripts/run_rollback_evidence_gate.py",
    "scripts/run_source_acceptance_gate.py",
    "scripts/run_artifact_evidence_gate.py",
    "scripts/run_plugin_semantic_validation_gate.py",
    "scripts/run_plugin_semantic_validation_collection_plan.py",
    "scripts/run_plugin_semantic_validation_queue.py",
    "scripts/run_plugin_semantic_validation_runtime_collection_package.py",
    "scripts/run_plugin_semantic_validation_runtime_collector_package.py",
    "scripts/run_plugin_semantic_validation_runtime_observation_gate.py",
    "scripts/run_plugin_semantic_validation_runtime_observation_provenance_gate.py",
    "scripts/run_plugin_semantic_validation_runtime_report_authoring_package.py",
    "scripts/run_plugin_semantic_validation_runtime_report_authoring_gate.py",
    "scripts/run_plugin_semantic_validation_runtime_evidence_gate.py",
    "scripts/run_plugin_validation_preflight.py",
    "scripts/run_plugin_validation_action_plan.py",
    "scripts/run_plugin_availability_resolution_plan.py",
    "scripts/run_plugin_availability_operator_decision_package.py",
    "scripts/run_plugin_availability_decision_gate.py",
    "scripts/run_source_handoff_readiness.py",
    "scripts/run_artifact_signal_audit.py",
    "scripts/run_approval_export_readiness.py",
    "scripts/run_feedback_revision_loop.py",
    "scripts/run_final_export_packager.py",
]

EVIDENCE_FILES = {
    "final_export_state": "export/final_export_state.json",
    "final_render_manifest": "export/final_render_manifest.json",
    "final_render_evidence_gate": "eval_reports/final_render_evidence_gate.json",
    "deliverable_package_manifest": "export/deliverable_package_manifest.json",
    "deliverable_package_evidence_gate": "eval_reports/deliverable_package_evidence_gate.json",
    "final_delivery_consistency_gate": "eval_reports/final_delivery_consistency_gate.json",
    "project_state_manifest": "export/project_state_manifest.json",
    "plugin_mapping_summary": "export/plugin_mapping_summary.md",
    "final_qc_metrics": "eval_reports/final_qc_metrics.json",
    "final_qc_evidence_gate": "eval_reports/final_qc_evidence_gate.json",
    "ab_preview_manifest": "eval_reports/final_ab_preview_manifest.json",
    "ab_preview_evidence_gate": "eval_reports/ab_preview_evidence_gate.json",
    "global_qc_summary": "eval_reports/global_qc_summary.json",
    "final_human_approval": "review/final_human_approval.json",
    "final_approval_evidence_gate": "eval_reports/final_approval_evidence_gate.json",
    "feedback_revision_memory": "review/user_feedback_revision_memory.json",
    "feedback_qc_integration": "eval_reports/user_feedback_qc_integration.json",
    "fixture_coverage_audit": "eval_reports/fixture_coverage_audit.json",
    "requirements_traceability_audit": "eval_reports/requirements_traceability_audit.json",
    "open_risk_register": "eval_reports/open_risk_register.json",
    "risk_root_cause_rollup": "eval_reports/risk_root_cause_rollup.json",
    "risk_remediation_plan": "eval_reports/risk_remediation_plan.json",
    "path_hygiene_audit": "eval_reports/path_hygiene_audit.json",
    "source_acceptance_gate": "eval_reports/source_acceptance_gate.json",
    "artifact_evidence_gate": "eval_reports/artifact_evidence_gate.json",
    "plugin_semantic_validation_gate": "eval_reports/plugin_semantic_validation_gate.json",
    "plugin_semantic_validation_collection_plan": "eval_reports/plugin_semantic_validation_collection_plan.json",
    "plugin_semantic_validation_queue": "eval_reports/plugin_semantic_validation_queue.json",
    "plugin_semantic_validation_runtime_collection_package": "eval_reports/plugin_semantic_validation_runtime_collection_package.json",
    "plugin_semantic_validation_runtime_collector_package": "eval_reports/plugin_semantic_validation_runtime_collector_package.json",
    "plugin_semantic_validation_runtime_observation_gate": "eval_reports/plugin_semantic_validation_runtime_observation_gate.json",
    "plugin_semantic_validation_runtime_observation_provenance_gate": "eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json",
    "plugin_semantic_validation_runtime_report_authoring_package": "eval_reports/plugin_semantic_validation_runtime_report_authoring_package.json",
    "plugin_semantic_validation_runtime_report_authoring_gate": "eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.json",
    "plugin_semantic_validation_runtime_evidence_gate": "eval_reports/plugin_semantic_validation_runtime_evidence_gate.json",
    "plugin_validation_preflight": "eval_reports/plugin_validation_preflight.json",
    "plugin_validation_action_plan": "eval_reports/plugin_validation_action_plan.json",
    "plugin_availability_resolution_plan": "eval_reports/plugin_availability_resolution_plan.json",
    "plugin_availability_operator_decision_package": "eval_reports/plugin_availability_operator_decision_package.json",
    "plugin_availability_decision_gate": "eval_reports/plugin_availability_decision_gate.json",
    "source_handoff_readiness": "eval_reports/source_handoff_readiness.json",
    "artifact_signal_audit": "eval_reports/artifact_signal_audit.json",
    "approval_export_readiness": "eval_reports/approval_export_readiness.json",
    "intent_classification": "eval_reports/intent_classification.json",
    "processing_policy_audit": "eval_reports/processing_policy_audit.json",
    "report_index": "eval_reports/automix_report_index.json",
    "global_rollback_registry": "rollback/global_rollback_registry.json",
    "rollback_evidence_gate": "eval_reports/rollback_evidence_gate.json",
}


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _file_status(root: Path, rel_paths: list[str]) -> list[dict[str, Any]]:
    return [{"path": str(root / rel), "relative_path": rel, "exists": (root / rel).exists()} for rel in rel_paths]


def _evidence_status(output_dir: Path) -> dict[str, dict[str, Any]]:
    status: dict[str, dict[str, Any]] = {}
    for name, rel in EVIDENCE_FILES.items():
        path = output_dir / rel
        data = _load_json(path)
        status[name] = {
            "path": str(path),
            "relative_path": rel,
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
            "json_valid": data is not None if path.suffix.lower() == ".json" else None,
            "data": data or {},
        }
    return status


def _missing_files(statuses: list[dict[str, Any]]) -> list[str]:
    return [item["relative_path"] for item in statuses if not item.get("exists")]


def _source_file_blockers(final_export_state: dict[str, Any]) -> list[str]:
    selected = final_export_state.get("selected_export_source", "")
    if selected and not Path(selected).exists():
        return ["selected_export_source_missing_on_disk"]
    return []


def _render_manifest_blockers(render_manifest: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if render_manifest.get("failures"):
        blockers.append("final_render_manifest_has_failures")
    primary = [
        item
        for item in render_manifest.get("renders", [])
        if item.get("format") == "wav" and item.get("created") and int(item.get("size_bytes", 0) or 0) > 0
    ]
    if not primary:
        blockers.append("primary_wav_render_missing")
    for item in primary:
        path = Path(str(item.get("path", "")))
        if not path.exists():
            blockers.append("primary_wav_render_file_missing")
        elif path.stat().st_size <= 0:
            blockers.append("primary_wav_render_file_empty")
    return sorted(set(blockers))


def _package_manifest_blockers(package_manifest: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not package_manifest.get("package_created", False):
        blockers.append("deliverable_zip_not_created")
    if package_manifest.get("files_missing"):
        blockers.append("deliverable_package_manifest_has_missing_files")
    zip_path = str(package_manifest.get("zip_path", ""))
    if not zip_path:
        blockers.append("deliverable_zip_path_missing")
    elif not Path(zip_path).exists():
        blockers.append("deliverable_zip_missing")
    elif Path(zip_path).stat().st_size <= 0:
        blockers.append("deliverable_zip_empty_on_disk")
    if int(package_manifest.get("package_size_bytes", 0) or 0) <= 0:
        blockers.append("deliverable_zip_empty")
    if not package_manifest.get("project_state_manifest"):
        blockers.append("project_state_manifest_missing_from_package")
    return sorted(set(blockers))


def _project_state_manifest_blockers(project_state_manifest: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not project_state_manifest.get("original_tracks_protected", False):
        blockers.append("project_state_original_tracks_not_protected")
    if not project_state_manifest.get("master_unchanged", False):
        blockers.append("project_state_master_mutated")
    return sorted(set(blockers))


def _ab_preview_blockers(ab_preview: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not ab_preview.get("created", False):
        blockers.append("ab_preview_not_created_for_final_delivery")
    if not ab_preview.get("loudness_matched", False):
        blockers.append("ab_preview_not_loudness_matched")
    output_path = str(ab_preview.get("output_path", ""))
    if not output_path:
        blockers.append("ab_preview_output_path_missing")
    elif not Path(output_path).exists():
        blockers.append("ab_preview_file_missing")
    elif Path(output_path).stat().st_size <= 0:
        blockers.append("ab_preview_file_empty")
    return sorted(set(blockers))


def _rollback_blockers(rollback_registry: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not rollback_registry.get("original_tracks_protected", False):
        blockers.append("rollback_original_tracks_not_protected")
    if not rollback_registry.get("original_master_protected", False):
        blockers.append("rollback_original_master_not_protected")
    validation = rollback_registry.get("validation", {})
    if not validation or not validation.get("passed", False):
        blockers.extend(validation.get("failures", []) or ["rollback_validation_failed"])
    return sorted(set(blockers))


def _plugin_summary_blockers(plugin_summary_status: dict[str, Any]) -> list[str]:
    if plugin_summary_status.get("exists") and int(plugin_summary_status.get("size_bytes", 0) or 0) <= 0:
        return ["plugin_mapping_summary_empty"]
    return []


def build_professional_readiness_audit(
    *,
    project_name: str,
    output_dir: Path,
    workspace_root: Path | None = None,
    final_delivery_requested: bool = False,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    workspace_root = Path(workspace_root or Path.cwd())
    root_doc_status = _file_status(workspace_root, REQUIRED_ROOT_DOCS)
    detail_doc_status = _file_status(workspace_root, REQUIRED_DETAIL_DOCS)
    script_status = _file_status(workspace_root, REQUIRED_SCRIPTS)
    evidence = _evidence_status(output_dir)
    claim_guard = run_claim_language_guard(workspace_root=workspace_root, output_dir=output_dir)

    blockers: list[str] = []
    warnings: list[str] = []
    missing_root_docs = _missing_files(root_doc_status)
    missing_detail_docs = _missing_files(detail_doc_status)
    missing_scripts = _missing_files(script_status)
    if missing_root_docs:
        blockers.append("professional_root_docs_missing")
    if missing_detail_docs:
        blockers.append("professional_detail_docs_missing")
    if missing_scripts:
        blockers.append("required_workflow_scripts_missing")

    final_export_state = evidence["final_export_state"]["data"]
    final_render_manifest = evidence["final_render_manifest"]["data"]
    final_render_evidence = evidence["final_render_evidence_gate"]["data"]
    package_manifest = evidence["deliverable_package_manifest"]["data"]
    deliverable_package_evidence = evidence["deliverable_package_evidence_gate"]["data"]
    final_delivery_consistency = evidence["final_delivery_consistency_gate"]["data"]
    project_state_manifest = evidence["project_state_manifest"]["data"]
    final_qc = evidence["final_qc_metrics"]["data"]
    final_qc_evidence = evidence["final_qc_evidence_gate"]["data"]
    ab_preview = evidence["ab_preview_manifest"]["data"]
    ab_preview_evidence = evidence["ab_preview_evidence_gate"]["data"]
    global_qc = evidence["global_qc_summary"]["data"]
    approval = evidence["final_human_approval"]["data"]
    final_approval_evidence = evidence["final_approval_evidence_gate"]["data"]
    rollback_registry = evidence["global_rollback_registry"]["data"]
    rollback_evidence = evidence["rollback_evidence_gate"]["data"]
    feedback_qc_integration = evidence["feedback_qc_integration"]["data"]
    fixture_coverage = evidence["fixture_coverage_audit"]["data"]
    requirements_traceability = evidence["requirements_traceability_audit"]["data"]
    open_risk_register = evidence["open_risk_register"]["data"]
    risk_root_cause_rollup = evidence["risk_root_cause_rollup"]["data"]
    risk_remediation_plan = evidence["risk_remediation_plan"]["data"]
    path_hygiene = evidence["path_hygiene_audit"]["data"]
    source_acceptance = evidence["source_acceptance_gate"]["data"]
    artifact_evidence = evidence["artifact_evidence_gate"]["data"]
    plugin_semantic_validation = evidence["plugin_semantic_validation_gate"]["data"]
    plugin_semantic_validation_collection_plan = evidence["plugin_semantic_validation_collection_plan"]["data"]
    plugin_semantic_validation_queue = evidence["plugin_semantic_validation_queue"]["data"]
    plugin_semantic_validation_runtime_collection_package = evidence["plugin_semantic_validation_runtime_collection_package"]["data"]
    plugin_semantic_validation_runtime_collector_package = evidence["plugin_semantic_validation_runtime_collector_package"]["data"]
    plugin_semantic_validation_runtime_observation_gate = evidence["plugin_semantic_validation_runtime_observation_gate"]["data"]
    plugin_semantic_validation_runtime_observation_provenance_gate = evidence["plugin_semantic_validation_runtime_observation_provenance_gate"]["data"]
    plugin_semantic_validation_runtime_report_authoring_package = evidence["plugin_semantic_validation_runtime_report_authoring_package"]["data"]
    plugin_semantic_validation_runtime_report_authoring_gate = evidence["plugin_semantic_validation_runtime_report_authoring_gate"]["data"]
    plugin_semantic_validation_runtime_evidence_gate = evidence["plugin_semantic_validation_runtime_evidence_gate"]["data"]
    plugin_validation_preflight = evidence["plugin_validation_preflight"]["data"]
    plugin_validation_action_plan = evidence["plugin_validation_action_plan"]["data"]
    plugin_availability_resolution_plan = evidence["plugin_availability_resolution_plan"]["data"]
    plugin_availability_operator_decision_package = evidence["plugin_availability_operator_decision_package"]["data"]
    plugin_availability_decision_gate = evidence["plugin_availability_decision_gate"]["data"]
    source_handoff = evidence["source_handoff_readiness"]["data"]
    artifact_signal = evidence["artifact_signal_audit"]["data"]
    approval_export_readiness = evidence["approval_export_readiness"]["data"]
    intent_classification = evidence["intent_classification"]["data"]
    processing_policy = evidence["processing_policy_audit"]["data"]
    feedback = summarize_feedback_memory(output_dir)

    if final_delivery_requested:
        for key in (
            "final_export_state",
            "final_render_manifest",
            "final_render_evidence_gate",
            "deliverable_package_manifest",
            "deliverable_package_evidence_gate",
            "final_delivery_consistency_gate",
            "project_state_manifest",
            "plugin_mapping_summary",
            "final_qc_metrics",
            "final_qc_evidence_gate",
            "ab_preview_manifest",
            "ab_preview_evidence_gate",
            "global_qc_summary",
            "final_human_approval",
            "final_approval_evidence_gate",
            "fixture_coverage_audit",
            "requirements_traceability_audit",
            "open_risk_register",
            "risk_root_cause_rollup",
            "risk_remediation_plan",
            "path_hygiene_audit",
            "intent_classification",
            "processing_policy_audit",
            "global_rollback_registry",
            "rollback_evidence_gate",
        ):
            if not evidence[key]["exists"]:
                blockers.append(f"{key}_missing")
            elif evidence[key]["json_valid"] is False:
                blockers.append(f"{key}_invalid_json")
        if final_export_state and not final_export_state.get("safe_to_export", False):
            blockers.extend(final_export_state.get("blocked_reasons", []) or ["final_export_state_not_safe"])
        if final_export_state:
            blockers.extend(_source_file_blockers(final_export_state))
        if final_render_manifest:
            blockers.extend(_render_manifest_blockers(final_render_manifest))
        if final_render_evidence and not final_render_evidence.get("ready_for_final_qc", False):
            blockers.extend(f"final_render_evidence:{item}" for item in final_render_evidence.get("blockers", []) or ["final_render_evidence_not_ready"])
        if package_manifest:
            blockers.extend(_package_manifest_blockers(package_manifest))
        if deliverable_package_evidence and not deliverable_package_evidence.get("ready_for_delivery_package", False):
            blockers.extend(f"deliverable_package_evidence:{item}" for item in deliverable_package_evidence.get("blockers", []) or ["deliverable_package_evidence_not_ready"])
        if final_delivery_consistency and not final_delivery_consistency.get("ready_for_delivery_consistency", False):
            blockers.extend(f"final_delivery_consistency:{item}" for item in final_delivery_consistency.get("blockers", []) or ["final_delivery_consistency_not_ready"])
        if project_state_manifest:
            blockers.extend(_project_state_manifest_blockers(project_state_manifest))
        blockers.extend(_plugin_summary_blockers(evidence["plugin_mapping_summary"]))
        if final_qc and not final_qc.get("qc_passed", False):
            blockers.append("final_qc_not_passed")
        if final_qc_evidence and not final_qc_evidence.get("ready_for_delivery_qc", False):
            blockers.extend(f"final_qc_evidence:{item}" for item in final_qc_evidence.get("blockers", []) or ["final_qc_evidence_not_ready"])
        if ab_preview:
            blockers.extend(_ab_preview_blockers(ab_preview))
        if ab_preview_evidence and not ab_preview_evidence.get("ready_for_human_ab_review", False):
            blockers.extend(f"ab_preview_evidence:{item}" for item in ab_preview_evidence.get("blockers", []) or ["ab_preview_evidence_not_ready"])
        if global_qc and not global_qc.get("safe_to_export", False):
            blockers.extend(global_qc.get("critical_blockers", []) or ["global_qc_not_safe"])
        if approval and not approval.get("approved", False):
            blockers.append("final_human_approval_missing")
        if final_approval_evidence and not final_approval_evidence.get("ready_for_delivery_request", False):
            blockers.extend(f"final_approval_evidence:{item}" for item in final_approval_evidence.get("blockers", []) or ["final_approval_evidence_not_ready"])
        if rollback_registry:
            blockers.extend(_rollback_blockers(rollback_registry))
        if rollback_evidence and not rollback_evidence.get("ready_for_delivery_readiness", False):
            blockers.extend(f"rollback_evidence:{item}" for item in rollback_evidence.get("blockers", []) or ["rollback_evidence_not_ready"])
        if fixture_coverage and not fixture_coverage.get("passed", False):
            blockers.extend(fixture_coverage.get("blockers", []) or ["fixture_coverage_audit_failed"])
        if requirements_traceability and not requirements_traceability.get("passed", False):
            blockers.extend(requirements_traceability.get("blockers", []) or ["requirements_traceability_audit_failed"])
        if open_risk_register and not open_risk_register.get("passed", False):
            blockers.extend(open_risk_register.get("blockers", []) or ["open_risk_register_has_blockers"])
        if risk_root_cause_rollup and not risk_root_cause_rollup.get("passed", False):
            blockers.extend(f"risk_root_cause:{item}" for item in risk_root_cause_rollup.get("blockers", []) or ["risk_root_causes_open"])
        if risk_remediation_plan and risk_remediation_plan.get("blockers"):
            blockers.extend(f"risk_remediation:{item}" for item in risk_remediation_plan.get("blockers", []))
        if path_hygiene and not path_hygiene.get("passed", False):
            blockers.extend(path_hygiene.get("blockers", []) or ["path_hygiene_audit_failed"])
        if processing_policy and not processing_policy.get("passed", False):
            blockers.extend(processing_policy.get("blockers", []) or ["processing_policy_audit_failed"])
        if feedback.get("pending_unresolved_count", 0) > 0:
            blockers.append("user_feedback_unresolved_for_final_delivery")
        if feedback.get("total_entries", 0) > 0:
            if not evidence["feedback_qc_integration"]["exists"]:
                blockers.append("feedback_qc_integration_missing")
            elif evidence["feedback_qc_integration"]["json_valid"] is False:
                blockers.append("feedback_qc_integration_invalid_json")
            elif feedback_qc_integration.get("summary", {}).get("requires_human_review", False):
                blockers.append("feedback_qc_integration_requires_human_review")
            if feedback_qc_integration.get("summary", {}).get("items_with_missing_qc_metrics", 0):
                warnings.append("feedback_qc_integration_has_missing_metric_values")
        if not claim_guard.get("passed", False):
            blockers.extend(claim_guard.get("blockers", []) or ["unsafe_claim_language_detected"])
    else:
        warnings.append("final_delivery_not_requested_readiness_is_documentation_and_gate_inventory_only")
        if not claim_guard.get("passed", False):
            warnings.append("unsafe_claim_language_detected")

    if not evidence["feedback_revision_memory"]["exists"]:
        warnings.append("feedback_revision_memory_not_created")
    if not evidence["report_index"]["exists"]:
        warnings.append("report_index_not_created")

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    ready = final_delivery_requested and not blockers
    audit = {
        "schema": PROFESSIONAL_READINESS_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "workspace_root": str(workspace_root),
        "output_dir": str(output_dir),
        "final_delivery_requested": bool(final_delivery_requested),
        "readiness_status": "ready_for_delivery" if ready else "review_required",
        "ready_for_delivery": ready,
        "blockers": blockers,
        "warnings": warnings,
        "root_docs": root_doc_status,
        "detail_docs": detail_doc_status,
        "workflow_scripts": script_status,
        "evidence_files": {key: {k: v for k, v in item.items() if k != "data"} for key, item in evidence.items()},
        "final_export_state_summary": {
            "safe_to_export": bool(final_export_state.get("safe_to_export", False)),
            "blocked_reasons": final_export_state.get("blocked_reasons", []),
            "selected_export_source": final_export_state.get("selected_export_source", ""),
        },
        "global_qc_summary": {
            "safe_to_export": bool(global_qc.get("safe_to_export", False)),
            "critical_blockers": global_qc.get("critical_blockers", []),
        },
        "final_qc_summary": {
            "qc_passed": bool(final_qc.get("qc_passed", False)),
            "failures": final_qc.get("failures", []),
        },
        "final_qc_evidence_gate_summary": {
            "ready_for_delivery_qc": bool(final_qc_evidence.get("ready_for_delivery_qc", False)),
            "ready_for_approval_readiness": bool(final_qc_evidence.get("ready_for_approval_readiness", False)),
            "final_audio_path": final_qc_evidence.get("final_audio_path", ""),
            "blockers": final_qc_evidence.get("blockers", []),
            "warnings": final_qc_evidence.get("warnings", []),
            "qc_summary": final_qc_evidence.get("qc_summary", {}),
            "render_link_summary": final_qc_evidence.get("render_link_summary", {}),
        },
        "final_render_summary": {
            "render_count": len(final_render_manifest.get("renders", [])),
            "failures": final_render_manifest.get("failures", []),
            "primary_wav_count": len(
                [
                    item
                    for item in final_render_manifest.get("renders", [])
                    if item.get("format") == "wav" and item.get("created") and int(item.get("size_bytes", 0) or 0) > 0
                ]
            ),
        },
        "final_render_evidence_gate_summary": {
            "ready_for_final_qc": bool(final_render_evidence.get("ready_for_final_qc", False)),
            "ready_for_approval_readiness": bool(final_render_evidence.get("ready_for_approval_readiness", False)),
            "primary_wav_path": final_render_evidence.get("primary_wav_path", ""),
            "blockers": final_render_evidence.get("blockers", []),
            "warnings": final_render_evidence.get("warnings", []),
        },
        "deliverable_package_summary": {
            "package_created": bool(package_manifest.get("package_created", False)),
            "package_size_bytes": int(package_manifest.get("package_size_bytes", 0) or 0),
            "files_missing": package_manifest.get("files_missing", []),
            "zip_path": package_manifest.get("zip_path", ""),
        },
        "deliverable_package_evidence_gate_summary": {
            "ready_for_delivery_package": bool(deliverable_package_evidence.get("ready_for_delivery_package", False)),
            "ready_for_professional_readiness": bool(deliverable_package_evidence.get("ready_for_professional_readiness", False)),
            "zip_valid": bool(deliverable_package_evidence.get("zip_status", {}).get("valid_zip", False)),
            "blockers": deliverable_package_evidence.get("blockers", []),
            "warnings": deliverable_package_evidence.get("warnings", []),
            "package_summary": deliverable_package_evidence.get("package_summary", {}),
        },
        "final_delivery_consistency_gate_summary": {
            "ready_for_delivery_consistency": bool(final_delivery_consistency.get("ready_for_delivery_consistency", False)),
            "ready_for_professional_readiness": bool(final_delivery_consistency.get("ready_for_professional_readiness", False)),
            "final_audio_path": final_delivery_consistency.get("final_audio_consistency", {}).get("final_audio_path", ""),
            "ab_preview_path": final_delivery_consistency.get("ab_preview_consistency", {}).get("preview_output_path", ""),
            "blockers": final_delivery_consistency.get("blockers", []),
            "warnings": final_delivery_consistency.get("warnings", []),
        },
        "project_state_summary": {
            "original_tracks_protected": bool(project_state_manifest.get("original_tracks_protected", False)),
            "master_unchanged": bool(project_state_manifest.get("master_unchanged", False)),
        },
        "plugin_mapping_summary": {
            "exists": bool(evidence["plugin_mapping_summary"].get("exists")),
            "size_bytes": int(evidence["plugin_mapping_summary"].get("size_bytes", 0) or 0),
        },
        "ab_preview_summary": {
            "created": bool(ab_preview.get("created", False)),
            "loudness_matched": bool(ab_preview.get("loudness_matched", False)),
            "output_path": ab_preview.get("output_path", ""),
            "warnings": ab_preview.get("warnings", []),
        },
        "ab_preview_evidence_gate_summary": {
            "ready_for_human_ab_review": bool(ab_preview_evidence.get("ready_for_human_ab_review", False)),
            "ready_for_final_approval_request": bool(ab_preview_evidence.get("ready_for_final_approval_request", False)),
            "human_ab_review_recorded": bool(ab_preview_evidence.get("human_ab_review_recorded", False)),
            "blockers": ab_preview_evidence.get("blockers", []),
            "warnings": ab_preview_evidence.get("warnings", []),
            "loudness_match_status": ab_preview_evidence.get("loudness_match_status", {}),
        },
        "rollback_summary": {
            "validation_passed": bool(rollback_registry.get("validation", {}).get("passed", False)),
            "failures": rollback_registry.get("validation", {}).get("failures", []),
        },
        "rollback_evidence_gate_summary": {
            "ready_for_delivery_readiness": bool(rollback_evidence.get("ready_for_delivery_readiness", False)),
            "original_tracks_protected": bool(rollback_evidence.get("original_tracks_protected", False)),
            "original_master_protected": bool(rollback_evidence.get("original_master_protected", False)),
            "rollback_entries_total": int(rollback_evidence.get("rollback_entries_total", 0) or 0),
            "safe_entries_total": int(rollback_evidence.get("safe_entries_total", 0) or 0),
            "blockers": rollback_evidence.get("blockers", []),
            "warnings": rollback_evidence.get("warnings", []),
        },
        "approval_summary": {
            "approved": bool(approval.get("approved", False)),
            "approved_stage": approval.get("approved_stage", ""),
        },
        "final_approval_evidence_gate_summary": {
            "ready_for_delivery_request": bool(final_approval_evidence.get("ready_for_delivery_request", False)),
            "approval_pending_only": bool(final_approval_evidence.get("approval_pending_only", False)),
            "approved": bool(final_approval_evidence.get("approved", False)),
            "review_decision": final_approval_evidence.get("review_decision", ""),
            "blockers": final_approval_evidence.get("blockers", []),
            "warnings": final_approval_evidence.get("warnings", []),
            "approval_summary": final_approval_evidence.get("approval_summary", {}),
            "supporting_gate_summary": final_approval_evidence.get("supporting_gate_summary", {}),
        },
        "feedback_revision_loop": feedback,
        "feedback_qc_integration_summary": feedback_qc_integration.get("summary", {}),
        "fixture_coverage_audit_summary": {
            "passed": bool(fixture_coverage.get("passed", False)),
            "covered_categories": fixture_coverage.get("covered_categories", []),
            "missing_categories": fixture_coverage.get("missing_categories", []),
            "blockers": fixture_coverage.get("blockers", []),
        },
        "requirements_traceability_audit_summary": {
            "passed": bool(requirements_traceability.get("passed", False)),
            "requirements_satisfied": int(requirements_traceability.get("requirements_satisfied", 0) or 0),
            "requirements_total": int(requirements_traceability.get("requirements_total", 0) or 0),
            "incomplete_requirement_ids": requirements_traceability.get("incomplete_requirement_ids", []),
            "blockers": requirements_traceability.get("blockers", []),
        },
        "open_risk_register_summary": {
            "passed": bool(open_risk_register.get("passed", False)),
            "risk_counts": open_risk_register.get("risk_counts", {}),
            "blockers": open_risk_register.get("blockers", []),
        },
        "risk_remediation_plan_summary": {
            "status": risk_remediation_plan.get("status", ""),
            "open_risk_total": int(risk_remediation_plan.get("open_risk_total", 0) or 0),
            "actions_total": int(risk_remediation_plan.get("actions_total", 0) or 0),
            "dry_run_only": bool(risk_remediation_plan.get("dry_run_only", True)),
            "blockers": risk_remediation_plan.get("blockers", []),
        },
        "risk_root_cause_rollup_summary": {
            "passed": bool(risk_root_cause_rollup.get("passed", False)),
            "open_risk_total": int(risk_root_cause_rollup.get("open_risk_total", 0) or 0),
            "root_cause_total": int(risk_root_cause_rollup.get("root_cause_total", 0) or 0),
            "next_root_cause": risk_root_cause_rollup.get("next_root_cause", {}),
            "blockers": risk_root_cause_rollup.get("blockers", []),
        },
        "path_hygiene_audit_summary": {
            "passed": bool(path_hygiene.get("passed", False)),
            "finding_counts": path_hygiene.get("finding_counts", {}),
            "blockers": path_hygiene.get("blockers", []),
            "warnings": path_hygiene.get("warnings", []),
        },
        "plugin_validation_preflight_summary": {
            "status": plugin_validation_preflight.get("status", ""),
            "safe_to_write_parameters": bool(plugin_validation_preflight.get("summary", {}).get("safe_to_write_parameters", False)),
            "available_plugins_total": int(plugin_validation_preflight.get("summary", {}).get("available_plugins_total", 0) or 0),
            "missing_plugins_total": int(plugin_validation_preflight.get("summary", {}).get("missing_plugins_total", 0) or 0),
            "blockers": plugin_validation_preflight.get("blockers", []),
            "warnings": plugin_validation_preflight.get("warnings", []),
        },
        "plugin_validation_action_plan_summary": {
            "status": plugin_validation_action_plan.get("status", ""),
            "safe_to_write_parameters": bool(plugin_validation_action_plan.get("summary", {}).get("safe_to_write_parameters", False)),
            "required_plugins_total": int(plugin_validation_action_plan.get("required_plugins_total", 0) or 0),
            "plugin_actions_total": int(plugin_validation_action_plan.get("plugin_actions_total", 0) or 0),
            "next_plugin_action": plugin_validation_action_plan.get("next_plugin_action", {}),
            "blockers": plugin_validation_action_plan.get("blockers", []),
            "warnings": plugin_validation_action_plan.get("warnings", []),
        },
        "plugin_availability_resolution_plan_summary": {
            "status": plugin_availability_resolution_plan.get("status", ""),
            "unavailable_plugins_total": int(plugin_availability_resolution_plan.get("unavailable_plugins_total", 0) or 0),
            "pending_operator_decisions": plugin_availability_resolution_plan.get("pending_operator_decisions", []),
            "disable_manifest_plugins_total": int(plugin_availability_resolution_plan.get("disable_manifest_plugins_total", 0) or 0),
            "blockers": plugin_availability_resolution_plan.get("blockers", []),
            "warnings": plugin_availability_resolution_plan.get("warnings", []),
        },
        "plugin_availability_operator_decision_package_summary": {
            "status": plugin_availability_operator_decision_package.get("status", ""),
            "operator_decision_package_ready": bool(plugin_availability_operator_decision_package.get("operator_decision_package_ready", False)),
            "availability_decisions_ready": bool(plugin_availability_operator_decision_package.get("availability_decisions_ready", False)),
            "required_decisions_total": int(plugin_availability_operator_decision_package.get("required_decisions_total", 0) or 0),
            "accepted_decisions_total": int(plugin_availability_operator_decision_package.get("accepted_decisions_total", 0) or 0),
            "missing_decisions": plugin_availability_operator_decision_package.get("missing_decisions", []),
            "candidate_manifest_path": plugin_availability_operator_decision_package.get("candidate_manifest_path", ""),
            "accepted_manifest_path": plugin_availability_operator_decision_package.get("accepted_manifest_path", ""),
            "accepted_manifest_exists": bool(plugin_availability_operator_decision_package.get("accepted_manifest_exists", False)),
            "safe_to_write_parameters": bool(plugin_availability_operator_decision_package.get("safe_to_write_parameters", False)),
            "blockers": plugin_availability_operator_decision_package.get("blockers", []),
            "warnings": plugin_availability_operator_decision_package.get("warnings", []),
        },
        "plugin_availability_decision_gate_summary": {
            "status": plugin_availability_decision_gate.get("status", ""),
            "availability_decisions_ready": bool(plugin_availability_decision_gate.get("availability_decisions_ready", False)),
            "required_decisions_total": int(plugin_availability_decision_gate.get("required_decisions_total", 0) or 0),
            "accepted_decisions_total": int(plugin_availability_decision_gate.get("accepted_decisions_total", 0) or 0),
            "missing_decisions": plugin_availability_decision_gate.get("missing_decisions", []),
            "safe_to_write_parameters": bool(plugin_availability_decision_gate.get("safe_to_write_parameters", False)),
            "blockers": plugin_availability_decision_gate.get("blockers", []),
            "warnings": plugin_availability_decision_gate.get("warnings", []),
        },
        "plugin_semantic_validation_gate_summary": {
            "semantic_validation_ready": bool(plugin_semantic_validation.get("semantic_validation_ready", False)),
            "required_plugins_total": int(plugin_semantic_validation.get("required_plugins_total", 0) or 0),
            "validation_reports_total": int(plugin_semantic_validation.get("validation_reports_total", 0) or 0),
            "safe_controls_total": int(plugin_semantic_validation.get("safe_controls_total", 0) or 0),
            "blockers": plugin_semantic_validation.get("blockers", []),
            "warnings": plugin_semantic_validation.get("warnings", []),
        },
        "plugin_semantic_validation_collection_plan_summary": {
            "status": plugin_semantic_validation_collection_plan.get("status", ""),
            "open_jobs_total": int(plugin_semantic_validation_collection_plan.get("open_jobs_total", 0) or 0),
            "collectable_jobs_total": int(plugin_semantic_validation_collection_plan.get("collectable_jobs_total", 0) or 0),
            "decision_blocked_jobs_total": int(plugin_semantic_validation_collection_plan.get("decision_blocked_jobs_total", 0) or 0),
            "ready_to_collect_some_in_reaper": bool(plugin_semantic_validation_collection_plan.get("ready_to_collect_some_in_reaper", False)),
            "all_jobs_resolved": bool(plugin_semantic_validation_collection_plan.get("all_jobs_resolved", False)),
            "safe_to_write_parameters": bool(plugin_semantic_validation_collection_plan.get("safe_to_write_parameters", False)),
            "next_collection_job": plugin_semantic_validation_collection_plan.get("next_collection_job", {}),
            "blockers": plugin_semantic_validation_collection_plan.get("blockers", []),
            "warnings": plugin_semantic_validation_collection_plan.get("warnings", []),
        },
        "plugin_semantic_validation_queue_summary": {
            "status": plugin_semantic_validation_queue.get("status", ""),
            "queue_jobs_total": int(plugin_semantic_validation_queue.get("queue_jobs_total", 0) or 0),
            "blocked_jobs_total": int(plugin_semantic_validation_queue.get("blocked_jobs_total", 0) or 0),
            "ready_to_run_reaper_collection": bool(plugin_semantic_validation_queue.get("ready_to_run_reaper_collection", False)),
            "requires_reaper_runtime": bool(plugin_semantic_validation_queue.get("requires_reaper_runtime", False)),
            "safe_to_write_parameters": bool(plugin_semantic_validation_queue.get("safe_to_write_parameters", False)),
            "next_queue_job": plugin_semantic_validation_queue.get("next_queue_job", {}),
            "blockers": plugin_semantic_validation_queue.get("blockers", []),
            "warnings": plugin_semantic_validation_queue.get("warnings", []),
        },
        "plugin_semantic_validation_runtime_collection_package_summary": {
            "status": plugin_semantic_validation_runtime_collection_package.get("status", ""),
            "ready_for_runtime_collection": bool(plugin_semantic_validation_runtime_collection_package.get("ready_for_runtime_collection", False)),
            "ready_for_runtime_evidence_gate": bool(plugin_semantic_validation_runtime_collection_package.get("ready_for_runtime_evidence_gate", False)),
            "collection_jobs_total": int(plugin_semantic_validation_runtime_collection_package.get("collection_jobs_total", 0) or 0),
            "report_templates_total": int(plugin_semantic_validation_runtime_collection_package.get("report_templates_total", 0) or 0),
            "target_reports_existing_total": int(plugin_semantic_validation_runtime_collection_package.get("target_reports_existing_total", 0) or 0),
            "target_reports_missing_total": int(plugin_semantic_validation_runtime_collection_package.get("target_reports_missing_total", 0) or 0),
            "blocked_queue_jobs_total": int(plugin_semantic_validation_runtime_collection_package.get("blocked_queue_jobs_total", 0) or 0),
            "safe_to_write_parameters": bool(plugin_semantic_validation_runtime_collection_package.get("safe_to_write_parameters", False)),
            "manifest_candidate_path": plugin_semantic_validation_runtime_collection_package.get("manifest_candidate_path", ""),
            "report_template_dir": plugin_semantic_validation_runtime_collection_package.get("report_template_dir", ""),
            "blockers": plugin_semantic_validation_runtime_collection_package.get("blockers", []),
            "warnings": plugin_semantic_validation_runtime_collection_package.get("warnings", []),
        },
        "plugin_semantic_validation_runtime_collector_package_summary": {
            "status": plugin_semantic_validation_runtime_collector_package.get("status", ""),
            "ready_for_reaper_runtime_collection": bool(
                plugin_semantic_validation_runtime_collector_package.get("ready_for_reaper_runtime_collection", False)
            ),
            "ready_for_runtime_evidence_gate": bool(plugin_semantic_validation_runtime_collector_package.get("ready_for_runtime_evidence_gate", False)),
            "collector_jobs_total": int(plugin_semantic_validation_runtime_collector_package.get("collector_jobs_total", 0) or 0),
            "blocked_queue_jobs_total": int(plugin_semantic_validation_runtime_collector_package.get("blocked_queue_jobs_total", 0) or 0),
            "safe_to_write_parameters": bool(plugin_semantic_validation_runtime_collector_package.get("safe_to_write_parameters", False)),
            "creates_validation_reports": bool(plugin_semantic_validation_runtime_collector_package.get("creates_validation_reports", False)),
            "lua_collector_script_path": plugin_semantic_validation_runtime_collector_package.get("lua_collector_script_path", ""),
            "queue_payload_path": plugin_semantic_validation_runtime_collector_package.get("queue_payload_path", ""),
            "operator_runbook_path": plugin_semantic_validation_runtime_collector_package.get("operator_runbook_path", ""),
            "blockers": plugin_semantic_validation_runtime_collector_package.get("blockers", []),
            "warnings": plugin_semantic_validation_runtime_collector_package.get("warnings", []),
        },
        "plugin_semantic_validation_runtime_observation_gate_summary": {
            "status": plugin_semantic_validation_runtime_observation_gate.get("status", ""),
            "runtime_observations_ready": bool(plugin_semantic_validation_runtime_observation_gate.get("runtime_observations_ready", False)),
            "ready_for_manual_report_authoring": bool(
                plugin_semantic_validation_runtime_observation_gate.get("ready_for_manual_report_authoring", False)
            ),
            "ready_for_runtime_evidence_gate": bool(plugin_semantic_validation_runtime_observation_gate.get("ready_for_runtime_evidence_gate", False)),
            "collector_jobs_total": int(plugin_semantic_validation_runtime_observation_gate.get("collector_jobs_total", 0) or 0),
            "accepted_observations_total": int(plugin_semantic_validation_runtime_observation_gate.get("accepted_observations_total", 0) or 0),
            "blocked_observations_total": int(plugin_semantic_validation_runtime_observation_gate.get("blocked_observations_total", 0) or 0),
            "blocked_queue_jobs_total": int(plugin_semantic_validation_runtime_observation_gate.get("blocked_queue_jobs_total", 0) or 0),
            "safe_to_write_parameters": bool(plugin_semantic_validation_runtime_observation_gate.get("safe_to_write_parameters", False)),
            "creates_validation_reports": bool(plugin_semantic_validation_runtime_observation_gate.get("creates_validation_reports", False)),
            "next_blocked_observation": plugin_semantic_validation_runtime_observation_gate.get("next_blocked_observation", {}),
            "blockers": plugin_semantic_validation_runtime_observation_gate.get("blockers", []),
            "warnings": plugin_semantic_validation_runtime_observation_gate.get("warnings", []),
        },
        "plugin_semantic_validation_runtime_observation_provenance_gate_summary": {
            "status": plugin_semantic_validation_runtime_observation_provenance_gate.get("status", ""),
            "passed": bool(plugin_semantic_validation_runtime_observation_provenance_gate.get("passed", False)),
            "expected_observation_provenance_packet_ready": bool(
                plugin_semantic_validation_runtime_observation_provenance_gate.get("readiness", {}).get(
                    "expected_observation_provenance_packet_ready", False
                )
            ),
            "observed_runtime_provenance_ready": bool(
                plugin_semantic_validation_runtime_observation_provenance_gate.get("readiness", {}).get(
                    "observed_runtime_provenance_ready", False
                )
            ),
            "ready_for_manual_report_authoring": bool(
                plugin_semantic_validation_runtime_observation_provenance_gate.get("readiness", {}).get(
                    "ready_for_manual_report_authoring", False
                )
            ),
            "safe_to_write_parameters": bool(
                plugin_semantic_validation_runtime_observation_provenance_gate.get("readiness", {}).get(
                    "safe_to_write_parameters", False
                )
            ),
            "creates_validation_reports": bool(
                plugin_semantic_validation_runtime_observation_provenance_gate.get("readiness", {}).get(
                    "creates_validation_reports", False
                )
            ),
            "counts": plugin_semantic_validation_runtime_observation_provenance_gate.get("counts", {}),
            "blockers": plugin_semantic_validation_runtime_observation_provenance_gate.get("blockers", []),
            "warnings": plugin_semantic_validation_runtime_observation_provenance_gate.get("warnings", []),
        },
        "plugin_semantic_validation_runtime_report_authoring_package_summary": {
            "status": plugin_semantic_validation_runtime_report_authoring_package.get("status", ""),
            "runtime_report_authoring_package_ready": bool(
                plugin_semantic_validation_runtime_report_authoring_package.get("runtime_report_authoring_package_ready", False)
            ),
            "ready_for_manual_report_authoring": bool(
                plugin_semantic_validation_runtime_report_authoring_package.get("ready_for_manual_report_authoring", False)
            ),
            "ready_for_runtime_evidence_gate": bool(
                plugin_semantic_validation_runtime_report_authoring_package.get("ready_for_runtime_evidence_gate", False)
            ),
            "accepted_observations_total": int(plugin_semantic_validation_runtime_report_authoring_package.get("accepted_observations_total", 0) or 0),
            "templates_total": int(plugin_semantic_validation_runtime_report_authoring_package.get("templates_total", 0) or 0),
            "safe_to_write_parameters": bool(plugin_semantic_validation_runtime_report_authoring_package.get("safe_to_write_parameters", False)),
            "creates_validation_reports": bool(plugin_semantic_validation_runtime_report_authoring_package.get("creates_validation_reports", False)),
            "writes_analysis_reports": bool(plugin_semantic_validation_runtime_report_authoring_package.get("writes_analysis_reports", False)),
            "template_dir": plugin_semantic_validation_runtime_report_authoring_package.get("template_dir", ""),
            "checklist_path": plugin_semantic_validation_runtime_report_authoring_package.get("checklist_path", ""),
            "blockers": plugin_semantic_validation_runtime_report_authoring_package.get("blockers", []),
            "warnings": plugin_semantic_validation_runtime_report_authoring_package.get("warnings", []),
        },
        "plugin_semantic_validation_runtime_report_authoring_gate_summary": {
            "status": plugin_semantic_validation_runtime_report_authoring_gate.get("status", ""),
            "authoring_candidates_ready": bool(plugin_semantic_validation_runtime_report_authoring_gate.get("authoring_candidates_ready", False)),
            "ready_for_operator_promotion": bool(plugin_semantic_validation_runtime_report_authoring_gate.get("ready_for_operator_promotion", False)),
            "ready_for_runtime_evidence_gate": bool(plugin_semantic_validation_runtime_report_authoring_gate.get("ready_for_runtime_evidence_gate", False)),
            "templates_total": int(plugin_semantic_validation_runtime_report_authoring_gate.get("templates_total", 0) or 0),
            "candidate_reports_total": int(plugin_semantic_validation_runtime_report_authoring_gate.get("candidate_reports_total", 0) or 0),
            "accepted_candidates_total": int(plugin_semantic_validation_runtime_report_authoring_gate.get("accepted_candidates_total", 0) or 0),
            "blocked_candidates_total": int(plugin_semantic_validation_runtime_report_authoring_gate.get("blocked_candidates_total", 0) or 0),
            "safe_to_write_parameters": bool(plugin_semantic_validation_runtime_report_authoring_gate.get("safe_to_write_parameters", False)),
            "writes_analysis_reports": bool(plugin_semantic_validation_runtime_report_authoring_gate.get("writes_analysis_reports", False)),
            "candidate_reports_are_validation_evidence": bool(
                plugin_semantic_validation_runtime_report_authoring_gate.get("candidate_reports_are_validation_evidence", False)
            ),
            "candidate_dir": plugin_semantic_validation_runtime_report_authoring_gate.get("candidate_dir", ""),
            "promotion_checklist_path": plugin_semantic_validation_runtime_report_authoring_gate.get("promotion_checklist_path", ""),
            "manifest_candidate_path": plugin_semantic_validation_runtime_report_authoring_gate.get("manifest_candidate_path", ""),
            "blockers": plugin_semantic_validation_runtime_report_authoring_gate.get("blockers", []),
            "warnings": plugin_semantic_validation_runtime_report_authoring_gate.get("warnings", []),
        },
        "plugin_semantic_validation_runtime_evidence_gate_summary": {
            "status": plugin_semantic_validation_runtime_evidence_gate.get("status", ""),
            "runtime_evidence_ready": bool(plugin_semantic_validation_runtime_evidence_gate.get("runtime_evidence_ready", False)),
            "ready_for_semantic_gate_rerun": bool(plugin_semantic_validation_runtime_evidence_gate.get("ready_for_semantic_gate_rerun", False)),
            "queue_jobs_total": int(plugin_semantic_validation_runtime_evidence_gate.get("queue_jobs_total", 0) or 0),
            "accepted_jobs_total": int(plugin_semantic_validation_runtime_evidence_gate.get("accepted_jobs_total", 0) or 0),
            "blocked_jobs_total": int(plugin_semantic_validation_runtime_evidence_gate.get("blocked_jobs_total", 0) or 0),
            "blocked_queue_jobs_total": int(plugin_semantic_validation_runtime_evidence_gate.get("blocked_queue_jobs_total", 0) or 0),
            "safe_to_write_parameters": bool(plugin_semantic_validation_runtime_evidence_gate.get("safe_to_write_parameters", False)),
            "next_blocked_job": plugin_semantic_validation_runtime_evidence_gate.get("next_blocked_job", {}),
            "blockers": plugin_semantic_validation_runtime_evidence_gate.get("blockers", []),
            "warnings": plugin_semantic_validation_runtime_evidence_gate.get("warnings", []),
        },
        "source_handoff_readiness_summary": {
            "stem_requests_total": int(source_handoff.get("summary", {}).get("stem_requests_total", 0) or 0),
            "manual_review_tracks_total": int(source_handoff.get("summary", {}).get("manual_review_tracks_total", 0) or 0),
            "source_files_present_total": int(source_handoff.get("summary", {}).get("source_files_present_total", 0) or 0),
            "source_files_total": int(source_handoff.get("summary", {}).get("source_files_total", 0) or 0),
            "accepted_export_source_present": bool(source_handoff.get("summary", {}).get("accepted_export_source_present", False)),
            "automatic_processing_ready": bool(source_handoff.get("summary", {}).get("automatic_processing_ready", False)),
            "blockers": source_handoff.get("blockers", []),
            "warnings": source_handoff.get("warnings", []),
        },
        "source_acceptance_gate_summary": {
            "accepted_export_source_ready": bool(source_acceptance.get("accepted_export_source_ready", False)),
            "accepted_stem_sources_total": int(source_acceptance.get("accepted_stem_sources_total", 0) or 0),
            "candidate_sources_total": int(source_acceptance.get("candidate_sources_total", 0) or 0),
            "blockers": source_acceptance.get("blockers", []),
            "warnings": source_acceptance.get("warnings", []),
        },
        "artifact_signal_audit_summary": {
            "artifact_signal_established": bool(artifact_signal.get("artifact_signal_established", False)),
            "safe_to_run_artifact_suppression": bool(artifact_signal.get("safe_to_run_artifact_suppression", False)),
            "usable_source_signals": int(artifact_signal.get("summary", {}).get("usable_source_signals", 0) or 0),
            "usable_metric_signals": int(artifact_signal.get("summary", {}).get("usable_metric_signals", 0) or 0),
            "usable_feedback_signal": bool(artifact_signal.get("summary", {}).get("usable_feedback_signal", False)),
            "blockers": artifact_signal.get("blockers", []),
            "warnings": artifact_signal.get("warnings", []),
        },
        "artifact_evidence_gate_summary": {
            "artifact_evidence_established": bool(artifact_evidence.get("artifact_evidence_established", False)),
            "measured_artifact_metrics_established": bool(artifact_evidence.get("measured_artifact_metrics_established", False)),
            "ready_for_artifact_review": bool(artifact_evidence.get("ready_for_artifact_review", False)),
            "safe_to_run_artifact_suppression": bool(artifact_evidence.get("safe_to_run_artifact_suppression", False)),
            "blockers": artifact_evidence.get("blockers", []),
            "warnings": artifact_evidence.get("warnings", []),
        },
        "approval_export_readiness_summary": {
            "readiness_status": approval_export_readiness.get("readiness_status", ""),
            "ready_for_delivery_request": bool(approval_export_readiness.get("ready_for_delivery_request", False)),
            "ready_for_human_approval_request": bool(approval_export_readiness.get("ready_for_human_approval_request", False)),
            "blockers": approval_export_readiness.get("blockers", []),
            "warnings": approval_export_readiness.get("warnings", []),
        },
        "intent_classification_summary": {
            "status": intent_classification.get("status", ""),
            "recommended_primary_intent": intent_classification.get("recommended_primary_intent", ""),
            "safe_next_mode": intent_classification.get("safe_next_mode", ""),
            "safe_draft_intents": intent_classification.get("safe_draft_intents", []),
        },
        "processing_policy_audit_summary": {
            "passed": bool(processing_policy.get("passed", False)),
            "plans_checked": int(processing_policy.get("plans_checked", 0) or 0),
            "blockers": processing_policy.get("blockers", []),
        },
        "claim_language_guard": claim_guard,
    }
    target = output_path or output_dir / "eval_reports" / "professional_readiness_audit.json"
    write_json(target, audit)
    write_professional_readiness_markdown(audit, output_dir)
    return audit


def write_professional_readiness_markdown(audit: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Professional Readiness Audit",
        "",
        f"- Project: `{audit.get('project_name')}`",
        f"- Created UTC: `{audit.get('created_at')}`",
        f"- Status: `{audit.get('readiness_status')}`",
        f"- Ready for delivery: `{audit.get('ready_for_delivery')}`",
        "",
        "## Blockers",
        "",
    ]
    blockers = audit.get("blockers", [])
    lines.extend([f"- `{item}`" for item in blockers] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    warnings = audit.get("warnings", [])
    lines.extend([f"- `{item}`" for item in warnings] or ["- none"])
    lines.extend(["", "## Evidence", ""])
    for name, item in audit.get("evidence_files", {}).items():
        lines.append(f"- `{name}`: exists=`{item.get('exists')}`, json_valid=`{item.get('json_valid')}`")
    lines.extend(["", "## Delivery Evidence Summary", ""])
    render = audit.get("final_render_summary", {})
    package = audit.get("deliverable_package_summary", {})
    package_evidence = audit.get("deliverable_package_evidence_gate_summary", {})
    delivery_consistency = audit.get("final_delivery_consistency_gate_summary", {})
    final_qc = audit.get("final_qc_summary", {})
    final_qc_evidence = audit.get("final_qc_evidence_gate_summary", {})
    project_state = audit.get("project_state_summary", {})
    plugin_summary = audit.get("plugin_mapping_summary", {})
    ab_preview = audit.get("ab_preview_summary", {})
    approval_evidence = audit.get("final_approval_evidence_gate_summary", {})
    rollback = audit.get("rollback_summary", {})
    lines.append(f"- Primary WAV renders: `{render.get('primary_wav_count', 0)}`")
    lines.append(f"- Render failures: `{render.get('failures', [])}`")
    render_evidence = audit.get("final_render_evidence_gate_summary", {})
    lines.append(f"- Final render evidence ready: `{render_evidence.get('ready_for_final_qc', False)}`")
    lines.append(f"- Final QC passed: `{final_qc.get('qc_passed', False)}`")
    lines.append(f"- Final QC failures: `{final_qc.get('failures', [])}`")
    lines.append(f"- Final QC evidence ready: `{final_qc_evidence.get('ready_for_delivery_qc', False)}`")
    lines.append(f"- ZIP package created: `{package.get('package_created', False)}`")
    lines.append(f"- ZIP package size bytes: `{package.get('package_size_bytes', 0)}`")
    lines.append(f"- Packaged files missing: `{package.get('files_missing', [])}`")
    lines.append(f"- Deliverable package evidence ready: `{package_evidence.get('ready_for_delivery_package', False)}`")
    lines.append(f"- Deliverable ZIP valid: `{package_evidence.get('zip_valid', False)}`")
    lines.append(f"- Final delivery consistency ready: `{delivery_consistency.get('ready_for_delivery_consistency', False)}`")
    lines.append(f"- Original tracks protected: `{project_state.get('original_tracks_protected', False)}`")
    lines.append(f"- Master unchanged: `{project_state.get('master_unchanged', False)}`")
    lines.append(f"- Plugin summary bytes: `{plugin_summary.get('size_bytes', 0)}`")
    lines.append(f"- A/B preview created: `{ab_preview.get('created', False)}`")
    lines.append(f"- A/B preview loudness matched: `{ab_preview.get('loudness_matched', False)}`")
    ab_evidence = audit.get("ab_preview_evidence_gate_summary", {})
    lines.append(f"- A/B preview evidence ready: `{ab_evidence.get('ready_for_human_ab_review', False)}`")
    lines.append(f"- Final approval evidence ready: `{approval_evidence.get('ready_for_delivery_request', False)}`")
    lines.append(f"- Rollback validation passed: `{rollback.get('validation_passed', False)}`")
    rollback_evidence = audit.get("rollback_evidence_gate_summary", {})
    lines.append(f"- Rollback evidence ready: `{rollback_evidence.get('ready_for_delivery_readiness', False)}`")
    intent = audit.get("intent_classification_summary", {})
    lines.extend(["", "## Intent Classification", ""])
    lines.append(f"- Status: `{intent.get('status', '')}`")
    lines.append(f"- Recommended primary intent: `{intent.get('recommended_primary_intent', '')}`")
    lines.append(f"- Safe next mode: `{intent.get('safe_next_mode', '')}`")
    lines.append(f"- Safe draft intents: `{intent.get('safe_draft_intents', [])}`")
    policy = audit.get("processing_policy_audit_summary", {})
    lines.extend(["", "## Processing Policy Audit", ""])
    lines.append(f"- Passed: `{policy.get('passed', False)}`")
    lines.append(f"- Plans checked: `{policy.get('plans_checked', 0)}`")
    lines.append(f"- Blockers: `{policy.get('blockers', [])}`")
    fixture = audit.get("fixture_coverage_audit_summary", {})
    lines.extend(["", "## Fixture Coverage Audit", ""])
    lines.append(f"- Passed: `{fixture.get('passed', False)}`")
    lines.append(f"- Covered categories: `{len(fixture.get('covered_categories', []))}`")
    lines.append(f"- Missing categories: `{fixture.get('missing_categories', [])}`")
    lines.append(f"- Blockers: `{fixture.get('blockers', [])}`")
    traceability = audit.get("requirements_traceability_audit_summary", {})
    lines.extend(["", "## Requirements Traceability Audit", ""])
    lines.append(f"- Passed: `{traceability.get('passed', False)}`")
    lines.append(f"- Requirements satisfied: `{traceability.get('requirements_satisfied', 0)}/{traceability.get('requirements_total', 0)}`")
    lines.append(f"- Incomplete requirement IDs: `{traceability.get('incomplete_requirement_ids', [])}`")
    lines.append(f"- Blockers: `{traceability.get('blockers', [])}`")
    risk_register = audit.get("open_risk_register_summary", {})
    lines.extend(["", "## Open Risk Register", ""])
    lines.append(f"- Passed: `{risk_register.get('passed', False)}`")
    lines.append(f"- Risk counts: `{risk_register.get('risk_counts', {})}`")
    lines.append(f"- Blockers: `{risk_register.get('blockers', [])}`")
    remediation = audit.get("risk_remediation_plan_summary", {})
    root_cause = audit.get("risk_root_cause_rollup_summary", {})
    next_cause = root_cause.get("next_root_cause", {}) if isinstance(root_cause.get("next_root_cause", {}), dict) else {}
    lines.extend(["", "## Risk Root Cause Rollup", ""])
    lines.append(f"- Passed: `{root_cause.get('passed', False)}`")
    lines.append(f"- Open risks: `{root_cause.get('open_risk_total', 0)}`")
    lines.append(f"- Root causes: `{root_cause.get('root_cause_total', 0)}`")
    lines.append(f"- Next root cause: `{next_cause.get('cause_id', '')}`")
    lines.append(f"- Blockers: `{root_cause.get('blockers', [])}`")
    lines.extend(["", "## Risk Remediation Plan", ""])
    lines.append(f"- Status: `{remediation.get('status', '')}`")
    lines.append(f"- Open risks: `{remediation.get('open_risk_total', 0)}`")
    lines.append(f"- Actions: `{remediation.get('actions_total', 0)}`")
    lines.append(f"- Dry-run only: `{remediation.get('dry_run_only', True)}`")
    lines.append(f"- Blockers: `{remediation.get('blockers', [])}`")
    path_hygiene = audit.get("path_hygiene_audit_summary", {})
    lines.extend(["", "## Path Hygiene Audit", ""])
    lines.append(f"- Passed: `{path_hygiene.get('passed', False)}`")
    lines.append(f"- Finding counts: `{path_hygiene.get('finding_counts', {})}`")
    lines.append(f"- Blockers: `{path_hygiene.get('blockers', [])}`")
    lines.append(f"- Warnings: `{path_hygiene.get('warnings', [])}`")
    plugin_preflight = audit.get("plugin_validation_preflight_summary", {})
    lines.extend(["", "## Plugin Validation Preflight", ""])
    lines.append(f"- Status: `{plugin_preflight.get('status', '')}`")
    lines.append(f"- Safe to write parameters: `{plugin_preflight.get('safe_to_write_parameters', False)}`")
    lines.append(f"- Available plugins: `{plugin_preflight.get('available_plugins_total', 0)}`")
    lines.append(f"- Missing plugins: `{plugin_preflight.get('missing_plugins_total', 0)}`")
    lines.append(f"- Blockers: `{plugin_preflight.get('blockers', [])}`")
    lines.append(f"- Warnings: `{plugin_preflight.get('warnings', [])}`")
    plugin_action_plan = audit.get("plugin_validation_action_plan_summary", {})
    next_plugin_action = plugin_action_plan.get("next_plugin_action", {}) if isinstance(plugin_action_plan.get("next_plugin_action", {}), dict) else {}
    lines.extend(["", "## Plugin Validation Action Plan", ""])
    lines.append(f"- Status: `{plugin_action_plan.get('status', '')}`")
    lines.append(f"- Safe to write parameters: `{plugin_action_plan.get('safe_to_write_parameters', False)}`")
    lines.append(f"- Plugin actions: `{plugin_action_plan.get('plugin_actions_total', 0)}`")
    lines.append(f"- Next plugin action: `{next_plugin_action.get('plugin_name', '')}:{next_plugin_action.get('action_id', '')}`")
    lines.append(f"- Blockers: `{plugin_action_plan.get('blockers', [])}`")
    lines.append(f"- Warnings: `{plugin_action_plan.get('warnings', [])}`")
    availability_resolution = audit.get("plugin_availability_resolution_plan_summary", {})
    lines.extend(["", "## Plugin Availability Resolution Plan", ""])
    lines.append(f"- Status: `{availability_resolution.get('status', '')}`")
    lines.append(f"- Unavailable plugins: `{availability_resolution.get('unavailable_plugins_total', 0)}`")
    lines.append(f"- Pending decisions: `{availability_resolution.get('pending_operator_decisions', [])}`")
    lines.append(f"- Disable manifest plugins: `{availability_resolution.get('disable_manifest_plugins_total', 0)}`")
    lines.append(f"- Blockers: `{availability_resolution.get('blockers', [])}`")
    availability_operator = audit.get("plugin_availability_operator_decision_package_summary", {})
    lines.extend(["", "## Plugin Availability Operator Decision Package", ""])
    lines.append(f"- Status: `{availability_operator.get('status', '')}`")
    lines.append(f"- Package ready: `{availability_operator.get('operator_decision_package_ready', False)}`")
    lines.append(f"- Availability decisions ready: `{availability_operator.get('availability_decisions_ready', False)}`")
    lines.append(f"- Required decisions: `{availability_operator.get('required_decisions_total', 0)}`")
    lines.append(f"- Accepted decisions: `{availability_operator.get('accepted_decisions_total', 0)}`")
    lines.append(f"- Missing decisions: `{availability_operator.get('missing_decisions', [])}`")
    lines.append(f"- Candidate manifest: `{availability_operator.get('candidate_manifest_path', '')}`")
    lines.append(f"- Accepted manifest: `{availability_operator.get('accepted_manifest_path', '')}`")
    lines.append(f"- Accepted manifest exists: `{availability_operator.get('accepted_manifest_exists', False)}`")
    lines.append(f"- Safe to write parameters: `{availability_operator.get('safe_to_write_parameters', False)}`")
    lines.append(f"- Blockers: `{availability_operator.get('blockers', [])}`")
    lines.append(f"- Warnings: `{availability_operator.get('warnings', [])}`")
    availability_decision = audit.get("plugin_availability_decision_gate_summary", {})
    lines.extend(["", "## Plugin Availability Decision Gate", ""])
    lines.append(f"- Status: `{availability_decision.get('status', '')}`")
    lines.append(f"- Decisions ready: `{availability_decision.get('availability_decisions_ready', False)}`")
    lines.append(f"- Required decisions: `{availability_decision.get('required_decisions_total', 0)}`")
    lines.append(f"- Accepted decisions: `{availability_decision.get('accepted_decisions_total', 0)}`")
    lines.append(f"- Missing decisions: `{availability_decision.get('missing_decisions', [])}`")
    lines.append(f"- Safe to write parameters: `{availability_decision.get('safe_to_write_parameters', False)}`")
    lines.append(f"- Blockers: `{availability_decision.get('blockers', [])}`")
    plugin_semantic = audit.get("plugin_semantic_validation_gate_summary", {})
    lines.extend(["", "## Plugin Semantic Validation Gate", ""])
    lines.append(f"- Semantic validation ready: `{plugin_semantic.get('semantic_validation_ready', False)}`")
    lines.append(f"- Required plugins: `{plugin_semantic.get('required_plugins_total', 0)}`")
    lines.append(f"- Validation reports: `{plugin_semantic.get('validation_reports_total', 0)}`")
    lines.append(f"- Safe controls: `{plugin_semantic.get('safe_controls_total', 0)}`")
    lines.append(f"- Blockers: `{plugin_semantic.get('blockers', [])}`")
    lines.append(f"- Warnings: `{plugin_semantic.get('warnings', [])}`")
    semantic_collection = audit.get("plugin_semantic_validation_collection_plan_summary", {})
    next_semantic_collection = semantic_collection.get("next_collection_job", {}) if isinstance(semantic_collection.get("next_collection_job", {}), dict) else {}
    lines.extend(["", "## Plugin Semantic Validation Collection Plan", ""])
    lines.append(f"- Status: `{semantic_collection.get('status', '')}`")
    lines.append(f"- Open jobs: `{semantic_collection.get('open_jobs_total', 0)}`")
    lines.append(f"- Collectable jobs: `{semantic_collection.get('collectable_jobs_total', 0)}`")
    lines.append(f"- Decision-blocked jobs: `{semantic_collection.get('decision_blocked_jobs_total', 0)}`")
    lines.append(f"- Ready to collect some in REAPER: `{semantic_collection.get('ready_to_collect_some_in_reaper', False)}`")
    lines.append(f"- All jobs resolved: `{semantic_collection.get('all_jobs_resolved', False)}`")
    lines.append(f"- Next collection job: `{next_semantic_collection.get('plugin_name', '')}:{next_semantic_collection.get('collection_action', '')}`")
    lines.append(f"- Safe to write parameters: `{semantic_collection.get('safe_to_write_parameters', False)}`")
    lines.append(f"- Blockers: `{semantic_collection.get('blockers', [])}`")
    lines.append(f"- Warnings: `{semantic_collection.get('warnings', [])}`")
    semantic_queue = audit.get("plugin_semantic_validation_queue_summary", {})
    next_queue_job = semantic_queue.get("next_queue_job", {}) if isinstance(semantic_queue.get("next_queue_job", {}), dict) else {}
    lines.extend(["", "## Plugin Semantic Validation Queue", ""])
    lines.append(f"- Status: `{semantic_queue.get('status', '')}`")
    lines.append(f"- Queue jobs: `{semantic_queue.get('queue_jobs_total', 0)}`")
    lines.append(f"- Blocked jobs: `{semantic_queue.get('blocked_jobs_total', 0)}`")
    lines.append(f"- Ready to run REAPER collection: `{semantic_queue.get('ready_to_run_reaper_collection', False)}`")
    lines.append(f"- Requires REAPER runtime: `{semantic_queue.get('requires_reaper_runtime', False)}`")
    lines.append(f"- Next queue job: `{next_queue_job.get('job_id', '')}:{next_queue_job.get('plugin_name', '')}`")
    lines.append(f"- Safe to write parameters: `{semantic_queue.get('safe_to_write_parameters', False)}`")
    lines.append(f"- Blockers: `{semantic_queue.get('blockers', [])}`")
    lines.append(f"- Warnings: `{semantic_queue.get('warnings', [])}`")
    runtime_package = audit.get("plugin_semantic_validation_runtime_collection_package_summary", {})
    lines.extend(["", "## Plugin Semantic Validation Runtime Collection Package", ""])
    lines.append(f"- Status: `{runtime_package.get('status', '')}`")
    lines.append(f"- Ready for runtime collection: `{runtime_package.get('ready_for_runtime_collection', False)}`")
    lines.append(f"- Ready for runtime evidence gate: `{runtime_package.get('ready_for_runtime_evidence_gate', False)}`")
    lines.append(f"- Collection jobs: `{runtime_package.get('collection_jobs_total', 0)}`")
    lines.append(f"- Report templates: `{runtime_package.get('report_templates_total', 0)}`")
    lines.append(f"- Target reports existing: `{runtime_package.get('target_reports_existing_total', 0)}`")
    lines.append(f"- Target reports missing: `{runtime_package.get('target_reports_missing_total', 0)}`")
    lines.append(f"- Blocked queue jobs: `{runtime_package.get('blocked_queue_jobs_total', 0)}`")
    lines.append(f"- Manifest candidate: `{runtime_package.get('manifest_candidate_path', '')}`")
    lines.append(f"- Report template dir: `{runtime_package.get('report_template_dir', '')}`")
    lines.append(f"- Safe to write parameters: `{runtime_package.get('safe_to_write_parameters', False)}`")
    lines.append(f"- Blockers: `{runtime_package.get('blockers', [])}`")
    lines.append(f"- Warnings: `{runtime_package.get('warnings', [])}`")
    runtime_observation = audit.get("plugin_semantic_validation_runtime_observation_gate_summary", {})
    next_observation_blocked = (
        runtime_observation.get("next_blocked_observation", {})
        if isinstance(runtime_observation.get("next_blocked_observation", {}), dict)
        else {}
    )
    lines.extend(["", "## Plugin Semantic Validation Runtime Observation Gate", ""])
    lines.append(f"- Status: `{runtime_observation.get('status', '')}`")
    lines.append(f"- Runtime observations ready: `{runtime_observation.get('runtime_observations_ready', False)}`")
    lines.append(f"- Ready for manual report authoring: `{runtime_observation.get('ready_for_manual_report_authoring', False)}`")
    lines.append(f"- Ready for runtime evidence gate: `{runtime_observation.get('ready_for_runtime_evidence_gate', False)}`")
    lines.append(f"- Collector jobs: `{runtime_observation.get('collector_jobs_total', 0)}`")
    lines.append(f"- Accepted observations: `{runtime_observation.get('accepted_observations_total', 0)}`")
    lines.append(f"- Blocked observations: `{runtime_observation.get('blocked_observations_total', 0)}`")
    lines.append(f"- Blocked queue jobs: `{runtime_observation.get('blocked_queue_jobs_total', 0)}`")
    lines.append(f"- Next blocked observation: `{next_observation_blocked.get('job_id', '')}:{next_observation_blocked.get('plugin_name', '')}`")
    lines.append(f"- Safe to write parameters: `{runtime_observation.get('safe_to_write_parameters', False)}`")
    lines.append(f"- Creates validation reports: `{runtime_observation.get('creates_validation_reports', False)}`")
    lines.append(f"- Blockers: `{runtime_observation.get('blockers', [])}`")
    lines.append(f"- Warnings: `{runtime_observation.get('warnings', [])}`")
    runtime_observation_provenance = audit.get("plugin_semantic_validation_runtime_observation_provenance_gate_summary", {})
    provenance_counts = (
        runtime_observation_provenance.get("counts", {})
        if isinstance(runtime_observation_provenance.get("counts", {}), dict)
        else {}
    )
    lines.extend(["", "## Plugin Semantic Validation Runtime Observation Provenance Gate", ""])
    lines.append(f"- Status: `{runtime_observation_provenance.get('status', '')}`")
    lines.append(f"- Passed: `{runtime_observation_provenance.get('passed', False)}`")
    lines.append(
        f"- Expected packet ready: `{runtime_observation_provenance.get('expected_observation_provenance_packet_ready', False)}`"
    )
    lines.append(f"- Observed provenance ready: `{runtime_observation_provenance.get('observed_runtime_provenance_ready', False)}`")
    lines.append(f"- Ready for manual report authoring: `{runtime_observation_provenance.get('ready_for_manual_report_authoring', False)}`")
    lines.append(f"- Observations existing: `{provenance_counts.get('observations_existing_total', 0)}`")
    lines.append(f"- Observations missing: `{provenance_counts.get('observations_missing_total', 0)}`")
    lines.append(f"- Observations verified: `{provenance_counts.get('observations_provenance_verified_total', 0)}`")
    lines.append(f"- Safe to write parameters: `{runtime_observation_provenance.get('safe_to_write_parameters', False)}`")
    lines.append(f"- Creates validation reports: `{runtime_observation_provenance.get('creates_validation_reports', False)}`")
    lines.append(f"- Blockers: `{runtime_observation_provenance.get('blockers', [])}`")
    lines.append(f"- Warnings: `{runtime_observation_provenance.get('warnings', [])}`")
    runtime_authoring = audit.get("plugin_semantic_validation_runtime_report_authoring_package_summary", {})
    lines.extend(["", "## Plugin Semantic Validation Runtime Report Authoring Package", ""])
    lines.append(f"- Status: `{runtime_authoring.get('status', '')}`")
    lines.append(f"- Package ready: `{runtime_authoring.get('runtime_report_authoring_package_ready', False)}`")
    lines.append(f"- Ready for manual report authoring: `{runtime_authoring.get('ready_for_manual_report_authoring', False)}`")
    lines.append(f"- Ready for runtime evidence gate: `{runtime_authoring.get('ready_for_runtime_evidence_gate', False)}`")
    lines.append(f"- Accepted observations: `{runtime_authoring.get('accepted_observations_total', 0)}`")
    lines.append(f"- Templates: `{runtime_authoring.get('templates_total', 0)}`")
    lines.append(f"- Template dir: `{runtime_authoring.get('template_dir', '')}`")
    lines.append(f"- Checklist: `{runtime_authoring.get('checklist_path', '')}`")
    lines.append(f"- Safe to write parameters: `{runtime_authoring.get('safe_to_write_parameters', False)}`")
    lines.append(f"- Creates validation reports: `{runtime_authoring.get('creates_validation_reports', False)}`")
    lines.append(f"- Writes analysis reports: `{runtime_authoring.get('writes_analysis_reports', False)}`")
    lines.append(f"- Blockers: `{runtime_authoring.get('blockers', [])}`")
    lines.append(f"- Warnings: `{runtime_authoring.get('warnings', [])}`")
    runtime_authoring_gate = audit.get("plugin_semantic_validation_runtime_report_authoring_gate_summary", {})
    lines.extend(["", "## Plugin Semantic Validation Runtime Report Authoring Gate", ""])
    lines.append(f"- Status: `{runtime_authoring_gate.get('status', '')}`")
    lines.append(f"- Candidates ready: `{runtime_authoring_gate.get('authoring_candidates_ready', False)}`")
    lines.append(f"- Ready for operator promotion: `{runtime_authoring_gate.get('ready_for_operator_promotion', False)}`")
    lines.append(f"- Ready for runtime evidence gate: `{runtime_authoring_gate.get('ready_for_runtime_evidence_gate', False)}`")
    lines.append(f"- Templates: `{runtime_authoring_gate.get('templates_total', 0)}`")
    lines.append(f"- Candidate reports: `{runtime_authoring_gate.get('candidate_reports_total', 0)}`")
    lines.append(f"- Accepted candidates: `{runtime_authoring_gate.get('accepted_candidates_total', 0)}`")
    lines.append(f"- Candidate dir: `{runtime_authoring_gate.get('candidate_dir', '')}`")
    lines.append(f"- Promotion checklist: `{runtime_authoring_gate.get('promotion_checklist_path', '')}`")
    lines.append(f"- Manifest candidate: `{runtime_authoring_gate.get('manifest_candidate_path', '')}`")
    lines.append(f"- Safe to write parameters: `{runtime_authoring_gate.get('safe_to_write_parameters', False)}`")
    lines.append(f"- Writes analysis reports: `{runtime_authoring_gate.get('writes_analysis_reports', False)}`")
    lines.append(f"- Candidate reports are validation evidence: `{runtime_authoring_gate.get('candidate_reports_are_validation_evidence', False)}`")
    lines.append(f"- Blockers: `{runtime_authoring_gate.get('blockers', [])}`")
    lines.append(f"- Warnings: `{runtime_authoring_gate.get('warnings', [])}`")
    runtime_evidence = audit.get("plugin_semantic_validation_runtime_evidence_gate_summary", {})
    next_runtime_blocked = runtime_evidence.get("next_blocked_job", {}) if isinstance(runtime_evidence.get("next_blocked_job", {}), dict) else {}
    lines.extend(["", "## Plugin Semantic Validation Runtime Evidence Gate", ""])
    lines.append(f"- Status: `{runtime_evidence.get('status', '')}`")
    lines.append(f"- Runtime evidence ready: `{runtime_evidence.get('runtime_evidence_ready', False)}`")
    lines.append(f"- Ready for semantic gate rerun: `{runtime_evidence.get('ready_for_semantic_gate_rerun', False)}`")
    lines.append(f"- Queue jobs: `{runtime_evidence.get('queue_jobs_total', 0)}`")
    lines.append(f"- Accepted jobs: `{runtime_evidence.get('accepted_jobs_total', 0)}`")
    lines.append(f"- Blocked jobs: `{runtime_evidence.get('blocked_jobs_total', 0)}`")
    lines.append(f"- Blocked queue jobs: `{runtime_evidence.get('blocked_queue_jobs_total', 0)}`")
    lines.append(f"- Next blocked job: `{next_runtime_blocked.get('job_id', '')}:{next_runtime_blocked.get('plugin_name', '')}`")
    lines.append(f"- Safe to write parameters: `{runtime_evidence.get('safe_to_write_parameters', False)}`")
    lines.append(f"- Blockers: `{runtime_evidence.get('blockers', [])}`")
    lines.append(f"- Warnings: `{runtime_evidence.get('warnings', [])}`")
    source_handoff = audit.get("source_handoff_readiness_summary", {})
    lines.extend(["", "## Source Handoff Readiness", ""])
    lines.append(f"- Stem requests: `{source_handoff.get('stem_requests_total', 0)}`")
    lines.append(f"- Manual review tracks: `{source_handoff.get('manual_review_tracks_total', 0)}`")
    lines.append(f"- Source files present: `{source_handoff.get('source_files_present_total', 0)}/{source_handoff.get('source_files_total', 0)}`")
    lines.append(f"- Accepted export source present: `{source_handoff.get('accepted_export_source_present', False)}`")
    lines.append(f"- Automatic processing ready: `{source_handoff.get('automatic_processing_ready', False)}`")
    lines.append(f"- Blockers: `{source_handoff.get('blockers', [])}`")
    lines.append(f"- Warnings: `{source_handoff.get('warnings', [])}`")
    source_acceptance = audit.get("source_acceptance_gate_summary", {})
    lines.extend(["", "## Source Acceptance Gate", ""])
    lines.append(f"- Accepted export source ready: `{source_acceptance.get('accepted_export_source_ready', False)}`")
    lines.append(f"- Accepted stem sources: `{source_acceptance.get('accepted_stem_sources_total', 0)}`")
    lines.append(f"- Candidate sources: `{source_acceptance.get('candidate_sources_total', 0)}`")
    lines.append(f"- Blockers: `{source_acceptance.get('blockers', [])}`")
    lines.append(f"- Warnings: `{source_acceptance.get('warnings', [])}`")
    rollback_evidence = audit.get("rollback_evidence_gate_summary", {})
    lines.extend(["", "## Rollback Evidence Gate", ""])
    lines.append(f"- Ready for delivery readiness: `{rollback_evidence.get('ready_for_delivery_readiness', False)}`")
    lines.append(f"- Original tracks protected: `{rollback_evidence.get('original_tracks_protected', False)}`")
    lines.append(f"- Original master protected: `{rollback_evidence.get('original_master_protected', False)}`")
    lines.append(f"- Rollback entries: `{rollback_evidence.get('rollback_entries_total', 0)}`")
    lines.append(f"- Safe entries: `{rollback_evidence.get('safe_entries_total', 0)}`")
    lines.append(f"- Blockers: `{rollback_evidence.get('blockers', [])}`")
    lines.append(f"- Warnings: `{rollback_evidence.get('warnings', [])}`")
    render_evidence = audit.get("final_render_evidence_gate_summary", {})
    lines.extend(["", "## Final Render Evidence Gate", ""])
    lines.append(f"- Ready for final QC: `{render_evidence.get('ready_for_final_qc', False)}`")
    lines.append(f"- Ready for approval readiness: `{render_evidence.get('ready_for_approval_readiness', False)}`")
    lines.append(f"- Primary WAV: `{render_evidence.get('primary_wav_path', '')}`")
    lines.append(f"- Blockers: `{render_evidence.get('blockers', [])}`")
    lines.append(f"- Warnings: `{render_evidence.get('warnings', [])}`")
    final_qc_evidence = audit.get("final_qc_evidence_gate_summary", {})
    lines.extend(["", "## Final QC Evidence Gate", ""])
    lines.append(f"- Ready for delivery QC: `{final_qc_evidence.get('ready_for_delivery_qc', False)}`")
    lines.append(f"- Ready for approval readiness: `{final_qc_evidence.get('ready_for_approval_readiness', False)}`")
    lines.append(f"- Final audio: `{final_qc_evidence.get('final_audio_path', '')}`")
    lines.append(f"- Blockers: `{final_qc_evidence.get('blockers', [])}`")
    lines.append(f"- Warnings: `{final_qc_evidence.get('warnings', [])}`")
    package_evidence = audit.get("deliverable_package_evidence_gate_summary", {})
    lines.extend(["", "## Deliverable Package Evidence Gate", ""])
    lines.append(f"- Ready for delivery package: `{package_evidence.get('ready_for_delivery_package', False)}`")
    lines.append(f"- Ready for professional readiness: `{package_evidence.get('ready_for_professional_readiness', False)}`")
    lines.append(f"- ZIP valid: `{package_evidence.get('zip_valid', False)}`")
    lines.append(f"- Blockers: `{package_evidence.get('blockers', [])}`")
    lines.append(f"- Warnings: `{package_evidence.get('warnings', [])}`")
    delivery_consistency = audit.get("final_delivery_consistency_gate_summary", {})
    lines.extend(["", "## Final Delivery Consistency Gate", ""])
    lines.append(f"- Ready for delivery consistency: `{delivery_consistency.get('ready_for_delivery_consistency', False)}`")
    lines.append(f"- Ready for professional readiness: `{delivery_consistency.get('ready_for_professional_readiness', False)}`")
    lines.append(f"- Final audio: `{delivery_consistency.get('final_audio_path', '')}`")
    lines.append(f"- A/B preview: `{delivery_consistency.get('ab_preview_path', '')}`")
    lines.append(f"- Blockers: `{delivery_consistency.get('blockers', [])}`")
    lines.append(f"- Warnings: `{delivery_consistency.get('warnings', [])}`")
    artifact_signal = audit.get("artifact_signal_audit_summary", {})
    lines.extend(["", "## Artifact Signal Audit", ""])
    lines.append(f"- Artifact signal established: `{artifact_signal.get('artifact_signal_established', False)}`")
    lines.append(f"- Safe to run artifact suppression: `{artifact_signal.get('safe_to_run_artifact_suppression', False)}`")
    lines.append(f"- Usable source signals: `{artifact_signal.get('usable_source_signals', 0)}`")
    lines.append(f"- Usable metric signals: `{artifact_signal.get('usable_metric_signals', 0)}`")
    lines.append(f"- Usable feedback signal: `{artifact_signal.get('usable_feedback_signal', False)}`")
    lines.append(f"- Blockers: `{artifact_signal.get('blockers', [])}`")
    lines.append(f"- Warnings: `{artifact_signal.get('warnings', [])}`")
    artifact_evidence = audit.get("artifact_evidence_gate_summary", {})
    lines.extend(["", "## Artifact Evidence Gate", ""])
    lines.append(f"- Artifact evidence established: `{artifact_evidence.get('artifact_evidence_established', False)}`")
    lines.append(f"- Measured artifact metrics established: `{artifact_evidence.get('measured_artifact_metrics_established', False)}`")
    lines.append(f"- Ready for artifact review: `{artifact_evidence.get('ready_for_artifact_review', False)}`")
    lines.append(f"- Safe to run artifact suppression: `{artifact_evidence.get('safe_to_run_artifact_suppression', False)}`")
    lines.append(f"- Blockers: `{artifact_evidence.get('blockers', [])}`")
    lines.append(f"- Warnings: `{artifact_evidence.get('warnings', [])}`")
    ab_evidence = audit.get("ab_preview_evidence_gate_summary", {})
    loudness = ab_evidence.get("loudness_match_status", {})
    lines.extend(["", "## A/B Preview Evidence Gate", ""])
    lines.append(f"- Ready for human A/B review: `{ab_evidence.get('ready_for_human_ab_review', False)}`")
    lines.append(f"- Ready for final approval request: `{ab_evidence.get('ready_for_final_approval_request', False)}`")
    lines.append(f"- Human A/B review recorded: `{ab_evidence.get('human_ab_review_recorded', False)}`")
    lines.append(f"- Loudness metrics present: `{loudness.get('metrics_present', False)}`")
    lines.append(f"- Loudness delta after match: `{loudness.get('delta_db_after_match')}`")
    lines.append(f"- Blockers: `{ab_evidence.get('blockers', [])}`")
    lines.append(f"- Warnings: `{ab_evidence.get('warnings', [])}`")
    approval_evidence = audit.get("final_approval_evidence_gate_summary", {})
    approval_evidence_summary = approval_evidence.get("approval_summary", {})
    lines.extend(["", "## Final Approval Evidence Gate", ""])
    lines.append(f"- Ready for delivery request: `{approval_evidence.get('ready_for_delivery_request', False)}`")
    lines.append(f"- Approval pending only: `{approval_evidence.get('approval_pending_only', False)}`")
    lines.append(f"- Approved: `{approval_evidence.get('approved', False)}`")
    lines.append(f"- Review decision: `{approval_evidence.get('review_decision', '')}`")
    lines.append(f"- Loudness-matched A/B reviewed: `{approval_evidence_summary.get('loudness_matched_ab_reviewed', False)}`")
    lines.append(f"- Final accepted at matched loudness: `{approval_evidence_summary.get('final_audio_accepted_at_matched_loudness', False)}`")
    lines.append(f"- Blockers: `{approval_evidence.get('blockers', [])}`")
    lines.append(f"- Warnings: `{approval_evidence.get('warnings', [])}`")
    approval_export = audit.get("approval_export_readiness_summary", {})
    lines.extend(["", "## Approval Export Readiness", ""])
    lines.append(f"- Status: `{approval_export.get('readiness_status', '')}`")
    lines.append(f"- Ready for delivery request: `{approval_export.get('ready_for_delivery_request', False)}`")
    lines.append(f"- Ready for human approval request: `{approval_export.get('ready_for_human_approval_request', False)}`")
    lines.append(f"- Blockers: `{approval_export.get('blockers', [])}`")
    lines.append(f"- Warnings: `{approval_export.get('warnings', [])}`")
    lines.extend(["", "## Feedback", ""])
    feedback = audit.get("feedback_revision_loop", {})
    lines.append(f"- Pending unresolved: `{feedback.get('pending_unresolved_count', 0)}`")
    lines.append(f"- Resolved: `{feedback.get('resolved_feedback_count', 0)}`")
    lines.extend(["", "## Claim Language Guard", ""])
    claim_guard = audit.get("claim_language_guard", {})
    lines.append(f"- Passed: `{claim_guard.get('passed')}`")
    lines.append(f"- Findings: `{len(claim_guard.get('findings', []))}`")
    path = Path(output_dir) / "eval_reports" / "professional_readiness_audit.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
