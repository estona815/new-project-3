from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


REQUIREMENTS_TRACEABILITY_SCHEMA = "automix-requirements-traceability-audit-v1"

AUDIT_REL_PATH = Path("eval_reports/requirements_traceability_audit.json")
AUDIT_REPORT_REL_PATH = Path("eval_reports/requirements_traceability_audit.md")

REQUIREMENTS: list[dict[str, Any]] = [
    {
        "id": "REQ-01",
        "category": "safety",
        "title": "Non-destructive original protection",
        "requirement": "Original tracks and original master must not be overwritten; applied stages need rollback evidence.",
        "required_files": [
            "PIPELINE_ARCHITECTURE.md",
            "automix/orchestrator/rollback_evidence_gate.py",
            "automix/orchestrator/global_rollback_registry.py",
            "automix/orchestrator/global_safety_controller.py",
            "scripts/run_rollback_evidence_gate.py",
            "tests/test_prompt40_automix_orchestrator.py",
            "tests/test_prompt64_rollback_evidence_gate.py",
        ],
        "required_terms": {
            "PIPELINE_ARCHITECTURE.md": ["Scan-only modes do not modify", "Missing rollback metadata"],
            "automix/orchestrator/rollback_evidence_gate.py": ["ready_for_delivery_readiness", "original_tracks_not_protected", "rollback_entry_not_safe"],
            "automix/orchestrator/global_rollback_registry.py": ["original_tracks_protected", "original_master_protected"],
            "tests/test_prompt40_automix_orchestrator.py": ["applied_without_rollback_file", "dry_run"],
        },
        "supporting_reports": ["rollback/global_rollback_registry.json", "eval_reports/rollback_evidence_gate.json", "eval_reports/global_qc_summary.json"],
    },
    {
        "id": "REQ-02",
        "category": "processing_policy",
        "title": "Conservative overprocessing guard",
        "requirement": "OTT-style processing, aggressive saturation, blind widening, and original-master limiting are blocked by default.",
        "required_files": [
            "automix/safety/processing_policy_audit.py",
            "scripts/run_processing_policy_audit.py",
            "tests/test_prompt49_processing_policy_audit.py",
            "TESTING_AND_HARNESS.md",
        ],
        "required_terms": {
            "automix/safety/processing_policy_audit.py": ["ott_style_processing_blocked_by_default", "dry_wet_exceeds_conservative_cap", "master_limiter_on_original_master_blocked"],
            "tests/test_prompt49_processing_policy_audit.py": ["aggressive_saturation", "blind_stereo_widening", "original_master_limiter"],
        },
        "supporting_reports": ["eval_reports/processing_policy_audit.json"],
    },
    {
        "id": "REQ-03",
        "category": "suno_ai",
        "title": "Suno/AI artifact suppression strategy",
        "requirement": "AI/Suno artifact handling must use reduction/suppression language, conservative mode, formant protection, and human review.",
        "required_files": [
            "SUNO_AI_ARTIFACT_STRATEGY.md",
            "automix/orchestrator/artifact_evidence_gate.py",
            "automix/orchestrator/artifact_signal_audit.py",
            "automix/intent/intent_classifier.py",
            "automix/feedback/feedback_action_mapping.py",
            "scripts/run_artifact_evidence_gate.py",
            "scripts/run_artifact_signal_audit.py",
            "tests/test_prompt48_intent_classification.py",
            "tests/test_prompt61_artifact_evidence_gate.py",
            "tests/test_prompt57_artifact_signal_audit.py",
        ],
        "required_terms": {
            "SUNO_AI_ARTIFACT_STRATEGY.md": ["artifact reduction", "watery smear", "fake stereo halo", "human review required"],
            "automix/orchestrator/artifact_evidence_gate.py": ["measured_artifact_metrics_missing", "report_only_metric", "safe_to_run_artifact_suppression"],
            "automix/orchestrator/artifact_signal_audit.py": ["artifact_signal_not_established", "measured_artifact_metrics_not_established", "Zero or missing metrics"],
            "automix/intent/intent_classifier.py": ["suno_artifact_suppression", "max_artifact_focus_dry_wet", "formant_protection_required"],
            "automix/feedback/feedback_action_mapping.py": ["claim_100_percent_removal", "conservative artifact suppression"],
        },
        "supporting_reports": ["eval_reports/intent_classification.json", "eval_reports/artifact_evidence_gate.json", "eval_reports/artifact_signal_audit.json", "eval_reports/fixture_coverage_audit.json"],
    },
    {
        "id": "REQ-04",
        "category": "vocal_first",
        "title": "Vocal-first mix strategy",
        "requirement": "Lead vocal remains central; female/support layers cannot become the default lead; vocal seat carving is preferred over master limiting.",
        "required_files": [
            "VOCAL_FIRST_MIXING_STRATEGY.md",
            "automix/vocal_placement/vocal_placement_analyzer.py",
            "automix/routing/vocal_sidechain_routing.py",
            "tests/test_prompt35_vocal_placement.py",
        ],
        "required_terms": {
            "VOCAL_FIRST_MIXING_STRATEGY.md": ["lead vocal", "support layers", "Vocal Seat Carving"],
            "tests/test_prompt35_vocal_placement.py": ["masking_2k_5k", "sibilance_conflict_duck_db"],
        },
        "supporting_reports": ["eval_reports/final_vocal_space_eval_metrics.json", "eval_reports/final_vocal_space_review_package_manifest.json"],
    },
    {
        "id": "REQ-05",
        "category": "feedback_loop",
        "title": "Feedback intake, action mapping, revision memory, and QC integration",
        "requirement": "User feedback is classified, mapped to dry-run actions, stored by pass, and linked to QC/A-B evidence before resolution.",
        "required_files": [
            "USER_FEEDBACK_REVISION_LOOP.md",
            "automix/feedback/feedback_intake.py",
            "automix/feedback/feedback_action_mapping.py",
            "automix/feedback/revision_memory.py",
            "automix/feedback/feedback_qc_integration.py",
            "scripts/run_feedback_revision_loop.py",
            "tests/test_prompt45_user_feedback_revision_loop.py",
        ],
        "required_terms": {
            "USER_FEEDBACK_REVISION_LOOP.md": ["measured QC", "loudness-matched A/B", "human review"],
            "automix/feedback/revision_memory.py": ["loudness_matched_ab_reviewed", "human_reviewed", "remaining_risks"],
            "tests/test_prompt45_user_feedback_revision_loop.py": ["dry_run_only", "feedback_qc_integration", "loudness_matched"],
        },
        "supporting_reports": ["review/user_feedback_revision_memory.json", "eval_reports/user_feedback_qc_integration.json"],
    },
    {
        "id": "REQ-06",
        "category": "source_intake",
        "title": "Source intake and role classification",
        "requirement": "The system classifies stem/full mix/reference/vocal roles, AI/processed-source risk, and read-only safety before processing.",
        "required_files": [
            "automix/real_project/real_project_scan_only.py",
            "automix/orchestrator/source_acceptance_gate.py",
            "automix/orchestrator/source_handoff_readiness.py",
            "automix/analyze_ai_pitch_source.py",
            "scripts/run_real_project_scan_only.py",
            "scripts/run_source_acceptance_gate.py",
            "scripts/run_source_handoff_readiness.py",
            "tests/test_prompt42_real_project_scan_only.py",
            "tests/test_prompt59_source_acceptance_gate.py",
            "tests/test_prompt56_source_handoff_readiness.py",
        ],
        "required_terms": {
            "automix/real_project/real_project_scan_only.py": ["ai_artifact_score", "source_safety_map", "strict_read_only"],
            "automix/orchestrator/source_acceptance_gate.py": ["explicit_source_acceptance_missing", "full_mix_source_cannot_be_accepted_for_automatic_processing", "accepted_export_source_ready"],
            "automix/orchestrator/source_handoff_readiness.py": ["accepted_export_source_missing", "stem_requests_open", "current_source_file_presence_is_not_acceptance"],
            "automix/analyze_ai_pitch_source.py": ["source_classification", "already_tuned_score", "ai_artifact_score"],
        },
        "supporting_reports": ["eval_reports/real_project_source_safety_map.json", "eval_reports/source_acceptance_gate.json", "eval_reports/source_handoff_readiness.json", "analysis_reports/orchestrator_source_classification_summary.json"],
    },
    {
        "id": "REQ-07",
        "category": "audio_diagnosis",
        "title": "Audio diagnosis metrics",
        "requirement": "Diagnosis covers loudness, true peak proxy, crest factor, spectral/harshness, vocal masking, AI artifact, stereo/phase, and limiter risk.",
        "required_files": [
            "automix/analyze_ai_pitch_source.py",
            "automix/orchestrator/final_qc_evidence_gate.py",
            "automix/mastering/premaster_safety_analyzer.py",
            "automix/vocal_placement/vocal_placement_analyzer.py",
            "scripts/run_final_qc_evidence_gate.py",
            "docs/final_export_and_delivery.md",
            "tests/test_prompt36_premaster_safety.py",
            "tests/test_prompt65_final_qc_evidence_gate.py",
        ],
        "required_terms": {
            "automix/orchestrator/final_qc_evidence_gate.py": ["final_qc_metrics_missing_or_invalid", "ready_for_delivery_qc", "true_peak", "digital_black"],
            "automix/mastering/premaster_safety_analyzer.py": ["limiter_pressure_risk", "mono_compatibility_risk", "ai_artifact_risk_profile"],
            "automix/vocal_placement/vocal_placement_analyzer.py": ["masking_profile", "sibilance", "harshness"],
            "docs/final_export_and_delivery.md": ["loudness", "true peak proxy", "AI fizz risk"],
        },
        "supporting_reports": ["eval_reports/final_qc_metrics.json", "eval_reports/final_qc_evidence_gate.json", "analysis_reports/orchestrator_premaster_analysis.json"],
    },
    {
        "id": "REQ-08",
        "category": "intent",
        "title": "Intent classification and risk scoring",
        "requirement": "Intent classification exposes confidence, source risk, vocal priority, artifact focus, overprocessing risk, dry-run state, and human review flags.",
        "required_files": [
            "automix/intent/intent_classifier.py",
            "scripts/run_intent_classifier.py",
            "docs/manual_test_plan_prompt48.md",
            "tests/test_prompt48_intent_classification.py",
        ],
        "required_terms": {
            "automix/intent/intent_classifier.py": ["source_risk_score", "vocal_priority_score", "overprocessing_risk_score", "human_review_required"],
            "docs/manual_test_plan_prompt48.md": ["confidence", "dry-run state", "human-review state"],
        },
        "supporting_reports": ["eval_reports/intent_classification.json"],
    },
    {
        "id": "REQ-09",
        "category": "plugin_chain_planning",
        "title": "Plugin fallback, parameter bounds, and clamp safety",
        "requirement": "Plugin mappings must fail closed; semantic controls need confidence, safe min/max bounds, and clamped writes.",
        "required_files": [
            "PLUGIN_FALLBACKS.md",
            "automix/plugins/plugin_adapter_schema.py",
            "automix/plugins/safe_parameter_writer.py",
            "automix/plugins/adapter_confidence_gate.py",
            "automix/plugins/plugin_semantic_validation_gate.py",
            "automix/plugins/plugin_semantic_validation_collection_plan.py",
            "automix/plugins/plugin_semantic_validation_queue.py",
            "automix/plugins/plugin_semantic_validation_runtime_collection_package.py",
            "automix/plugins/plugin_semantic_validation_runtime_collector_package.py",
            "automix/plugins/plugin_semantic_validation_runtime_observation_gate.py",
            "automix/plugins/plugin_semantic_validation_runtime_observation_provenance_gate.py",
            "automix/plugins/plugin_semantic_validation_runtime_report_authoring_package.py",
            "automix/plugins/plugin_semantic_validation_runtime_report_authoring_gate.py",
            "automix/plugins/plugin_semantic_validation_runtime_evidence_gate.py",
            "automix/plugins/plugin_semantic_validation_runtime_handoff_packet_gate.py",
            "automix/plugins/reaper_runtime_collection_operator_readiness_gate.py",
            "automix/plugins/reaper_runtime_collector_safety_audit.py",
            "automix/harness/public_pc_legacy_fixture_plan.py",
            "automix/harness/public_pc_legacy_api_regression_gate.py",
            "automix/harness/public_pc_legacy_semantic_firewall_gate.py",
            "automix/plugins/plugin_validation_preflight.py",
            "automix/plugins/plugin_validation_action_plan.py",
            "automix/plugins/plugin_availability_resolution_plan.py",
            "automix/plugins/plugin_availability_operator_decision_package.py",
            "automix/plugins/plugin_availability_operator_decision_firewall_gate.py",
            "automix/plugins/plugin_availability_decision_gate.py",
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
            "scripts/run_plugin_semantic_validation_runtime_handoff_packet_gate.py",
            "scripts/run_reaper_runtime_collection_operator_readiness_gate.py",
            "scripts/run_reaper_runtime_collector_safety_audit.py",
            "scripts/run_public_pc_legacy_fixture_plan.py",
            "scripts/run_public_pc_legacy_api_regression_gate.py",
            "scripts/run_public_pc_legacy_semantic_firewall_gate.py",
            "scripts/run_plugin_validation_preflight.py",
            "scripts/run_plugin_validation_action_plan.py",
            "scripts/run_plugin_availability_resolution_plan.py",
            "scripts/run_plugin_availability_operator_decision_package.py",
            "scripts/run_plugin_availability_operator_decision_firewall_gate.py",
            "scripts/run_plugin_availability_decision_gate.py",
            "tests/test_prompt39_plugin_intelligence.py",
            "tests/test_prompt60_plugin_semantic_validation_gate.py",
            "tests/test_prompt73_plugin_semantic_validation_collection_plan.py",
            "tests/test_prompt74_plugin_semantic_validation_queue.py",
            "tests/test_prompt76_plugin_semantic_validation_runtime_collection_package.py",
            "tests/test_prompt78_plugin_semantic_validation_runtime_collector_package.py",
            "tests/test_prompt79_plugin_semantic_validation_runtime_observation_gate.py",
            "tests/test_prompt84_plugin_semantic_validation_runtime_observation_provenance_gate.py",
            "tests/test_prompt80_plugin_semantic_validation_runtime_report_authoring_package.py",
            "tests/test_prompt81_plugin_semantic_validation_runtime_report_authoring_gate.py",
            "tests/test_prompt75_plugin_semantic_validation_runtime_evidence_gate.py",
            "tests/test_prompt82_plugin_semantic_validation_runtime_handoff_packet_gate.py",
            "tests/test_reaper_runtime_collection_operator_readiness_gate.py",
            "tests/test_reaper_runtime_collector_safety_audit.py",
            "tests/test_public_pc_legacy_fixture_plan.py",
            "tests/test_public_pc_legacy_api_regression_gate.py",
            "tests/test_public_pc_legacy_semantic_firewall_gate.py",
            "tests/test_prompt55_plugin_validation_preflight.py",
            "tests/test_prompt70_plugin_validation_action_plan.py",
            "tests/test_prompt71_plugin_availability_resolution_plan.py",
            "tests/test_prompt77_plugin_availability_operator_decision_package.py",
            "tests/test_prompt83_plugin_availability_operator_decision_firewall_gate.py",
            "tests/test_prompt72_plugin_availability_decision_gate.py",
        ],
        "required_terms": {
            "automix/plugins/plugin_adapter_schema.py": ["safe_min", "safe_max", "clamp_semantic_value"],
            "automix/plugins/safe_parameter_writer.py": ["UNKNOWN_PLUGIN_PARAMETER", "dry_run", "clamped_value"],
            "automix/plugins/plugin_semantic_validation_gate.py": ["validation_report_has_no_write_safe_controls", "validation_report_no_fake_success_missing", "semantic_validation_ready"],
            "automix/plugins/plugin_semantic_validation_collection_plan.py": ["PLUGIN_SEMANTIC_VALIDATION_COLLECTION_PLAN_SCHEMA", "REAPER-observed semantic validation", "Do not write parameters before this collection plan has no open jobs"],
            "automix/plugins/plugin_semantic_validation_queue.py": ["PLUGIN_SEMANTIC_VALIDATION_QUEUE_SCHEMA", "requires_temporary_muted_test_context", "This queue does not open REAPER"],
            "automix/plugins/plugin_semantic_validation_runtime_collection_package.py": ["PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTION_PACKAGE_SCHEMA", "PLUGIN_PARAMETER_VALIDATION_REPORT_TEMPLATE_SCHEMA", "This package does not open REAPER"],
            "automix/plugins/plugin_semantic_validation_runtime_collector_package.py": [
                "PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA",
                "collect_plugin_semantic_validation_runtime.lua",
                "requires_collector_safety_audit",
                "This collector writes raw observations only",
            ],
            "automix/plugins/plugin_semantic_validation_runtime_observation_gate.py": [
                "PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_GATE_SCHEMA",
                "runtime_observation_missing",
                "This gate validates raw collector observations only",
            ],
            "automix/plugins/plugin_semantic_validation_runtime_observation_provenance_gate.py": [
                "PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_PROVENANCE_GATE_SCHEMA",
                "expected_observation_provenance_packet_ready",
                "runtime_observation_hash_mismatch",
            ],
            "automix/plugins/plugin_semantic_validation_runtime_report_authoring_package.py": [
                "PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_PACKAGE_SCHEMA",
                "authoring_template_not_validation_evidence",
                "No files are written under automix/analysis_reports",
            ],
            "automix/plugins/plugin_semantic_validation_runtime_report_authoring_gate.py": [
                "PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_GATE_SCHEMA",
                "candidate_reports_are_validation_evidence",
                "writes no analysis_reports files",
            ],
            "automix/plugins/plugin_semantic_validation_runtime_evidence_gate.py": ["PLUGIN_SEMANTIC_VALIDATION_RUNTIME_EVIDENCE_GATE_SCHEMA", "runtime_manifest_job_missing", "This gate does not open REAPER"],
            "automix/plugins/plugin_semantic_validation_runtime_handoff_packet_gate.py": [
                "PLUGIN_SEMANTIC_VALIDATION_RUNTIME_HANDOFF_PACKET_GATE_SCHEMA",
                "operator_runtime_handoff_packet_ready",
                "required_operator_file_missing",
            ],
            "automix/plugins/reaper_runtime_collection_operator_readiness_gate.py": [
                "REAPER_RUNTIME_COLLECTION_OPERATOR_READINESS_SCHEMA",
                "ready_for_partial_operator_runtime_collection",
                "This gate does not open REAPER",
            ],
            "automix/plugins/reaper_runtime_collector_safety_audit.py": [
                "REAPER_RUNTIME_COLLECTOR_SAFETY_AUDIT_SCHEMA",
                "lua_disallowed_reaper_call",
                "temporary_probe_track_mutation_detected",
            ],
            "automix/harness/public_pc_legacy_fixture_plan.py": [
                "legacy_lua_contains_parameter_write_calls",
                "safe_to_merge_legacy_runtime_code",
                "Current fail-closed plugin semantic validation gates remain authoritative",
            ],
            "automix/harness/public_pc_legacy_api_regression_gate.py": [
                "legacy_disallowed_call_not_in_current_policy",
                "ready_to_use_negative_safety_fixtures",
                "safe_to_execute_legacy_lua_in_user_project",
            ],
            "automix/harness/public_pc_legacy_semantic_firewall_gate.py": [
                "legacy_fixtures_count_as_validation_evidence",
                "legacy_path_referenced_by_semantic_validation_report",
                "semantic_validation_inputs_clean",
            ],
            "automix/plugins/plugin_validation_preflight.py": ["safe_to_write_parameters", "availability_does_not_grant_write_safety", "semantic_parameter_validation_required"],
            "automix/plugins/plugin_validation_action_plan.py": ["PLUGIN_VALIDATION_ACTION_PLAN_SCHEMA", "next_plugin_action", "Plugin availability is not semantic write safety"],
            "automix/plugins/plugin_availability_resolution_plan.py": ["PLUGIN_AVAILABILITY_RESOLUTION_PLAN_SCHEMA", "disable_manifest_template", "Fallback candidates require their own semantic validation"],
            "automix/plugins/plugin_availability_operator_decision_package.py": ["PLUGIN_AVAILABILITY_OPERATOR_DECISION_PACKAGE_SCHEMA", "PLUGIN_AVAILABILITY_DISABLE_MANIFEST_CANDIDATE_SCHEMA", "This candidate is not accepted evidence"],
            "automix/plugins/plugin_availability_operator_decision_firewall_gate.py": [
                "PLUGIN_AVAILABILITY_OPERATOR_DECISION_FIREWALL_GATE_SCHEMA",
                "candidate_counts_as_accepted_operator_evidence",
                "accepted_operator_decision_manifest_is_candidate",
            ],
            "automix/plugins/plugin_availability_decision_gate.py": ["PLUGIN_AVAILABILITY_DECISION_GATE_SCHEMA", "operator_acknowledgement_missing", "Fallback writes remain blocked"],
            "PLUGIN_FALLBACKS.md": ["low-confidence", "must not write"],
        },
        "supporting_reports": [
            "analysis_reports/plugin_inventory_audit.json",
            "eval_reports/plugin_capability_report.md",
            "eval_reports/plugin_semantic_validation_gate.json",
            "eval_reports/plugin_semantic_validation_collection_plan.json",
            "eval_reports/plugin_semantic_validation_queue.json",
            "eval_reports/plugin_semantic_validation_runtime_collection_package.json",
            "eval_reports/plugin_semantic_validation_runtime_collector_package.json",
            "eval_reports/plugin_semantic_validation_runtime_observation_gate.json",
            "eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json",
            "eval_reports/plugin_semantic_validation_runtime_report_authoring_package.json",
            "eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.json",
            "eval_reports/plugin_semantic_validation_runtime_evidence_gate.json",
            "eval_reports/plugin_semantic_validation_runtime_handoff_packet_gate.json",
            "eval_reports/reaper_runtime_collection_operator_readiness.json",
            "eval_reports/reaper_runtime_collector_safety_audit.json",
            "eval_reports/public_pc_legacy_fixture_plan.json",
            "eval_reports/public_pc_legacy_api_regression_gate.json",
            "eval_reports/public_pc_legacy_semantic_firewall_gate.json",
            "eval_reports/plugin_validation_preflight.json",
            "eval_reports/plugin_validation_action_plan.json",
            "eval_reports/plugin_availability_resolution_plan.json",
            "eval_reports/plugin_availability_operator_decision_package.json",
            "eval_reports/plugin_availability_operator_decision_firewall_gate.json",
            "eval_reports/plugin_availability_decision_gate.json",
        ],
    },
    {
        "id": "REQ-10",
        "category": "application_render",
        "title": "Dry-run, preview-only, A/B render, and rollback gated application",
        "requirement": "FX application and render paths must support dry-run/preview-only review, level-matched A/B, and rollback before delivery.",
        "required_files": [
            "automix/orchestrator/ab_preview_evidence_gate.py",
            "automix/orchestrator/final_render_evidence_gate.py",
            "automix/orchestrator/final_qc_evidence_gate.py",
            "automix/orchestrator/rollback_evidence_gate.py",
            "automix/export/ab_preview_montage.py",
            "automix/export/final_export_state_resolver.py",
            "scripts/run_ab_preview_evidence_gate.py",
            "scripts/run_final_render_evidence_gate.py",
            "scripts/run_final_qc_evidence_gate.py",
            "scripts/run_rollback_evidence_gate.py",
            "docs/end_to_end_automix_orchestrator.md",
            "tests/test_prompt37_final_export_packaging.py",
            "tests/test_prompt62_ab_preview_evidence_gate.py",
            "tests/test_prompt63_final_render_evidence_gate.py",
            "tests/test_prompt65_final_qc_evidence_gate.py",
            "tests/test_prompt64_rollback_evidence_gate.py",
        ],
        "required_terms": {
            "automix/orchestrator/ab_preview_evidence_gate.py": ["ab_preview_loudness_match_metrics_missing", "ready_for_human_ab_review", "Human listening review"],
            "automix/orchestrator/final_render_evidence_gate.py": ["final_render_manifest_diagnostic_or_report_only", "ready_for_final_qc", "Diagnostic/report-only renders"],
            "automix/orchestrator/final_qc_evidence_gate.py": ["final_qc_has_failures", "ready_for_approval_readiness", "Measured QC does not replace"],
            "automix/orchestrator/rollback_evidence_gate.py": ["Rollback evidence does not replace final QC", "rollback_validation_missing"],
            "automix/export/ab_preview_montage.py": ["loudness_matched", "final_ab_preview_manifest"],
            "automix/export/final_export_state_resolver.py": ["rollback_safety_validation_failed", "human_review_required"],
            "docs/end_to_end_automix_orchestrator.md": ["loudness-matched A/B preview", "rollback registry"],
        },
        "supporting_reports": [
            "eval_reports/final_ab_preview_manifest.json",
            "eval_reports/ab_preview_evidence_gate.json",
            "eval_reports/final_render_evidence_gate.json",
            "eval_reports/final_qc_evidence_gate.json",
            "eval_reports/rollback_evidence_gate.json",
            "export/final_export_state.json",
        ],
    },
    {
        "id": "REQ-11",
        "category": "mastering_qc",
        "title": "Mastering QC and profile separation",
        "requirement": "Mastering distinguishes streaming/reels/AI-source/stem-rebeat profiles and checks true peak, mono compatibility, low-end, dynamics, and limiter risk.",
        "required_files": [
            "MASTERING_QC_STANDARD.md",
            "automix/mastering/premaster_profiles.py",
            "automix/mastering/premaster_policy.py",
            "tests/test_prompt36_premaster_safety.py",
        ],
        "required_terms": {
            "MASTERING_QC_STANDARD.md": ["Conservative Streaming Master", "Loud Reels Preview Master", "AI Source Repair Master", "Stem Rebeat Master"],
            "tests/test_prompt36_premaster_safety.py": ["limiter_pressure_risk", "mono_compatibility_risk", "limiter_max_gain_db"],
        },
        "supporting_reports": ["eval_reports/final_qc_metrics.json", "eval_reports/project_premaster_eval_metrics.json"],
    },
    {
        "id": "REQ-12",
        "category": "harness",
        "title": "REAPER-free harness and required fixtures",
        "requirement": "Static/unit validation runs without REAPER and covers the required synthetic audio/mock failure fixtures.",
        "required_files": [
            "TESTING_AND_HARNESS.md",
            "automix/harness/fixture_coverage_audit.py",
            "scripts/run_fixture_coverage_audit.py",
            "tests/test_prompt50_fixture_coverage_audit.py",
            "tests/automix_validation/scripts/generate_synthetic_audio_fixtures.py",
            "tests/automix_validation/scripts/generate_mock_analysis_fixtures.py",
        ],
        "required_terms": {
            "TESTING_AND_HARNESS.md": ["REAPER-Free Tests", "fixture coverage", "render failure"],
            "automix/harness/fixture_coverage_audit.py": ["over_limited_master", "feedback_mapping", "phase_issue"],
            "tests/test_prompt50_fixture_coverage_audit.py": ["required_fixture_category_missing", "missing_audio_files"],
        },
        "supporting_reports": ["eval_reports/fixture_coverage_audit.json", "validation_reports/prompt41_validation_summary.json"],
    },
    {
        "id": "REQ-13",
        "category": "docs_claims",
        "title": "Professional documentation and claim-language guard",
        "requirement": "Delivery docs exist, distinguish automation limits, avoid total-removal claims, and run unsafe-claim detection.",
        "required_files": [
            "README.md",
            "QUICKSTART.md",
            "CHANGELOG.md",
            "automix/orchestrator/claim_language_guard.py",
            "tests/test_prompt46_professional_docs.py",
            "tests/test_prompt47_professional_readiness_audit.py",
        ],
        "required_terms": {
            "README.md": ["artifact reduction", "human review required"],
            "automix/orchestrator/claim_language_guard.py": ["total_artifact_removal_claim", "unsupported_commercial_master_claim"],
            "tests/test_prompt46_professional_docs.py": ["BANNED_CLAIMS", "scripts/run_professional_readiness_audit.py"],
        },
        "supporting_reports": ["eval_reports/claim_language_guard.json", "eval_reports/professional_readiness_audit.json"],
    },
    {
        "id": "REQ-14",
        "category": "delivery_readiness",
        "title": "Delivery readiness and report inventory",
        "requirement": "Final delivery needs render/package/project-state/plugin/QC/A-B/approval/rollback/feedback evidence and a report index.",
        "required_files": [
            "automix/orchestrator/approval_export_readiness.py",
            "automix/orchestrator/final_approval_evidence_gate.py",
            "automix/orchestrator/deliverable_package_evidence_gate.py",
            "automix/orchestrator/final_delivery_consistency_gate.py",
            "automix/orchestrator/final_render_evidence_gate.py",
            "automix/orchestrator/final_qc_evidence_gate.py",
            "automix/orchestrator/rollback_evidence_gate.py",
            "automix/orchestrator/professional_readiness_audit.py",
            "automix/orchestrator/report_index.py",
            "automix/orchestrator/risk_root_cause_rollup.py",
            "scripts/run_ab_preview_evidence_gate.py",
            "scripts/run_final_approval_evidence_gate.py",
            "scripts/run_deliverable_package_evidence_gate.py",
            "scripts/run_final_delivery_consistency_gate.py",
            "scripts/run_final_render_evidence_gate.py",
            "scripts/run_final_qc_evidence_gate.py",
            "scripts/run_rollback_evidence_gate.py",
            "scripts/run_approval_export_readiness.py",
            "scripts/run_risk_root_cause_rollup.py",
            "scripts/run_professional_readiness_audit.py",
            "docs/final_export_and_delivery.md",
            "tests/test_prompt62_ab_preview_evidence_gate.py",
            "tests/test_prompt66_final_approval_evidence_gate.py",
            "tests/test_prompt67_deliverable_package_evidence_gate.py",
            "tests/test_prompt68_final_delivery_consistency_gate.py",
            "tests/test_prompt63_final_render_evidence_gate.py",
            "tests/test_prompt65_final_qc_evidence_gate.py",
            "tests/test_prompt64_rollback_evidence_gate.py",
            "tests/test_prompt58_approval_export_readiness.py",
            "tests/test_prompt47_professional_readiness_audit.py",
            "tests/test_prompt69_risk_root_cause_rollup.py",
        ],
        "required_terms": {
            "automix/orchestrator/approval_export_readiness.py": ["accepted_export_source_missing", "ab_preview_missing_or_not_loudness_matched", "final_human_approval_missing", "final_approval_evidence_not_ready"],
            "automix/orchestrator/final_approval_evidence_gate.py": ["loudness_matched_ab_review_not_recorded", "final_audio_accepted_at_matched_loudness", "This gate validates final approval evidence only"],
            "automix/orchestrator/deliverable_package_evidence_gate.py": ["ready_for_delivery_package", "deliverable_package_manifest_has_missing_files", "This gate validates deliverable package evidence only"],
            "automix/orchestrator/final_delivery_consistency_gate.py": ["ready_for_delivery_consistency", "final_qc_audio_mismatch_render_evidence_primary_wav", "This gate validates final delivery cross-report consistency only"],
            "automix/orchestrator/final_render_evidence_gate.py": ["primary_wav_render_missing", "primary_wav_path_matches_selected_export_source", "hidden_limiter"],
            "automix/orchestrator/final_qc_evidence_gate.py": ["final_audio_path_mismatch_render_evidence_primary_wav", "final_qc_true_peak_above_ceiling"],
            "automix/orchestrator/rollback_evidence_gate.py": ["rollback_registry_missing_or_invalid", "ready_for_delivery_readiness"],
            "automix/orchestrator/professional_readiness_audit.py": ["primary_wav_render_missing", "deliverable_zip_not_created", "feedback_qc_integration", "final_qc_evidence_gate"],
            "automix/orchestrator/report_index.py": ["delivery readiness", "approval_export_readiness", "validation harness"],
            "automix/orchestrator/risk_root_cause_rollup.py": ["RISK_ROOT_CAUSE_ROLLUP_SCHEMA", "root_cause_total", "This rollup compresses risk evidence into root causes"],
            "docs/final_export_and_delivery.md": ["primary WAV", "loudness-matched A/B preview", "Approval Export Readiness"],
        },
        "supporting_reports": [
            "eval_reports/approval_export_readiness.json",
            "eval_reports/final_approval_evidence_gate.json",
            "eval_reports/deliverable_package_evidence_gate.json",
            "eval_reports/final_delivery_consistency_gate.json",
            "eval_reports/ab_preview_evidence_gate.json",
            "eval_reports/final_render_evidence_gate.json",
            "eval_reports/final_qc_evidence_gate.json",
            "eval_reports/rollback_evidence_gate.json",
            "eval_reports/automix_report_index.json",
            "eval_reports/professional_readiness_audit.json",
            "eval_reports/open_risk_register.json",
            "eval_reports/risk_root_cause_rollup.json",
            "eval_reports/risk_remediation_plan.json",
        ],
    },
    {
        "id": "REQ-15",
        "category": "path_hygiene",
        "title": "Hardcoded path and handoff hygiene",
        "requirement": "Source code should avoid hardcoded local user paths, while generated reports expose local evidence paths only as auditable runtime evidence.",
        "required_files": [
            "automix/orchestrator/path_hygiene_audit.py",
            "scripts/run_path_hygiene_audit.py",
            "tests/test_prompt54_path_hygiene_audit.py",
            "TESTING_AND_HARNESS.md",
        ],
        "required_terms": {
            "automix/orchestrator/path_hygiene_audit.py": ["source_code_contains_absolute_local_path", "runtime reports may contain local evidence paths"],
            "TESTING_AND_HARNESS.md": ["path hygiene", "hardcoded local paths"],
        },
        "supporting_reports": ["eval_reports/path_hygiene_audit.json"],
    },
]


def _load_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {}, f"read_error:{path}:{exc}"
    except json.JSONDecodeError as exc:
        return {}, f"json_decode_error:{path}:{exc}"
    if not isinstance(data, dict):
        return {}, f"json_type_error:{path}:expected_object"
    return data, None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _file_evidence(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    return {
        "relative_path": rel,
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
    }


def _term_evidence(root: Path, rel: str, terms: list[str]) -> list[dict[str, Any]]:
    text = _read_text(root / rel).lower()
    return [{"term": term, "found": term.lower() in text} for term in terms]


def _report_evidence(output_dir: Path, rel: str) -> dict[str, Any]:
    path = output_dir / rel
    data: dict[str, Any] = {}
    error: str | None = None
    json_valid: bool | None = None
    if path.suffix.lower() == ".json":
        data, error = _load_json(path)
        json_valid = error is None if path.exists() else None
    summary: dict[str, Any] = {}
    if data:
        for key in ("schema", "passed", "ready_for_delivery", "safe_to_export", "qc_passed", "status", "readiness_status"):
            if key in data:
                summary[key] = data.get(key)
    return {
        "relative_path": rel,
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
        "json_valid": json_valid,
        "json_error": error,
        "summary": summary,
    }


def _evaluate_requirement(req: dict[str, Any], *, workspace_root: Path, output_dir: Path) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    files = [_file_evidence(workspace_root, rel) for rel in req.get("required_files", [])]
    for item in files:
        if not item["exists"]:
            blockers.append(f"{req['id']}:required_file_missing:{item['relative_path']}")
        elif item["size_bytes"] <= 0:
            blockers.append(f"{req['id']}:required_file_empty:{item['relative_path']}")

    term_results: dict[str, list[dict[str, Any]]] = {}
    for rel, terms in req.get("required_terms", {}).items():
        results = _term_evidence(workspace_root, rel, list(terms))
        term_results[rel] = results
        if not (workspace_root / rel).exists():
            continue
        for result in results:
            if not result["found"]:
                blockers.append(f"{req['id']}:required_term_missing:{rel}:{result['term']}")

    reports = [_report_evidence(output_dir, rel) for rel in req.get("supporting_reports", [])]
    missing_reports = [item["relative_path"] for item in reports if not item["exists"]]
    if missing_reports:
        warnings.extend(f"{req['id']}:supporting_report_missing:{rel}" for rel in missing_reports)
    for report in reports:
        if report["exists"] and report["json_valid"] is False:
            blockers.append(f"{req['id']}:supporting_report_invalid_json:{report['relative_path']}")

    status = "satisfied" if not blockers else "incomplete"
    return {
        "id": req["id"],
        "category": req["category"],
        "title": req["title"],
        "requirement": req["requirement"],
        "status": status,
        "files": files,
        "term_results": term_results,
        "supporting_reports": reports,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def build_requirements_traceability_audit(
    *,
    project_name: str,
    output_dir: Path,
    workspace_root: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    workspace_root = Path(workspace_root or Path.cwd())
    output_dir = Path(output_dir)
    results = [_evaluate_requirement(req, workspace_root=workspace_root, output_dir=output_dir) for req in REQUIREMENTS]
    blockers = sorted({blocker for result in results for blocker in result.get("blockers", [])})
    warnings = sorted({warning for result in results for warning in result.get("warnings", [])})
    satisfied = [result["id"] for result in results if result.get("status") == "satisfied"]
    incomplete = [result["id"] for result in results if result.get("status") != "satisfied"]
    category_summary: dict[str, dict[str, int]] = {}
    for result in results:
        summary = category_summary.setdefault(result["category"], {"satisfied": 0, "incomplete": 0})
        summary["satisfied" if result.get("status") == "satisfied" else "incomplete"] += 1
    audit = {
        "schema": REQUIREMENTS_TRACEABILITY_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "workspace_root": str(workspace_root),
        "output_dir": str(output_dir),
        "passed": not blockers,
        "requirements_total": len(results),
        "requirements_satisfied": len(satisfied),
        "requirements_incomplete": len(incomplete),
        "satisfied_requirement_ids": satisfied,
        "incomplete_requirement_ids": incomplete,
        "category_summary": category_summary,
        "requirement_results": results,
        "blockers": blockers,
        "warnings": warnings,
        "limits": [
            "Traceability proves implementation evidence exists; it does not prove audio quality.",
            "Runtime reports strengthen evidence but user A/B review remains required for accepted audio.",
        ],
    }
    target = output_path or output_dir / AUDIT_REL_PATH
    write_json(target, audit)
    write_requirements_traceability_report(audit, output_dir)
    return audit


def write_requirements_traceability_report(audit: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Requirements Traceability Audit",
        "",
        f"- Project: `{audit.get('project_name')}`",
        f"- Created UTC: `{audit.get('created_at')}`",
        f"- Passed: `{audit.get('passed')}`",
        f"- Requirements satisfied: `{audit.get('requirements_satisfied')}/{audit.get('requirements_total')}`",
        "",
        "This report maps the project brief requirements to current code, documentation, tests, and runtime reports. It does not prove audio quality or user acceptance.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in audit.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in audit.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Category Summary", ""])
    for category, summary in sorted(audit.get("category_summary", {}).items()):
        lines.append(f"- `{category}` satisfied `{summary.get('satisfied', 0)}`, incomplete `{summary.get('incomplete', 0)}`")
    lines.extend(["", "## Requirements", ""])
    for result in audit.get("requirement_results", []):
        lines.extend(
            [
                f"### {result.get('id')} {result.get('title')}",
                "",
                f"- Category: `{result.get('category')}`",
                f"- Status: `{result.get('status')}`",
                f"- Requirement: {result.get('requirement')}",
                f"- Blockers: `{', '.join(result.get('blockers', [])) or 'none'}`",
                f"- Warnings: `{', '.join(result.get('warnings', [])) or 'none'}`",
                "- Evidence files:",
            ]
        )
        for item in result.get("files", []):
            lines.append(f"  - `{item.get('relative_path')}` exists `{item.get('exists')}`")
        lines.append("- Supporting reports:")
        for report in result.get("supporting_reports", []):
            summary = report.get("summary", {})
            lines.append(f"  - `{report.get('relative_path')}` exists `{report.get('exists')}` summary `{summary}`")
        lines.append("")
    path = Path(output_dir) / AUDIT_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
