from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOCS = [
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

BANNED_CLAIMS = [
    "100% 제거",
    "완전 제거",
    "perfect cleanup",
    "guaranteed commercial",
    "replace human",
    "total artifact removal",
    "reference matched perfectly",
]


def test_professional_delivery_docs_exist() -> None:
    missing = [name for name in REQUIRED_DOCS if not (ROOT / name).exists()]
    assert missing == []


def test_docs_cross_link_core_operating_gates() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = (ROOT / "QUICKSTART.md").read_text(encoding="utf-8")
    feedback = (ROOT / "USER_FEEDBACK_REVISION_LOOP.md").read_text(encoding="utf-8")
    assert "docs/automix_runbook.md" in readme
    assert "scripts/run_prompt41_smoke_validation.py" in quickstart
    assert "scripts/run_fixture_coverage_audit.py" in quickstart
    assert "scripts/run_requirements_traceability_audit.py" in quickstart
    assert "scripts/run_open_risk_register.py" in quickstart
    assert "scripts/run_risk_root_cause_rollup.py" in quickstart
    assert "scripts/run_risk_remediation_plan.py" in quickstart
    assert "scripts/run_path_hygiene_audit.py" in quickstart
    assert "scripts/run_ab_preview_evidence_gate.py" in quickstart
    assert "scripts/run_final_approval_evidence_gate.py" in quickstart
    assert "scripts/run_deliverable_package_evidence_gate.py" in quickstart
    assert "scripts/run_final_delivery_consistency_gate.py" in quickstart
    assert "scripts/run_final_render_evidence_gate.py" in quickstart
    assert "scripts/run_final_qc_evidence_gate.py" in quickstart
    assert "scripts/run_rollback_evidence_gate.py" in quickstart
    assert "scripts/run_source_acceptance_gate.py" in quickstart
    assert "scripts/run_artifact_evidence_gate.py" in quickstart
    assert "scripts/run_plugin_semantic_validation_gate.py" in quickstart
    assert "scripts/run_plugin_semantic_validation_collection_plan.py" in quickstart
    assert "scripts/run_plugin_semantic_validation_queue.py" in quickstart
    assert "scripts/run_plugin_semantic_validation_runtime_collection_package.py" in quickstart
    assert "scripts/run_plugin_semantic_validation_runtime_collector_package.py" in quickstart
    assert "scripts/run_plugin_semantic_validation_runtime_observation_gate.py" in quickstart
    assert "scripts/run_plugin_semantic_validation_runtime_report_authoring_package.py" in quickstart
    assert "scripts/run_plugin_semantic_validation_runtime_report_authoring_gate.py" in quickstart
    assert "scripts/run_plugin_semantic_validation_runtime_evidence_gate.py" in quickstart
    assert "scripts/run_plugin_validation_preflight.py" in quickstart
    assert "scripts/run_plugin_validation_action_plan.py" in quickstart
    assert "scripts/run_plugin_availability_resolution_plan.py" in quickstart
    assert "scripts/run_plugin_availability_operator_decision_package.py" in quickstart
    assert "scripts/run_plugin_availability_decision_gate.py" in quickstart
    assert "scripts/run_source_handoff_readiness.py" in quickstart
    assert "scripts/run_artifact_signal_audit.py" in quickstart
    assert "scripts/run_approval_export_readiness.py" in quickstart
    assert "scripts/run_intent_classifier.py" in quickstart
    assert "scripts/run_processing_policy_audit.py" in quickstart
    assert "scripts/run_feedback_revision_loop.py" in quickstart
    assert "scripts/run_final_export_packager.py" in quickstart
    assert "scripts/run_professional_readiness_audit.py" in quickstart
    assert "measured QC" in feedback
    assert "loudness-matched A/B" in feedback
    assert "human review" in feedback


def test_docs_do_not_claim_total_artifact_removal() -> None:
    offenders = []
    for name in REQUIRED_DOCS:
        text = (ROOT / name).read_text(encoding="utf-8").lower()
        for claim in BANNED_CLAIMS:
            if claim.lower() in text:
                offenders.append(f"{name}:{claim}")
    assert offenders == []


def test_docs_reference_existing_detail_docs_and_scripts() -> None:
    referenced = [
        "docs/user_feedback_revision_loop.md",
        "docs/automix_runbook.md",
        "docs/final_export_and_delivery.md",
        "scripts/run_feedback_revision_loop.py",
        "scripts/run_fixture_coverage_audit.py",
        "scripts/run_requirements_traceability_audit.py",
        "scripts/run_open_risk_register.py",
        "scripts/run_risk_root_cause_rollup.py",
        "scripts/run_risk_remediation_plan.py",
        "scripts/run_path_hygiene_audit.py",
        "scripts/run_ab_preview_evidence_gate.py",
        "scripts/run_final_approval_evidence_gate.py",
        "scripts/run_deliverable_package_evidence_gate.py",
        "scripts/run_final_delivery_consistency_gate.py",
        "scripts/run_final_render_evidence_gate.py",
        "scripts/run_final_qc_evidence_gate.py",
        "scripts/run_rollback_evidence_gate.py",
        "scripts/run_source_acceptance_gate.py",
        "scripts/run_artifact_evidence_gate.py",
        "scripts/run_plugin_semantic_validation_gate.py",
        "scripts/run_plugin_semantic_validation_collection_plan.py",
        "scripts/run_plugin_semantic_validation_queue.py",
        "scripts/run_plugin_semantic_validation_runtime_collection_package.py",
        "scripts/run_plugin_semantic_validation_runtime_collector_package.py",
        "scripts/run_plugin_semantic_validation_runtime_observation_gate.py",
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
        "scripts/run_intent_classifier.py",
        "scripts/run_processing_policy_audit.py",
        "scripts/run_automix_orchestrator.py",
        "scripts/run_final_export_packager.py",
        "scripts/run_professional_readiness_audit.py",
    ]
    missing = [path for path in referenced if not (ROOT / path).exists()]
    assert missing == []
