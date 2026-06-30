# Risk Root Cause Rollup

- Project: `project`
- Created UTC: `2026-06-05T12:48:10Z`
- Passed: `False`
- Open risks: `429`
- Root causes: `12`

This rollup compresses repeated report blockers into root causes. It does not approve audio or replace source reports.

## Root Causes

### 10. Plugin availability and semantic write validation are not ready

- Cause ID: `plugin_validation_not_ready`
- Severity: `blocker`
- Phase: `plugin_safety`
- Source risks: `146`
- Unique codes: `134`
- Categories: `['delivery_readiness', 'intent', 'plugin', 'qc']`
- Recommended next action: Run plugin preflight and semantic validation, then disable or remap unsafe plugins before any draft processing.
- Representative codes:
  - `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx:collect_reaper_observed_semantic_validation`
  - `OTT (Xfer Records):install_or_disable_unavailable_plugin`
  - `ReaComp (Cockos):rerun_or_keep_plugin_read_only`
  - `ReaComp (Cockos):validation_report_has_no_write_safe_controls`
  - `ReaComp (Cockos):validation_report_not_passed:validation_unavailable`
  - `ReaComp (Cockos):validation_report_not_safe_for_automix`
  - `ReaDelay (Cockos):rerun_or_keep_plugin_read_only`
  - `ReaDelay (Cockos):validation_report_has_no_write_safe_controls`
  - `ReaDelay (Cockos):validation_report_not_passed:validation_unavailable`
  - `ReaDelay (Cockos):validation_report_not_safe_for_automix`
  - `ReaEQ (Cockos):rerun_or_keep_plugin_read_only`
  - `ReaEQ (Cockos):validation_report_has_no_write_safe_controls`
- Acceptance criteria:
  - plugin_validation_preflight has no blockers
  - plugin_semantic_validation_gate reports ready validation evidence
  - unsafe or unavailable plugins are disabled or kept manual-review only

### 20. Accepted export source or required stems are missing

- Cause ID: `accepted_source_or_stems_missing`
- Severity: `blocker`
- Phase: `source_intake`
- Source risks: `26`
- Unique codes: `20`
- Categories: `['delivery_readiness', 'final_export', 'human_review', 'intent', 'package', 'qc', 'render', 'source']`
- Recommended next action: Collect isolated stems or record explicit acceptance for a reviewed export source before final export.
- Representative codes:
  - `accepted_export_source_missing`
  - `final_approval_evidence:final_qc_evidence:final_render_evidence:selected_export_source_path_missing`
  - `final_approval_evidence:final_render_evidence:selected_export_source_path_missing`
  - `final_qc_evidence:final_render_evidence:selected_export_source_path_missing`
  - `final_render_evidence:selected_export_source_path_missing`
  - `full_mix_unsafe_tracks:2`
  - `high_risk_track:unsafe:SOURCE full mix reference muted`
  - `high_risk_track:unsafe:V37 INSTRUMENTAL BUS free EQ pocket`
  - `no_accepted_export_source`
  - `selected_export_source_path_missing`
  - `source_acceptance:source_acceptance_candidates_missing`
  - `source_acceptance_candidates_missing`
- Acceptance criteria:
  - source_acceptance_gate confirms explicit acceptance for the export source
  - source_handoff_readiness no longer has open stem requests for automatic processing
  - full-mix/reference tracks remain manual-review only and outside the premaster path

### 30. Artifact-focused work lacks source, metric, or feedback evidence

- Cause ID: `artifact_evidence_missing`
- Severity: `blocker`
- Phase: `artifact_evidence`
- Source risks: `16`
- Unique codes: `16`
- Categories: `['artifact', 'delivery_readiness', 'intent', 'qc']`
- Recommended next action: Collect measured artifact metrics, source signal, or user feedback before artifact-focused processing.
- Representative codes:
  - `artifact_evidence:artifact_evidence_not_established`
  - `artifact_evidence:measured_artifact_metrics_missing`
  - `artifact_evidence_not_established`
  - `artifact_signal:artifact_signal_not_established`
  - `artifact_signal:measured_artifact_metrics_not_established`
  - `artifact_signal_not_established`
  - `measured_artifact_metrics_missing`
  - `feedback:feedback_baseline_is_not_user_evidence`
  - `feedback:user_artifact_feedback_missing`
  - `intent_blocker:artifact_signal_not_established`
  - `report_only_metric:final_qc.vocal_preservation.ai_fizz_score`
  - `report_only_metric:final_qc.vocal_preservation.metallic_artifact_score`
- Acceptance criteria:
  - artifact_signal_audit establishes usable source, metric, or feedback signal
  - artifact_evidence_gate separates measured evidence from report-only placeholders

### 40. Primary final WAV render evidence is missing or diagnostic-only

- Cause ID: `primary_render_missing`
- Severity: `blocker`
- Phase: `render`
- Source risks: `56`
- Unique codes: `31`
- Categories: `['ab_preview', 'delivery_readiness', 'human_review', 'package', 'qc', 'render']`
- Recommended next action: Create a real primary WAV render from the accepted source and rerun final render evidence.
- Representative codes:
  - `final_approval_evidence:final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing`
  - `final_approval_evidence:final_qc_evidence:final_render_evidence:final_export_state_not_safe`
  - `final_approval_evidence:final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only`
  - `final_approval_evidence:final_qc_evidence:final_render_evidence:primary_wav_render_missing`
  - `final_approval_evidence:final_qc_evidence:final_render_evidence_not_ready`
  - `final_approval_evidence:final_qc_evidence:final_render_manifest_primary_wav_missing`
  - `final_approval_evidence:final_render_evidence:final_export_state_not_safe`
  - `final_approval_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only`
  - `final_approval_evidence:final_render_evidence:primary_wav_render_missing`
  - `final_approval_evidence:final_render_evidence_not_ready`
  - `final_export_state_not_safe`
  - `final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing`
- Acceptance criteria:
  - final_render_manifest contains a nonzero created primary WAV
  - final_render_evidence_gate is ready for final QC
  - the render path is not the selected source path and is not diagnostic-only

### 50. Final QC evidence is missing, failed, or not linked to render evidence

- Cause ID: `final_qc_missing_or_failed`
- Severity: `blocker`
- Phase: `final_qc`
- Source risks: `48`
- Unique codes: `30`
- Categories: `['delivery_readiness', 'human_review', 'package', 'qc']`
- Recommended next action: Run final QC on the primary WAV and validate QC evidence against render evidence.
- Representative codes:
  - `files_missing:automix/eval_reports/final_qc_report.md`
  - `final_approval_evidence:final_qc_evidence:final_audio_path_not_file`
  - `final_approval_evidence:final_qc_evidence:final_qc_file_integrity_bit_depth_missing`
  - `final_approval_evidence:final_qc_evidence:final_qc_file_integrity_channels_missing`
  - `final_approval_evidence:final_qc_evidence:final_qc_file_integrity_duration_seconds_missing`
  - `final_approval_evidence:final_qc_evidence:final_qc_file_integrity_sample_rate_missing`
  - `final_approval_evidence:final_qc_evidence:final_qc_has_failures`
  - `final_approval_evidence:final_qc_evidence:final_qc_not_passed`
  - `final_approval_evidence:final_qc_evidence:final_qc_true_peak_above_ceiling`
  - `final_approval_evidence:final_qc_evidence_not_ready`
  - `final_audio_path_missing`
  - `final_audio_path_not_file`
- Acceptance criteria:
  - final_qc_metrics has qc_passed true and no failures
  - final_qc_evidence_gate is ready for delivery QC
  - QC final_audio_path matches final render evidence primary WAV

### 60. Loudness-matched A/B preview evidence is missing or invalid

- Cause ID: `ab_preview_missing_or_not_matched`
- Severity: `blocker`
- Phase: `ab_preview`
- Source risks: `63`
- Unique codes: `39`
- Categories: `['ab_preview', 'delivery_readiness', 'human_review', 'package']`
- Recommended next action: Create a measured loudness-matched A/B preview linked to the final render before approval.
- Representative codes:
  - `ab_preview_evidence:ab_preview_final_segment_missing`
  - `ab_preview_evidence:ab_preview_loudness_match_metrics_missing`
  - `ab_preview_evidence:ab_preview_manifest_has_warnings`
  - `ab_preview_evidence:ab_preview_not_created`
  - `ab_preview_evidence:ab_preview_not_loudness_matched`
  - `ab_preview_evidence:ab_preview_original_segment_missing`
  - `ab_preview_evidence:ab_preview_segments_missing`
  - `ab_preview_evidence:ab_preview_too_few_segments`
  - `ab_preview_evidence:preview_output_path_missing`
  - `ab_preview_evidence:source_final_path_missing`
  - `ab_preview_evidence:source_original_path_missing`
  - `ab_preview_evidence_gate_not_ready`
- Acceptance criteria:
  - final_ab_preview_manifest has created true and loudness_matched true
  - ab_preview_evidence_gate is ready for human A/B review
  - preview source_final matches the primary final WAV

### 70. Final human approval evidence is missing or incomplete

- Cause ID: `human_approval_missing`
- Severity: `blocker`
- Phase: `human_review`
- Source risks: `5`
- Unique codes: `4`
- Categories: `['delivery_readiness', 'human_review', 'package']`
- Recommended next action: Record matched-loudness A/B listening approval after QC and preview evidence are ready.
- Representative codes:
  - `final_approval_evidence:final_human_approval_missing`
  - `final_approval_evidence_gate_not_ready`
  - `final_approval_evidence_not_ready`
  - `final_human_approval_missing`
- Acceptance criteria:
  - final_human_approval records accepted decision, reviewer, source, stage, final audio, and preview paths
  - final_approval_evidence_gate is ready for delivery request

### 80. Deliverable ZIP/package evidence is missing or incomplete

- Cause ID: `deliverable_package_missing`
- Severity: `blocker`
- Phase: `package`
- Source risks: `8`
- Unique codes: `8`
- Categories: `['delivery_readiness', 'package']`
- Recommended next action: Build a real deliverable ZIP after final evidence is ready and validate package evidence.
- Representative codes:
  - `deliverable_package_evidence_not_ready`
  - `deliverable_package_manifest_has_missing_files`
  - `deliverable_package_not_created`
  - `deliverable_package_size_missing_or_zero`
  - `deliverable_zip_path_missing`
  - `package_created_false`
  - `package_size_bytes_missing_or_zero`
  - `zip_path_missing`
- Acceptance criteria:
  - deliverable_package_manifest has package_created true and files_missing empty
  - deliverable_package_evidence_gate confirms ZIP integrity and required evidence files
  - credential-like and raw/reference paths are excluded by default

### 90. Final delivery reports do not yet prove cross-report consistency

- Cause ID: `delivery_consistency_not_ready`
- Severity: `blocker`
- Phase: `delivery_consistency`
- Source risks: `1`
- Unique codes: `1`
- Categories: `['delivery_readiness']`
- Recommended next action: Regenerate downstream reports from the accepted source until render, QC, A/B, approval, and package evidence paths agree.
- Representative codes:
  - `final_export_state_not_safe`
- Acceptance criteria:
  - final_delivery_consistency_gate is ready
  - final audio path matches render, QC, A/B, approval, and package evidence
  - A/B preview path matches preview and approval evidence

### 999. Other open risks require manual review

- Cause ID: `other_open_risks`
- Severity: `blocker`
- Phase: `other`
- Source risks: `49`
- Unique codes: `46`
- Categories: `['delivery_readiness', 'human_review', 'intent', 'plugin', 'qc', 'source']`
- Recommended next action: Review the source report and choose the safest dry-run or manual-review action.
- Representative codes:
  - `aggressive_creative_enhancement_disabled_by_default`
  - `explicit_rebeat_stems_and_arrangement_review_required`
  - `explicit_user_approval_and_preview_required`
  - `no_safe_vocal_candidate`
  - `operator_decision_missing:OTT (Xfer Records)`
  - `operator_decision_missing:TDR Nova (Tokyo Dawn Labs)`
  - `plugin_availability_decision_manifest_missing`
  - `qc_failure_for_final_delivery`
  - `analysis_only_no_audio_recovery_rendered`
  - `audio_source_classification_not_run_no_track_audio`
  - `availability_decisions_not_ready_for_complete_collection`
  - `availability_operator_decisions_missing:2`
- Acceptance criteria:
  - the source report no longer emits this blocker or warning

### 100. Rollback or project-state protection evidence is incomplete

- Cause ID: `rollback_or_project_state_not_ready`
- Severity: `warning`
- Phase: `rollback`
- Source risks: `3`
- Unique codes: `3`
- Categories: `['rollback']`
- Recommended next action: Repair rollback registry and project-state manifests before applied-stage or delivery confidence.
- Representative codes:
  - `no_applied_stages_declared`
  - `unknown:rollback_entry:rollback_entry_points_to_global_registry`
  - `unknown:rollback_entry:rollback_stage_unknown`
- Acceptance criteria:
  - rollback_evidence_gate is ready for delivery readiness
  - project_state_manifest records original_tracks_protected true and master_unchanged true

### 110. Feedback, claim language, or policy evidence still needs review

- Cause ID: `feedback_or_claims_need_review`
- Severity: `warning`
- Phase: `review_hygiene`
- Source risks: `8`
- Unique codes: `8`
- Categories: `['harness', 'processing_policy']`
- Recommended next action: Resolve feedback and static audit blockers without inventing listening approval.
- Representative codes:
  - `chain_plan_policy_clean:final_safe_premaster_chain_plan.json`
  - `chain_plan_policy_clean:final_vocal_space_applicator_plan.json`
  - `chain_plan_policy_clean:final_vocal_space_carving_chain_plan.json`
  - `chain_plan_policy_clean:high_quality_mix_master_readiness_plan.json`
  - `chain_plan_policy_clean:project_premaster_chain_plan.json`
  - `chain_plan_policy_clean:project_reference_match_adjustment_plan.json`
  - `chain_plan_policy_clean:real_project_dry_run_chain_proposals.json`
  - `fixture_coverage_complete_static_only`
- Acceptance criteria:
  - feedback items are resolved only with measured QC and human review evidence
  - claim language guard and policy audits have no blockers
