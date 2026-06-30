# Professional Readiness Audit

- Project: `project`
- Created UTC: `2026-06-05T12:48:26Z`
- Status: `review_required`
- Ready for delivery: `False`

## Blockers

- none

## Warnings

- `final_delivery_not_requested_readiness_is_documentation_and_gate_inventory_only`

## Evidence

- `final_export_state`: exists=`True`, json_valid=`True`
- `final_render_manifest`: exists=`True`, json_valid=`True`
- `final_render_evidence_gate`: exists=`True`, json_valid=`True`
- `deliverable_package_manifest`: exists=`True`, json_valid=`True`
- `deliverable_package_evidence_gate`: exists=`True`, json_valid=`True`
- `final_delivery_consistency_gate`: exists=`True`, json_valid=`True`
- `project_state_manifest`: exists=`True`, json_valid=`True`
- `plugin_mapping_summary`: exists=`True`, json_valid=`None`
- `final_qc_metrics`: exists=`True`, json_valid=`True`
- `final_qc_evidence_gate`: exists=`True`, json_valid=`True`
- `ab_preview_manifest`: exists=`True`, json_valid=`True`
- `ab_preview_evidence_gate`: exists=`True`, json_valid=`True`
- `global_qc_summary`: exists=`True`, json_valid=`True`
- `final_human_approval`: exists=`True`, json_valid=`True`
- `final_approval_evidence_gate`: exists=`True`, json_valid=`True`
- `feedback_revision_memory`: exists=`True`, json_valid=`True`
- `feedback_qc_integration`: exists=`True`, json_valid=`True`
- `fixture_coverage_audit`: exists=`True`, json_valid=`True`
- `requirements_traceability_audit`: exists=`True`, json_valid=`True`
- `open_risk_register`: exists=`True`, json_valid=`True`
- `risk_root_cause_rollup`: exists=`True`, json_valid=`True`
- `risk_remediation_plan`: exists=`True`, json_valid=`True`
- `path_hygiene_audit`: exists=`True`, json_valid=`True`
- `source_acceptance_gate`: exists=`True`, json_valid=`True`
- `artifact_evidence_gate`: exists=`True`, json_valid=`True`
- `plugin_semantic_validation_gate`: exists=`True`, json_valid=`True`
- `plugin_semantic_validation_collection_plan`: exists=`True`, json_valid=`True`
- `plugin_semantic_validation_queue`: exists=`True`, json_valid=`True`
- `plugin_semantic_validation_runtime_collection_package`: exists=`True`, json_valid=`True`
- `plugin_semantic_validation_runtime_collector_package`: exists=`True`, json_valid=`True`
- `plugin_semantic_validation_runtime_observation_gate`: exists=`True`, json_valid=`True`
- `plugin_semantic_validation_runtime_observation_provenance_gate`: exists=`True`, json_valid=`True`
- `plugin_semantic_validation_runtime_report_authoring_package`: exists=`True`, json_valid=`True`
- `plugin_semantic_validation_runtime_report_authoring_gate`: exists=`True`, json_valid=`True`
- `plugin_semantic_validation_runtime_evidence_gate`: exists=`True`, json_valid=`True`
- `plugin_validation_preflight`: exists=`True`, json_valid=`True`
- `plugin_validation_action_plan`: exists=`True`, json_valid=`True`
- `plugin_availability_resolution_plan`: exists=`True`, json_valid=`True`
- `plugin_availability_operator_decision_package`: exists=`True`, json_valid=`True`
- `plugin_availability_decision_gate`: exists=`True`, json_valid=`True`
- `source_handoff_readiness`: exists=`True`, json_valid=`True`
- `artifact_signal_audit`: exists=`True`, json_valid=`True`
- `approval_export_readiness`: exists=`True`, json_valid=`True`
- `intent_classification`: exists=`True`, json_valid=`True`
- `processing_policy_audit`: exists=`True`, json_valid=`True`
- `report_index`: exists=`True`, json_valid=`True`
- `global_rollback_registry`: exists=`True`, json_valid=`True`
- `rollback_evidence_gate`: exists=`True`, json_valid=`True`

## Delivery Evidence Summary

- Primary WAV renders: `0`
- Render failures: `[]`
- Final render evidence ready: `False`
- Final QC passed: `False`
- Final QC failures: `['qc_not_requested_or_primary_wav_missing']`
- Final QC evidence ready: `False`
- ZIP package created: `False`
- ZIP package size bytes: `0`
- Packaged files missing: `['automix/eval_reports/final_qc_report.md']`
- Deliverable package evidence ready: `False`
- Deliverable ZIP valid: `False`
- Final delivery consistency ready: `False`
- Original tracks protected: `True`
- Master unchanged: `True`
- Plugin summary bytes: `555`
- A/B preview created: `False`
- A/B preview loudness matched: `False`
- A/B preview evidence ready: `False`
- Final approval evidence ready: `False`
- Rollback validation passed: `True`
- Rollback evidence ready: `True`

## Intent Classification

- Status: `review_required`
- Recommended primary intent: `conservative_cleanup`
- Safe next mode: `validate_plugin_mappings`
- Safe draft intents: `[]`

## Processing Policy Audit

- Passed: `True`
- Plans checked: `7`
- Blockers: `[]`

## Fixture Coverage Audit

- Passed: `True`
- Covered categories: `17`
- Missing categories: `[]`
- Blockers: `[]`

## Requirements Traceability Audit

- Passed: `True`
- Requirements satisfied: `15/15`
- Incomplete requirement IDs: `[]`
- Blockers: `[]`

## Open Risk Register

- Passed: `False`
- Risk counts: `{'blocker': 308, 'info': 1, 'review': 2, 'warning': 118}`
- Blockers: `['ab_preview_final_segment_missing', 'ab_preview_loudness_match_metrics_missing', 'ab_preview_manifest_has_warnings', 'ab_preview_not_created', 'ab_preview_not_loudness_matched', 'ab_preview_original_segment_missing', 'ab_preview_segments_missing', 'ab_preview_too_few_segments', 'preview_output_path_missing', 'source_final_path_missing', 'source_original_path_missing', 'artifact_evidence_not_established', 'measured_artifact_metrics_missing', 'ab_preview_evidence:ab_preview_final_segment_missing', 'ab_preview_evidence:ab_preview_loudness_match_metrics_missing', 'ab_preview_evidence:ab_preview_manifest_has_warnings', 'ab_preview_evidence:ab_preview_not_created', 'ab_preview_evidence:ab_preview_not_loudness_matched', 'ab_preview_evidence:ab_preview_original_segment_missing', 'ab_preview_evidence:ab_preview_segments_missing', 'ab_preview_evidence:ab_preview_too_few_segments', 'ab_preview_evidence:preview_output_path_missing', 'ab_preview_evidence:source_final_path_missing', 'ab_preview_evidence:source_original_path_missing', 'ab_preview_evidence_not_ready', 'ab_preview_missing_or_not_loudness_matched', 'accepted_export_source_missing', 'artifact_evidence:artifact_evidence_not_established', 'artifact_evidence:measured_artifact_metrics_missing', 'artifact_signal:artifact_signal_not_established', 'artifact_signal:measured_artifact_metrics_not_established', 'final_human_approval_missing', 'final_qc_evidence:final_audio_path_not_file', 'final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing', 'final_qc_evidence:final_qc_file_integrity_bit_depth_missing', 'final_qc_evidence:final_qc_file_integrity_channels_missing', 'final_qc_evidence:final_qc_file_integrity_duration_seconds_missing', 'final_qc_evidence:final_qc_file_integrity_sample_rate_missing', 'final_qc_evidence:final_qc_has_failures', 'final_qc_evidence:final_qc_not_passed', 'final_qc_evidence:final_qc_true_peak_above_ceiling', 'final_qc_evidence:final_render_evidence:final_export_state_not_safe', 'final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_qc_evidence:final_render_evidence:primary_wav_render_missing', 'final_qc_evidence:final_render_evidence:selected_export_source_path_missing', 'final_qc_evidence:final_render_evidence_not_ready', 'final_qc_evidence:final_render_manifest_primary_wav_missing', 'final_qc_evidence_not_ready', 'final_qc_missing_or_failed', 'final_render_evidence:final_export_state_not_safe', 'final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_render_evidence:primary_wav_render_missing', 'final_render_evidence:selected_export_source_path_missing', 'final_render_evidence_not_ready', 'final_render_missing_or_diagnostic_only', 'plugin_semantic_validation:ReaComp (Cockos):validation_report_has_no_write_safe_controls', 'plugin_semantic_validation:ReaComp (Cockos):validation_report_not_passed:validation_unavailable', 'plugin_semantic_validation:ReaComp (Cockos):validation_report_not_safe_for_automix', 'plugin_semantic_validation:ReaDelay (Cockos):validation_report_has_no_write_safe_controls', 'plugin_semantic_validation:ReaDelay (Cockos):validation_report_not_passed:validation_unavailable', 'plugin_semantic_validation:ReaDelay (Cockos):validation_report_not_safe_for_automix', 'plugin_semantic_validation:ReaEQ (Cockos):validation_report_has_no_write_safe_controls', 'plugin_semantic_validation:ReaEQ (Cockos):validation_report_not_passed:validation_unavailable', 'plugin_semantic_validation:ReaEQ (Cockos):validation_report_not_safe_for_automix', 'plugin_semantic_validation:no_passed_semantic_validation_report:ReaComp (Cockos)', 'plugin_semantic_validation:no_passed_semantic_validation_report:ReaDelay (Cockos)', 'plugin_semantic_validation:no_passed_semantic_validation_report:ReaEQ (Cockos)', 'plugin_semantic_validation:semantic_validation_passed_reports_missing', 'plugin_semantic_validation:validation_report_missing:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx', 'plugin_semantic_validation:validation_report_missing:OTT (Xfer Records)', 'plugin_semantic_validation:validation_report_missing:ReaVerbate (Cockos)', 'plugin_semantic_validation:validation_report_missing:TDR Nova (Tokyo Dawn Labs)', 'plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_air_guard.jsfx', 'plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx', 'plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_output_guard.jsfx', 'plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_presence_enhancer.jsfx', 'plugin_validation_preflight:required_plugin_availability_missing:OTT (Xfer Records)', 'plugin_validation_preflight:required_plugin_availability_missing:TDR Nova (Tokyo Dawn Labs)', 'plugin_validation_preflight:semantic_parameter_validation_required', 'source_acceptance:source_acceptance_candidates_missing', 'source_handoff:current_source_file_missing:V37 RETURN ReaDelay filtered throw', 'source_handoff:current_source_file_missing:V37 RETURN ReaVerbate dark send', 'source_handoff:full_mix_unsafe_tracks:2', 'source_handoff:stem_requests_open:2', 'ab_preview_evidence_not_ready', 'ab_preview_output_path_missing', 'deliverable_package_evidence_not_ready', 'final_approval_evidence_not_ready', 'final_audio_path_missing', 'final_export_state_not_safe', 'final_qc_evidence_not_ready', 'final_render_evidence_not_ready', 'final_render_evidence_primary_wav_missing', 'final_render_manifest_primary_wav_missing', 'no_accepted_export_source', 'ab_preview_evidence:ab_preview_final_segment_missing', 'ab_preview_evidence:ab_preview_loudness_match_metrics_missing', 'ab_preview_evidence:ab_preview_manifest_has_warnings', 'ab_preview_evidence:ab_preview_not_created', 'ab_preview_evidence:ab_preview_not_loudness_matched', 'ab_preview_evidence:ab_preview_original_segment_missing', 'ab_preview_evidence:ab_preview_segments_missing', 'ab_preview_evidence:ab_preview_too_few_segments', 'ab_preview_evidence:preview_output_path_missing', 'ab_preview_evidence:source_final_path_missing', 'ab_preview_evidence:source_original_path_missing', 'ab_preview_evidence_not_ready', 'final_human_approval_missing', 'final_qc_evidence:final_audio_path_not_file', 'final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing', 'final_qc_evidence:final_qc_file_integrity_bit_depth_missing', 'final_qc_evidence:final_qc_file_integrity_channels_missing', 'final_qc_evidence:final_qc_file_integrity_duration_seconds_missing', 'final_qc_evidence:final_qc_file_integrity_sample_rate_missing', 'final_qc_evidence:final_qc_has_failures', 'final_qc_evidence:final_qc_not_passed', 'final_qc_evidence:final_qc_true_peak_above_ceiling', 'final_qc_evidence:final_render_evidence:final_export_state_not_safe', 'final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_qc_evidence:final_render_evidence:primary_wav_render_missing', 'final_qc_evidence:final_render_evidence:selected_export_source_path_missing', 'final_qc_evidence:final_render_evidence_not_ready', 'final_qc_evidence:final_render_manifest_primary_wav_missing', 'final_qc_evidence_not_ready', 'final_render_evidence:final_export_state_not_safe', 'final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_render_evidence:primary_wav_render_missing', 'final_render_evidence:selected_export_source_path_missing', 'final_render_evidence_not_ready', 'aggressive_creative_enhancement_disabled_by_default', 'artifact_signal_not_established', 'explicit_rebeat_stems_and_arrangement_review_required', 'explicit_user_approval_and_preview_required', 'no_safe_vocal_candidate', 'stems_not_ready', 'validated_plugin_mapping_required', 'ab_preview_evidence:ab_preview_final_segment_missing', 'ab_preview_evidence:ab_preview_loudness_match_metrics_missing', 'ab_preview_evidence:ab_preview_manifest_has_warnings', 'ab_preview_evidence:ab_preview_not_created', 'ab_preview_evidence:ab_preview_not_loudness_matched', 'ab_preview_evidence:ab_preview_original_segment_missing', 'ab_preview_evidence:ab_preview_segments_missing', 'ab_preview_evidence:ab_preview_too_few_segments', 'ab_preview_evidence:preview_output_path_missing', 'ab_preview_evidence:source_final_path_missing', 'ab_preview_evidence:source_original_path_missing', 'ab_preview_evidence_gate_not_ready', 'deliverable_package_manifest_has_missing_files', 'deliverable_package_not_created', 'deliverable_package_size_missing_or_zero', 'deliverable_zip_path_missing', 'final_approval_evidence:ab_preview_evidence:ab_preview_final_segment_missing', 'final_approval_evidence:ab_preview_evidence:ab_preview_loudness_match_metrics_missing', 'final_approval_evidence:ab_preview_evidence:ab_preview_manifest_has_warnings', 'final_approval_evidence:ab_preview_evidence:ab_preview_not_created', 'final_approval_evidence:ab_preview_evidence:ab_preview_not_loudness_matched', 'final_approval_evidence:ab_preview_evidence:ab_preview_original_segment_missing', 'final_approval_evidence:ab_preview_evidence:ab_preview_segments_missing', 'final_approval_evidence:ab_preview_evidence:ab_preview_too_few_segments', 'final_approval_evidence:ab_preview_evidence:preview_output_path_missing', 'final_approval_evidence:ab_preview_evidence:source_final_path_missing', 'final_approval_evidence:ab_preview_evidence:source_original_path_missing', 'final_approval_evidence:ab_preview_evidence_not_ready', 'final_approval_evidence:final_human_approval_missing', 'final_approval_evidence:final_qc_evidence:final_audio_path_not_file', 'final_approval_evidence:final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing', 'final_approval_evidence:final_qc_evidence:final_qc_file_integrity_bit_depth_missing', 'final_approval_evidence:final_qc_evidence:final_qc_file_integrity_channels_missing', 'final_approval_evidence:final_qc_evidence:final_qc_file_integrity_duration_seconds_missing', 'final_approval_evidence:final_qc_evidence:final_qc_file_integrity_sample_rate_missing', 'final_approval_evidence:final_qc_evidence:final_qc_has_failures', 'final_approval_evidence:final_qc_evidence:final_qc_not_passed', 'final_approval_evidence:final_qc_evidence:final_qc_true_peak_above_ceiling', 'final_approval_evidence:final_qc_evidence:final_render_evidence:final_export_state_not_safe', 'final_approval_evidence:final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_approval_evidence:final_qc_evidence:final_render_evidence:primary_wav_render_missing', 'final_approval_evidence:final_qc_evidence:final_render_evidence:selected_export_source_path_missing', 'final_approval_evidence:final_qc_evidence:final_render_evidence_not_ready', 'final_approval_evidence:final_qc_evidence:final_render_manifest_primary_wav_missing', 'final_approval_evidence:final_qc_evidence_not_ready', 'final_approval_evidence:final_render_evidence:final_export_state_not_safe', 'final_approval_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_approval_evidence:final_render_evidence:primary_wav_render_missing', 'final_approval_evidence:final_render_evidence:selected_export_source_path_missing', 'final_approval_evidence:final_render_evidence_not_ready', 'final_approval_evidence_gate_not_ready', 'final_qc_evidence:final_audio_path_not_file', 'final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing', 'final_qc_evidence:final_qc_file_integrity_bit_depth_missing', 'final_qc_evidence:final_qc_file_integrity_channels_missing', 'final_qc_evidence:final_qc_file_integrity_duration_seconds_missing', 'final_qc_evidence:final_qc_file_integrity_sample_rate_missing', 'final_qc_evidence:final_qc_has_failures', 'final_qc_evidence:final_qc_not_passed', 'final_qc_evidence:final_qc_true_peak_above_ceiling', 'final_qc_evidence:final_render_evidence:final_export_state_not_safe', 'final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_qc_evidence:final_render_evidence:primary_wav_render_missing', 'final_qc_evidence:final_render_evidence:selected_export_source_path_missing', 'final_qc_evidence:final_render_evidence_not_ready', 'final_qc_evidence:final_render_manifest_primary_wav_missing', 'final_qc_evidence_gate_not_ready', 'final_render_evidence:final_export_state_not_safe', 'final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_render_evidence:primary_wav_render_missing', 'final_render_evidence:selected_export_source_path_missing', 'final_render_evidence_gate_not_ready', 'files_missing:automix/eval_reports/final_qc_report.md', 'package_created_false', 'package_size_bytes_missing_or_zero', 'zip_path_missing', 'operator_decision_missing:OTT (Xfer Records)', 'operator_decision_missing:TDR Nova (Tokyo Dawn Labs)', 'plugin_availability_decision_manifest_missing', 'availability_decision_missing:OTT (Xfer Records)', 'availability_decision_missing:TDR Nova (Tokyo Dawn Labs)', 'ReaComp (Cockos):validation_report_has_no_write_safe_controls', 'ReaComp (Cockos):validation_report_not_passed:validation_unavailable', 'ReaComp (Cockos):validation_report_not_safe_for_automix', 'ReaDelay (Cockos):validation_report_has_no_write_safe_controls', 'ReaDelay (Cockos):validation_report_not_passed:validation_unavailable', 'ReaDelay (Cockos):validation_report_not_safe_for_automix', 'ReaEQ (Cockos):validation_report_has_no_write_safe_controls', 'ReaEQ (Cockos):validation_report_not_passed:validation_unavailable', 'ReaEQ (Cockos):validation_report_not_safe_for_automix', 'no_passed_semantic_validation_report:ReaComp (Cockos)', 'no_passed_semantic_validation_report:ReaDelay (Cockos)', 'no_passed_semantic_validation_report:ReaEQ (Cockos)', 'semantic_validation_passed_reports_missing', 'validation_report_missing:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx', 'validation_report_missing:OTT (Xfer Records)', 'validation_report_missing:ReaVerbate (Cockos)', 'validation_report_missing:TDR Nova (Tokyo Dawn Labs)', 'validation_report_missing:Vocal Clarity Repair/vocal_air_guard.jsfx', 'validation_report_missing:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx', 'validation_report_missing:Vocal Clarity Repair/vocal_output_guard.jsfx', 'validation_report_missing:Vocal Clarity Repair/vocal_presence_enhancer.jsfx', 'collection_job_blocked:OTT (Xfer Records):availability_decision_missing:OTT (Xfer Records)', 'collection_job_blocked:TDR Nova (Tokyo Dawn Labs):availability_decision_missing:TDR Nova (Tokyo Dawn Labs)', 'plugin_semantic_validation_runtime_manifest_missing', 'runtime_manifest_job_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx', 'runtime_manifest_job_missing:semantic_validation_02_reaverbate_cockos', 'runtime_manifest_job_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx', 'runtime_manifest_job_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx', 'runtime_manifest_job_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx', 'runtime_manifest_job_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx', 'runtime_manifest_job_missing:semantic_validation_07_reacomp_cockos', 'runtime_manifest_job_missing:semantic_validation_08_readelay_cockos', 'runtime_manifest_job_missing:semantic_validation_09_reaeq_cockos', 'runtime_validation_report_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx', 'runtime_validation_report_missing:semantic_validation_02_reaverbate_cockos', 'runtime_validation_report_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx', 'runtime_validation_report_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx', 'runtime_validation_report_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx', 'runtime_validation_report_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx', 'runtime_validation_report_missing:semantic_validation_07_reacomp_cockos', 'runtime_validation_report_missing:semantic_validation_08_readelay_cockos', 'runtime_validation_report_missing:semantic_validation_09_reaeq_cockos', 'runtime_observation_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx', 'runtime_observation_missing:semantic_validation_02_reaverbate_cockos', 'runtime_observation_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx', 'runtime_observation_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx', 'runtime_observation_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx', 'runtime_observation_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx', 'runtime_observation_missing:semantic_validation_07_reacomp_cockos', 'runtime_observation_missing:semantic_validation_08_readelay_cockos', 'runtime_observation_missing:semantic_validation_09_reaeq_cockos', 'runtime_report_authoring_package_not_ready:no_accepted_runtime_observations', 'accepted_runtime_observations_missing', 'Codex Vocal/vocal_ai_artifact_split_tamer.jsfx:collect_reaper_observed_semantic_validation', 'OTT (Xfer Records):install_or_disable_unavailable_plugin', 'ReaComp (Cockos):rerun_or_keep_plugin_read_only', 'ReaDelay (Cockos):rerun_or_keep_plugin_read_only', 'ReaEQ (Cockos):rerun_or_keep_plugin_read_only', 'ReaVerbate (Cockos):collect_reaper_observed_semantic_validation', 'TDR Nova (Tokyo Dawn Labs):install_or_disable_unavailable_plugin', 'Vocal Clarity Repair/vocal_air_guard.jsfx:collect_reaper_observed_semantic_validation', 'Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx:collect_reaper_observed_semantic_validation', 'Vocal Clarity Repair/vocal_output_guard.jsfx:collect_reaper_observed_semantic_validation', 'Vocal Clarity Repair/vocal_presence_enhancer.jsfx:collect_reaper_observed_semantic_validation', 'safe_draft_plugin_ready_false', 'final_audio_path_not_file', 'final_qc_failure:qc_not_requested_or_primary_wav_missing', 'final_qc_file_integrity_bit_depth_missing', 'final_qc_file_integrity_channels_missing', 'final_qc_file_integrity_duration_seconds_missing', 'final_qc_file_integrity_sample_rate_missing', 'final_qc_has_failures', 'final_qc_not_passed', 'final_qc_true_peak_above_ceiling', 'final_render_evidence:final_export_state_not_safe', 'final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_render_evidence:primary_wav_render_missing', 'final_render_evidence:selected_export_source_path_missing', 'final_render_evidence_not_ready', 'final_render_manifest_primary_wav_missing', 'qc_not_requested_or_primary_wav_missing', 'qc_failure_for_final_delivery', 'final_export_state_not_safe', 'final_render_manifest_diagnostic_or_report_only', 'primary_wav_render_missing', 'selected_export_source_path_missing', 'full_mix_unsafe_tracks:2', 'high_risk_track:unsafe:SOURCE full mix reference muted', 'high_risk_track:unsafe:V37 INSTRUMENTAL BUS free EQ pocket', 'stem_required_tracks:2', 'source_acceptance_candidates_missing']`

## Risk Root Cause Rollup

- Passed: `False`
- Open risks: `429`
- Root causes: `12`
- Next root cause: `plugin_validation_not_ready`
- Blockers: `['plugin_validation_not_ready', 'accepted_source_or_stems_missing', 'artifact_evidence_missing', 'primary_render_missing', 'final_qc_missing_or_failed', 'ab_preview_missing_or_not_matched', 'human_approval_missing', 'deliverable_package_missing', 'delivery_consistency_not_ready', 'other_open_risks']`

## Risk Remediation Plan

- Status: `remediation_plan_ready`
- Open risks: `429`
- Actions: `6`
- Dry-run only: `True`
- Blockers: `[]`

## Path Hygiene Audit

- Passed: `True`
- Finding counts: `{'blocker': 0, 'info': 18, 'warning': 0}`
- Blockers: `[]`
- Warnings: `[]`

## Plugin Validation Preflight

- Status: `availability_or_validation_incomplete`
- Safe to write parameters: `False`
- Available plugins: `9`
- Missing plugins: `2`
- Blockers: `['required_plugin_availability_missing:OTT (Xfer Records)', 'required_plugin_availability_missing:TDR Nova (Tokyo Dawn Labs)', 'semantic_parameter_validation_required']`
- Warnings: `['adapter_validation_reports_unavailable', 'availability_does_not_grant_write_safety']`

## Plugin Validation Action Plan

- Status: `plugin_validation_actions_open`
- Safe to write parameters: `False`
- Plugin actions: `11`
- Next plugin action: `OTT (Xfer Records):install_or_disable_unavailable_plugin`
- Blockers: `['Codex Vocal/vocal_ai_artifact_split_tamer.jsfx:collect_reaper_observed_semantic_validation', 'OTT (Xfer Records):install_or_disable_unavailable_plugin', 'ReaComp (Cockos):rerun_or_keep_plugin_read_only', 'ReaDelay (Cockos):rerun_or_keep_plugin_read_only', 'ReaEQ (Cockos):rerun_or_keep_plugin_read_only', 'ReaVerbate (Cockos):collect_reaper_observed_semantic_validation', 'TDR Nova (Tokyo Dawn Labs):install_or_disable_unavailable_plugin', 'Vocal Clarity Repair/vocal_air_guard.jsfx:collect_reaper_observed_semantic_validation', 'Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx:collect_reaper_observed_semantic_validation', 'Vocal Clarity Repair/vocal_output_guard.jsfx:collect_reaper_observed_semantic_validation', 'Vocal Clarity Repair/vocal_presence_enhancer.jsfx:collect_reaper_observed_semantic_validation']`
- Warnings: `['Codex Vocal/vocal_ai_artifact_split_tamer.jsfx:availability_only_not_write_safety', 'ReaComp (Cockos):availability_only_not_write_safety', 'ReaComp (Cockos):some_semantic_controls_remain_write_blocked', 'ReaDelay (Cockos):availability_only_not_write_safety', 'ReaDelay (Cockos):some_semantic_controls_remain_write_blocked', 'ReaEQ (Cockos):availability_only_not_write_safety', 'ReaEQ (Cockos):some_semantic_controls_remain_write_blocked', 'ReaVerbate (Cockos):availability_only_not_write_safety', 'Vocal Clarity Repair/vocal_air_guard.jsfx:availability_only_not_write_safety', 'Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx:availability_only_not_write_safety', 'Vocal Clarity Repair/vocal_output_guard.jsfx:availability_only_not_write_safety', 'Vocal Clarity Repair/vocal_presence_enhancer.jsfx:availability_only_not_write_safety', 'adapter_validation_reports_unavailable', 'availability_does_not_grant_write_safety']`

## Plugin Availability Resolution Plan

- Status: `operator_resolution_required`
- Unavailable plugins: `2`
- Pending decisions: `['OTT (Xfer Records)', 'TDR Nova (Tokyo Dawn Labs)']`
- Disable manifest plugins: `2`
- Blockers: `[]`

## Plugin Availability Operator Decision Package

- Status: `operator_decisions_ready_for_human_acknowledgement`
- Package ready: `True`
- Availability decisions ready: `False`
- Required decisions: `2`
- Accepted decisions: `0`
- Missing decisions: `['OTT (Xfer Records)', 'TDR Nova (Tokyo Dawn Labs)']`
- Candidate manifest: `automix/review/plugin_availability_disable_manifest_candidate.json`
- Accepted manifest: `automix/review/plugin_availability_disable_manifest.json`
- Accepted manifest exists: `False`
- Safe to write parameters: `False`
- Blockers: `[]`
- Warnings: `['operator_disable_or_install_decision_required']`

## Plugin Availability Decision Gate

- Status: `operator_decision_manifest_missing`
- Decisions ready: `False`
- Required decisions: `2`
- Accepted decisions: `0`
- Missing decisions: `['OTT (Xfer Records)', 'TDR Nova (Tokyo Dawn Labs)']`
- Safe to write parameters: `False`
- Blockers: `['operator_decision_missing:OTT (Xfer Records)', 'operator_decision_missing:TDR Nova (Tokyo Dawn Labs)', 'plugin_availability_decision_manifest_missing']`

## Plugin Semantic Validation Gate

- Semantic validation ready: `False`
- Required plugins: `11`
- Validation reports: `6`
- Safe controls: `0`
- Blockers: `['ReaComp (Cockos):validation_report_has_no_write_safe_controls', 'ReaComp (Cockos):validation_report_not_passed:validation_unavailable', 'ReaComp (Cockos):validation_report_not_safe_for_automix', 'ReaDelay (Cockos):validation_report_has_no_write_safe_controls', 'ReaDelay (Cockos):validation_report_not_passed:validation_unavailable', 'ReaDelay (Cockos):validation_report_not_safe_for_automix', 'ReaEQ (Cockos):validation_report_has_no_write_safe_controls', 'ReaEQ (Cockos):validation_report_not_passed:validation_unavailable', 'ReaEQ (Cockos):validation_report_not_safe_for_automix', 'no_passed_semantic_validation_report:ReaComp (Cockos)', 'no_passed_semantic_validation_report:ReaDelay (Cockos)', 'no_passed_semantic_validation_report:ReaEQ (Cockos)', 'semantic_validation_passed_reports_missing', 'validation_report_missing:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx', 'validation_report_missing:OTT (Xfer Records)', 'validation_report_missing:ReaVerbate (Cockos)', 'validation_report_missing:TDR Nova (Tokyo Dawn Labs)', 'validation_report_missing:Vocal Clarity Repair/vocal_air_guard.jsfx', 'validation_report_missing:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx', 'validation_report_missing:Vocal Clarity Repair/vocal_output_guard.jsfx', 'validation_report_missing:Vocal Clarity Repair/vocal_presence_enhancer.jsfx']`
- Warnings: `['ReaComp (Cockos):some_semantic_controls_remain_write_blocked', 'ReaDelay (Cockos):some_semantic_controls_remain_write_blocked', 'ReaEQ (Cockos):some_semantic_controls_remain_write_blocked']`

## Plugin Semantic Validation Collection Plan

- Status: `availability_decisions_required_before_full_collection`
- Open jobs: `11`
- Collectable jobs: `9`
- Decision-blocked jobs: `2`
- Ready to collect some in REAPER: `True`
- All jobs resolved: `False`
- Next collection job: `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx:collect_missing_reaper_observed_semantic_report`
- Safe to write parameters: `False`
- Blockers: `['availability_decision_missing:OTT (Xfer Records)', 'availability_decision_missing:TDR Nova (Tokyo Dawn Labs)']`
- Warnings: `['ReaComp (Cockos):some_semantic_controls_remain_write_blocked', 'ReaDelay (Cockos):some_semantic_controls_remain_write_blocked', 'ReaEQ (Cockos):some_semantic_controls_remain_write_blocked']`

## Plugin Semantic Validation Queue

- Status: `queue_ready_with_blocked_unavailable_decisions`
- Queue jobs: `9`
- Blocked jobs: `2`
- Ready to run REAPER collection: `True`
- Requires REAPER runtime: `True`
- Next queue job: `semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- Safe to write parameters: `False`
- Blockers: `['collection_job_blocked:OTT (Xfer Records):availability_decision_missing:OTT (Xfer Records)', 'collection_job_blocked:TDR Nova (Tokyo Dawn Labs):availability_decision_missing:TDR Nova (Tokyo Dawn Labs)']`
- Warnings: `['ReaComp (Cockos):some_semantic_controls_remain_write_blocked', 'ReaDelay (Cockos):some_semantic_controls_remain_write_blocked', 'ReaEQ (Cockos):some_semantic_controls_remain_write_blocked']`

## Plugin Semantic Validation Runtime Collection Package

- Status: `runtime_collection_package_ready`
- Ready for runtime collection: `True`
- Ready for runtime evidence gate: `False`
- Collection jobs: `9`
- Report templates: `9`
- Target reports existing: `0`
- Target reports missing: `9`
- Blocked queue jobs: `2`
- Manifest candidate: `automix/review/plugin_semantic_validation_runtime_manifest_candidate.json`
- Report template dir: `automix/review/plugin_semantic_validation_runtime_report_templates`
- Safe to write parameters: `False`
- Blockers: `[]`
- Warnings: `['blocked_queue_jobs_remain:2']`

## Plugin Semantic Validation Runtime Observation Gate

- Status: `runtime_observations_missing`
- Runtime observations ready: `False`
- Ready for manual report authoring: `False`
- Ready for runtime evidence gate: `False`
- Collector jobs: `9`
- Accepted observations: `0`
- Blocked observations: `9`
- Blocked queue jobs: `2`
- Next blocked observation: `semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- Safe to write parameters: `False`
- Creates validation reports: `False`
- Blockers: `['runtime_observation_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx', 'runtime_observation_missing:semantic_validation_02_reaverbate_cockos', 'runtime_observation_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx', 'runtime_observation_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx', 'runtime_observation_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx', 'runtime_observation_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx', 'runtime_observation_missing:semantic_validation_07_reacomp_cockos', 'runtime_observation_missing:semantic_validation_08_readelay_cockos', 'runtime_observation_missing:semantic_validation_09_reaeq_cockos']`
- Warnings: `['blocked_queue_jobs_remain:2']`

## Plugin Semantic Validation Runtime Observation Provenance Gate

- Status: `runtime_observation_provenance_pending_observations`
- Passed: `True`
- Expected packet ready: `True`
- Observed provenance ready: `False`
- Ready for manual report authoring: `False`
- Observations existing: `0`
- Observations missing: `9`
- Observations verified: `0`
- Safe to write parameters: `False`
- Creates validation reports: `False`
- Blockers: `[]`
- Warnings: `['runtime_observation_files_missing:9', 'semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx:runtime_observation_file_missing', 'semantic_validation_02_reaverbate_cockos:runtime_observation_file_missing', 'semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx:runtime_observation_file_missing', 'semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx:runtime_observation_file_missing', 'semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx:runtime_observation_file_missing', 'semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx:runtime_observation_file_missing', 'semantic_validation_07_reacomp_cockos:runtime_observation_file_missing', 'semantic_validation_08_readelay_cockos:runtime_observation_file_missing', 'semantic_validation_09_reaeq_cockos:runtime_observation_file_missing']`

## Plugin Semantic Validation Runtime Report Authoring Package

- Status: `no_accepted_runtime_observations`
- Package ready: `False`
- Ready for manual report authoring: `False`
- Ready for runtime evidence gate: `False`
- Accepted observations: `0`
- Templates: `0`
- Template dir: `automix/review/plugin_semantic_validation_runtime_report_authoring_templates`
- Checklist: `automix/review/plugin_semantic_validation_runtime_report_authoring_checklist.md`
- Safe to write parameters: `False`
- Creates validation reports: `False`
- Writes analysis reports: `False`
- Blockers: `['accepted_runtime_observations_missing']`
- Warnings: `[]`

## Plugin Semantic Validation Runtime Report Authoring Gate

- Status: `runtime_report_authoring_package_not_ready`
- Candidates ready: `False`
- Ready for operator promotion: `False`
- Ready for runtime evidence gate: `False`
- Templates: `0`
- Candidate reports: `0`
- Accepted candidates: `0`
- Candidate dir: `automix/review/plugin_semantic_validation_runtime_report_authoring_candidates`
- Promotion checklist: `automix/review/plugin_semantic_validation_runtime_report_promotion_checklist.md`
- Manifest candidate: `automix/review/plugin_semantic_validation_runtime_manifest_candidate_from_authoring.json`
- Safe to write parameters: `False`
- Writes analysis reports: `False`
- Candidate reports are validation evidence: `False`
- Blockers: `['runtime_report_authoring_package_not_ready:no_accepted_runtime_observations']`
- Warnings: `[]`

## Plugin Semantic Validation Runtime Evidence Gate

- Status: `runtime_manifest_missing`
- Runtime evidence ready: `False`
- Ready for semantic gate rerun: `False`
- Queue jobs: `9`
- Accepted jobs: `0`
- Blocked jobs: `9`
- Blocked queue jobs: `2`
- Next blocked job: `semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- Safe to write parameters: `False`
- Blockers: `['plugin_semantic_validation_runtime_manifest_missing', 'runtime_manifest_job_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx', 'runtime_manifest_job_missing:semantic_validation_02_reaverbate_cockos', 'runtime_manifest_job_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx', 'runtime_manifest_job_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx', 'runtime_manifest_job_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx', 'runtime_manifest_job_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx', 'runtime_manifest_job_missing:semantic_validation_07_reacomp_cockos', 'runtime_manifest_job_missing:semantic_validation_08_readelay_cockos', 'runtime_manifest_job_missing:semantic_validation_09_reaeq_cockos', 'runtime_validation_report_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx', 'runtime_validation_report_missing:semantic_validation_02_reaverbate_cockos', 'runtime_validation_report_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx', 'runtime_validation_report_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx', 'runtime_validation_report_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx', 'runtime_validation_report_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx', 'runtime_validation_report_missing:semantic_validation_07_reacomp_cockos', 'runtime_validation_report_missing:semantic_validation_08_readelay_cockos', 'runtime_validation_report_missing:semantic_validation_09_reaeq_cockos']`
- Warnings: `['blocked_queue_jobs_remain:2']`

## Source Handoff Readiness

- Stem requests: `2`
- Manual review tracks: `4`
- Source files present: `6/8`
- Accepted export source present: `False`
- Automatic processing ready: `False`
- Blockers: `['accepted_export_source_missing', 'current_source_file_missing:V37 RETURN ReaDelay filtered throw', 'current_source_file_missing:V37 RETURN ReaVerbate dark send', 'full_mix_unsafe_tracks:2', 'stem_requests_open:2']`
- Warnings: `['current_source_file_presence_is_not_acceptance', 'manual_review_required_tracks:4']`

## Source Acceptance Gate

- Accepted export source ready: `False`
- Accepted stem sources: `0`
- Candidate sources: `0`
- Blockers: `['source_acceptance_candidates_missing']`
- Warnings: `['accepted_final_export_source_not_recorded']`

## Rollback Evidence Gate

- Ready for delivery readiness: `True`
- Original tracks protected: `True`
- Original master protected: `True`
- Rollback entries: `3`
- Safe entries: `3`
- Blockers: `[]`
- Warnings: `['no_applied_stages_declared', 'unknown:rollback_entry:rollback_entry_points_to_global_registry', 'unknown:rollback_entry:rollback_stage_unknown']`

## Final Render Evidence Gate

- Ready for final QC: `False`
- Ready for approval readiness: `False`
- Primary WAV: ``
- Blockers: `['final_export_state_not_safe', 'final_render_manifest_diagnostic_or_report_only', 'primary_wav_render_missing', 'selected_export_source_path_missing']`
- Warnings: `[]`

## Final QC Evidence Gate

- Ready for delivery QC: `False`
- Ready for approval readiness: `False`
- Final audio: `.`
- Blockers: `['final_audio_path_not_file', 'final_qc_failure:qc_not_requested_or_primary_wav_missing', 'final_qc_file_integrity_bit_depth_missing', 'final_qc_file_integrity_channels_missing', 'final_qc_file_integrity_duration_seconds_missing', 'final_qc_file_integrity_sample_rate_missing', 'final_qc_has_failures', 'final_qc_not_passed', 'final_qc_true_peak_above_ceiling', 'final_render_evidence:final_export_state_not_safe', 'final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_render_evidence:primary_wav_render_missing', 'final_render_evidence:selected_export_source_path_missing', 'final_render_evidence_not_ready', 'final_render_manifest_primary_wav_missing']`
- Warnings: `[]`

## Deliverable Package Evidence Gate

- Ready for delivery package: `False`
- Ready for professional readiness: `False`
- ZIP valid: `False`
- Blockers: `['ab_preview_evidence:ab_preview_final_segment_missing', 'ab_preview_evidence:ab_preview_loudness_match_metrics_missing', 'ab_preview_evidence:ab_preview_manifest_has_warnings', 'ab_preview_evidence:ab_preview_not_created', 'ab_preview_evidence:ab_preview_not_loudness_matched', 'ab_preview_evidence:ab_preview_original_segment_missing', 'ab_preview_evidence:ab_preview_segments_missing', 'ab_preview_evidence:ab_preview_too_few_segments', 'ab_preview_evidence:preview_output_path_missing', 'ab_preview_evidence:source_final_path_missing', 'ab_preview_evidence:source_original_path_missing', 'ab_preview_evidence_gate_not_ready', 'deliverable_package_manifest_has_missing_files', 'deliverable_package_not_created', 'deliverable_package_size_missing_or_zero', 'deliverable_zip_path_missing', 'final_approval_evidence:ab_preview_evidence:ab_preview_final_segment_missing', 'final_approval_evidence:ab_preview_evidence:ab_preview_loudness_match_metrics_missing', 'final_approval_evidence:ab_preview_evidence:ab_preview_manifest_has_warnings', 'final_approval_evidence:ab_preview_evidence:ab_preview_not_created', 'final_approval_evidence:ab_preview_evidence:ab_preview_not_loudness_matched', 'final_approval_evidence:ab_preview_evidence:ab_preview_original_segment_missing', 'final_approval_evidence:ab_preview_evidence:ab_preview_segments_missing', 'final_approval_evidence:ab_preview_evidence:ab_preview_too_few_segments', 'final_approval_evidence:ab_preview_evidence:preview_output_path_missing', 'final_approval_evidence:ab_preview_evidence:source_final_path_missing', 'final_approval_evidence:ab_preview_evidence:source_original_path_missing', 'final_approval_evidence:ab_preview_evidence_not_ready', 'final_approval_evidence:final_human_approval_missing', 'final_approval_evidence:final_qc_evidence:final_audio_path_not_file', 'final_approval_evidence:final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing', 'final_approval_evidence:final_qc_evidence:final_qc_file_integrity_bit_depth_missing', 'final_approval_evidence:final_qc_evidence:final_qc_file_integrity_channels_missing', 'final_approval_evidence:final_qc_evidence:final_qc_file_integrity_duration_seconds_missing', 'final_approval_evidence:final_qc_evidence:final_qc_file_integrity_sample_rate_missing', 'final_approval_evidence:final_qc_evidence:final_qc_has_failures', 'final_approval_evidence:final_qc_evidence:final_qc_not_passed', 'final_approval_evidence:final_qc_evidence:final_qc_true_peak_above_ceiling', 'final_approval_evidence:final_qc_evidence:final_render_evidence:final_export_state_not_safe', 'final_approval_evidence:final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_approval_evidence:final_qc_evidence:final_render_evidence:primary_wav_render_missing', 'final_approval_evidence:final_qc_evidence:final_render_evidence:selected_export_source_path_missing', 'final_approval_evidence:final_qc_evidence:final_render_evidence_not_ready', 'final_approval_evidence:final_qc_evidence:final_render_manifest_primary_wav_missing', 'final_approval_evidence:final_qc_evidence_not_ready', 'final_approval_evidence:final_render_evidence:final_export_state_not_safe', 'final_approval_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_approval_evidence:final_render_evidence:primary_wav_render_missing', 'final_approval_evidence:final_render_evidence:selected_export_source_path_missing', 'final_approval_evidence:final_render_evidence_not_ready', 'final_approval_evidence_gate_not_ready', 'final_qc_evidence:final_audio_path_not_file', 'final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing', 'final_qc_evidence:final_qc_file_integrity_bit_depth_missing', 'final_qc_evidence:final_qc_file_integrity_channels_missing', 'final_qc_evidence:final_qc_file_integrity_duration_seconds_missing', 'final_qc_evidence:final_qc_file_integrity_sample_rate_missing', 'final_qc_evidence:final_qc_has_failures', 'final_qc_evidence:final_qc_not_passed', 'final_qc_evidence:final_qc_true_peak_above_ceiling', 'final_qc_evidence:final_render_evidence:final_export_state_not_safe', 'final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_qc_evidence:final_render_evidence:primary_wav_render_missing', 'final_qc_evidence:final_render_evidence:selected_export_source_path_missing', 'final_qc_evidence:final_render_evidence_not_ready', 'final_qc_evidence:final_render_manifest_primary_wav_missing', 'final_qc_evidence_gate_not_ready', 'final_render_evidence:final_export_state_not_safe', 'final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_render_evidence:primary_wav_render_missing', 'final_render_evidence:selected_export_source_path_missing', 'final_render_evidence_gate_not_ready']`
- Warnings: `[]`

## Final Delivery Consistency Gate

- Ready for delivery consistency: `False`
- Ready for professional readiness: `False`
- Final audio: ``
- A/B preview: ``
- Blockers: `['ab_preview_evidence_not_ready', 'ab_preview_output_path_missing', 'deliverable_package_evidence_not_ready', 'final_approval_evidence_not_ready', 'final_audio_path_missing', 'final_export_state_not_safe', 'final_qc_evidence_not_ready', 'final_render_evidence_not_ready', 'final_render_evidence_primary_wav_missing', 'final_render_manifest_primary_wav_missing']`
- Warnings: `[]`

## Artifact Signal Audit

- Artifact signal established: `False`
- Safe to run artifact suppression: `False`
- Usable source signals: `0`
- Usable metric signals: `0`
- Usable feedback signal: `False`
- Blockers: `['artifact_signal_not_established', 'measured_artifact_metrics_not_established']`
- Warnings: `['no_user_artifact_feedback_recorded', 'some_artifact_metric_reports_are_report_only', 'source_map_does_not_classify_ai_or_source_separated_vocals']`

## Artifact Evidence Gate

- Artifact evidence established: `False`
- Measured artifact metrics established: `False`
- Ready for artifact review: `False`
- Safe to run artifact suppression: `False`
- Blockers: `['artifact_evidence_not_established', 'measured_artifact_metrics_missing']`
- Warnings: `['feedback:feedback_baseline_is_not_user_evidence', 'feedback:user_artifact_feedback_missing', 'report_only_metric:final_qc.vocal_preservation.ai_fizz_score', 'report_only_metric:final_qc.vocal_preservation.metallic_artifact_score', 'report_only_metric:final_qc.vocal_preservation.sibilance_splatter_score', 'report_only_metric:premaster.ai_artifact_risk_profile.high_fizz_risk', 'report_only_metric:premaster.ai_artifact_risk_profile.metallic_harshness_risk', 'report_only_metric:premaster.ai_artifact_risk_profile.sibilance_splatter_risk']`

## A/B Preview Evidence Gate

- Ready for human A/B review: `False`
- Ready for final approval request: `False`
- Human A/B review recorded: `False`
- Loudness metrics present: `False`
- Loudness delta after match: `None`
- Blockers: `['ab_preview_final_segment_missing', 'ab_preview_loudness_match_metrics_missing', 'ab_preview_manifest_has_warnings', 'ab_preview_not_created', 'ab_preview_not_loudness_matched', 'ab_preview_original_segment_missing', 'ab_preview_segments_missing', 'ab_preview_too_few_segments', 'preview_output_path_missing', 'source_final_path_missing', 'source_original_path_missing']`
- Warnings: `['final_render_manifest_missing_ab_link_unverified', 'manifest:ab_preview_not_requested_or_missing_sources']`

## Final Approval Evidence Gate

- Ready for delivery request: `False`
- Approval pending only: `False`
- Approved: `False`
- Review decision: ``
- Loudness-matched A/B reviewed: `False`
- Final accepted at matched loudness: `False`
- Blockers: `['ab_preview_evidence:ab_preview_final_segment_missing', 'ab_preview_evidence:ab_preview_loudness_match_metrics_missing', 'ab_preview_evidence:ab_preview_manifest_has_warnings', 'ab_preview_evidence:ab_preview_not_created', 'ab_preview_evidence:ab_preview_not_loudness_matched', 'ab_preview_evidence:ab_preview_original_segment_missing', 'ab_preview_evidence:ab_preview_segments_missing', 'ab_preview_evidence:ab_preview_too_few_segments', 'ab_preview_evidence:preview_output_path_missing', 'ab_preview_evidence:source_final_path_missing', 'ab_preview_evidence:source_original_path_missing', 'ab_preview_evidence_not_ready', 'final_human_approval_missing', 'final_qc_evidence:final_audio_path_not_file', 'final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing', 'final_qc_evidence:final_qc_file_integrity_bit_depth_missing', 'final_qc_evidence:final_qc_file_integrity_channels_missing', 'final_qc_evidence:final_qc_file_integrity_duration_seconds_missing', 'final_qc_evidence:final_qc_file_integrity_sample_rate_missing', 'final_qc_evidence:final_qc_has_failures', 'final_qc_evidence:final_qc_not_passed', 'final_qc_evidence:final_qc_true_peak_above_ceiling', 'final_qc_evidence:final_render_evidence:final_export_state_not_safe', 'final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_qc_evidence:final_render_evidence:primary_wav_render_missing', 'final_qc_evidence:final_render_evidence:selected_export_source_path_missing', 'final_qc_evidence:final_render_evidence_not_ready', 'final_qc_evidence:final_render_manifest_primary_wav_missing', 'final_qc_evidence_not_ready', 'final_render_evidence:final_export_state_not_safe', 'final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_render_evidence:primary_wav_render_missing', 'final_render_evidence:selected_export_source_path_missing', 'final_render_evidence_not_ready']`
- Warnings: `[]`

## Approval Export Readiness

- Status: `blocked`
- Ready for delivery request: `False`
- Ready for human approval request: `False`
- Blockers: `['ab_preview_evidence:ab_preview_final_segment_missing', 'ab_preview_evidence:ab_preview_loudness_match_metrics_missing', 'ab_preview_evidence:ab_preview_manifest_has_warnings', 'ab_preview_evidence:ab_preview_not_created', 'ab_preview_evidence:ab_preview_not_loudness_matched', 'ab_preview_evidence:ab_preview_original_segment_missing', 'ab_preview_evidence:ab_preview_segments_missing', 'ab_preview_evidence:ab_preview_too_few_segments', 'ab_preview_evidence:preview_output_path_missing', 'ab_preview_evidence:source_final_path_missing', 'ab_preview_evidence:source_original_path_missing', 'ab_preview_evidence_not_ready', 'ab_preview_missing_or_not_loudness_matched', 'accepted_export_source_missing', 'artifact_evidence:artifact_evidence_not_established', 'artifact_evidence:measured_artifact_metrics_missing', 'artifact_signal:artifact_signal_not_established', 'artifact_signal:measured_artifact_metrics_not_established', 'final_human_approval_missing', 'final_qc_evidence:final_audio_path_not_file', 'final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing', 'final_qc_evidence:final_qc_file_integrity_bit_depth_missing', 'final_qc_evidence:final_qc_file_integrity_channels_missing', 'final_qc_evidence:final_qc_file_integrity_duration_seconds_missing', 'final_qc_evidence:final_qc_file_integrity_sample_rate_missing', 'final_qc_evidence:final_qc_has_failures', 'final_qc_evidence:final_qc_not_passed', 'final_qc_evidence:final_qc_true_peak_above_ceiling', 'final_qc_evidence:final_render_evidence:final_export_state_not_safe', 'final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_qc_evidence:final_render_evidence:primary_wav_render_missing', 'final_qc_evidence:final_render_evidence:selected_export_source_path_missing', 'final_qc_evidence:final_render_evidence_not_ready', 'final_qc_evidence:final_render_manifest_primary_wav_missing', 'final_qc_evidence_not_ready', 'final_qc_missing_or_failed', 'final_render_evidence:final_export_state_not_safe', 'final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_render_evidence:primary_wav_render_missing', 'final_render_evidence:selected_export_source_path_missing', 'final_render_evidence_not_ready', 'final_render_missing_or_diagnostic_only', 'plugin_semantic_validation:ReaComp (Cockos):validation_report_has_no_write_safe_controls', 'plugin_semantic_validation:ReaComp (Cockos):validation_report_not_passed:validation_unavailable', 'plugin_semantic_validation:ReaComp (Cockos):validation_report_not_safe_for_automix', 'plugin_semantic_validation:ReaDelay (Cockos):validation_report_has_no_write_safe_controls', 'plugin_semantic_validation:ReaDelay (Cockos):validation_report_not_passed:validation_unavailable', 'plugin_semantic_validation:ReaDelay (Cockos):validation_report_not_safe_for_automix', 'plugin_semantic_validation:ReaEQ (Cockos):validation_report_has_no_write_safe_controls', 'plugin_semantic_validation:ReaEQ (Cockos):validation_report_not_passed:validation_unavailable', 'plugin_semantic_validation:ReaEQ (Cockos):validation_report_not_safe_for_automix', 'plugin_semantic_validation:no_passed_semantic_validation_report:ReaComp (Cockos)', 'plugin_semantic_validation:no_passed_semantic_validation_report:ReaDelay (Cockos)', 'plugin_semantic_validation:no_passed_semantic_validation_report:ReaEQ (Cockos)', 'plugin_semantic_validation:semantic_validation_passed_reports_missing', 'plugin_semantic_validation:validation_report_missing:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx', 'plugin_semantic_validation:validation_report_missing:OTT (Xfer Records)', 'plugin_semantic_validation:validation_report_missing:ReaVerbate (Cockos)', 'plugin_semantic_validation:validation_report_missing:TDR Nova (Tokyo Dawn Labs)', 'plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_air_guard.jsfx', 'plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx', 'plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_output_guard.jsfx', 'plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_presence_enhancer.jsfx', 'plugin_validation_preflight:required_plugin_availability_missing:OTT (Xfer Records)', 'plugin_validation_preflight:required_plugin_availability_missing:TDR Nova (Tokyo Dawn Labs)', 'plugin_validation_preflight:semantic_parameter_validation_required', 'source_acceptance:source_acceptance_candidates_missing', 'source_handoff:current_source_file_missing:V37 RETURN ReaDelay filtered throw', 'source_handoff:current_source_file_missing:V37 RETURN ReaVerbate dark send', 'source_handoff:full_mix_unsafe_tracks:2', 'source_handoff:stem_requests_open:2']`
- Warnings: `[]`

## Feedback

- Pending unresolved: `0`
- Resolved: `0`

## Claim Language Guard

- Passed: `True`
- Findings: `0`
