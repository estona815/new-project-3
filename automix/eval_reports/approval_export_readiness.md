# Approval Export Readiness

- Project: `project`
- Created UTC: `2026-06-02T16:41:33Z`
- Status: `blocked`
- Ready for delivery request: `False`
- Ready for human approval request: `False`

This report does not approve audio. It explains which final export approval gates are still missing.

## Blockers

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
- `ab_preview_evidence_not_ready`
- `ab_preview_missing_or_not_loudness_matched`
- `accepted_export_source_missing`
- `artifact_evidence:artifact_evidence_not_established`
- `artifact_evidence:measured_artifact_metrics_missing`
- `artifact_signal:artifact_signal_not_established`
- `artifact_signal:measured_artifact_metrics_not_established`
- `final_human_approval_missing`
- `final_qc_evidence:final_audio_path_not_file`
- `final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing`
- `final_qc_evidence:final_qc_file_integrity_bit_depth_missing`
- `final_qc_evidence:final_qc_file_integrity_channels_missing`
- `final_qc_evidence:final_qc_file_integrity_duration_seconds_missing`
- `final_qc_evidence:final_qc_file_integrity_sample_rate_missing`
- `final_qc_evidence:final_qc_has_failures`
- `final_qc_evidence:final_qc_not_passed`
- `final_qc_evidence:final_qc_true_peak_above_ceiling`
- `final_qc_evidence:final_render_evidence:final_export_state_not_safe`
- `final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- `final_qc_evidence:final_render_evidence:primary_wav_render_missing`
- `final_qc_evidence:final_render_evidence:selected_export_source_path_missing`
- `final_qc_evidence:final_render_evidence_not_ready`
- `final_qc_evidence:final_render_manifest_primary_wav_missing`
- `final_qc_evidence_not_ready`
- `final_qc_missing_or_failed`
- `final_render_evidence:final_export_state_not_safe`
- `final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- `final_render_evidence:primary_wav_render_missing`
- `final_render_evidence:selected_export_source_path_missing`
- `final_render_evidence_not_ready`
- `final_render_missing_or_diagnostic_only`
- `plugin_semantic_validation:ReaComp (Cockos):validation_report_has_no_write_safe_controls`
- `plugin_semantic_validation:ReaComp (Cockos):validation_report_not_passed:validation_unavailable`
- `plugin_semantic_validation:ReaComp (Cockos):validation_report_not_safe_for_automix`
- `plugin_semantic_validation:ReaDelay (Cockos):validation_report_has_no_write_safe_controls`
- `plugin_semantic_validation:ReaDelay (Cockos):validation_report_not_passed:validation_unavailable`
- `plugin_semantic_validation:ReaDelay (Cockos):validation_report_not_safe_for_automix`
- `plugin_semantic_validation:ReaEQ (Cockos):validation_report_has_no_write_safe_controls`
- `plugin_semantic_validation:ReaEQ (Cockos):validation_report_not_passed:validation_unavailable`
- `plugin_semantic_validation:ReaEQ (Cockos):validation_report_not_safe_for_automix`
- `plugin_semantic_validation:no_passed_semantic_validation_report:ReaComp (Cockos)`
- `plugin_semantic_validation:no_passed_semantic_validation_report:ReaDelay (Cockos)`
- `plugin_semantic_validation:no_passed_semantic_validation_report:ReaEQ (Cockos)`
- `plugin_semantic_validation:semantic_validation_passed_reports_missing`
- `plugin_semantic_validation:validation_report_missing:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- `plugin_semantic_validation:validation_report_missing:OTT (Xfer Records)`
- `plugin_semantic_validation:validation_report_missing:ReaVerbate (Cockos)`
- `plugin_semantic_validation:validation_report_missing:TDR Nova (Tokyo Dawn Labs)`
- `plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_air_guard.jsfx`
- `plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx`
- `plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_output_guard.jsfx`
- `plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_presence_enhancer.jsfx`
- `plugin_validation_preflight:required_plugin_availability_missing:OTT (Xfer Records)`
- `plugin_validation_preflight:required_plugin_availability_missing:TDR Nova (Tokyo Dawn Labs)`
- `plugin_validation_preflight:semantic_parameter_validation_required`
- `source_acceptance:source_acceptance_candidates_missing`
- `source_handoff:current_source_file_missing:V37 RETURN ReaDelay filtered throw`
- `source_handoff:current_source_file_missing:V37 RETURN ReaVerbate dark send`
- `source_handoff:full_mix_unsafe_tracks:2`
- `source_handoff:stem_requests_open:2`

## Warnings

- none

## Gate Summary

- Accepted export source present: `False`
- Source acceptance ready: `False`
- Source acceptance blockers: `['source_acceptance_candidates_missing']`
- Artifact evidence ready: `False`
- Artifact evidence blockers: `['artifact_evidence_not_established', 'measured_artifact_metrics_missing']`
- Plugin semantic validation ready: `False`
- Plugin semantic validation blockers: `['ReaComp (Cockos):validation_report_has_no_write_safe_controls', 'ReaComp (Cockos):validation_report_not_passed:validation_unavailable', 'ReaComp (Cockos):validation_report_not_safe_for_automix', 'ReaDelay (Cockos):validation_report_has_no_write_safe_controls', 'ReaDelay (Cockos):validation_report_not_passed:validation_unavailable', 'ReaDelay (Cockos):validation_report_not_safe_for_automix', 'ReaEQ (Cockos):validation_report_has_no_write_safe_controls', 'ReaEQ (Cockos):validation_report_not_passed:validation_unavailable', 'ReaEQ (Cockos):validation_report_not_safe_for_automix', 'no_passed_semantic_validation_report:ReaComp (Cockos)', 'no_passed_semantic_validation_report:ReaDelay (Cockos)', 'no_passed_semantic_validation_report:ReaEQ (Cockos)', 'semantic_validation_passed_reports_missing', 'validation_report_missing:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx', 'validation_report_missing:OTT (Xfer Records)', 'validation_report_missing:ReaVerbate (Cockos)', 'validation_report_missing:TDR Nova (Tokyo Dawn Labs)', 'validation_report_missing:Vocal Clarity Repair/vocal_air_guard.jsfx', 'validation_report_missing:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx', 'validation_report_missing:Vocal Clarity Repair/vocal_output_guard.jsfx', 'validation_report_missing:Vocal Clarity Repair/vocal_presence_enhancer.jsfx']`
- Selected export source: ``
- Final export safe to export: `False`
- Final render ready: `False`
- Primary WAV count: `0`
- Final render evidence ready: `False`
- Final render evidence blockers: `['final_export_state_not_safe', 'final_render_manifest_diagnostic_or_report_only', 'primary_wav_render_missing', 'selected_export_source_path_missing']`
- Final QC passed: `False`
- Final QC failures: `['qc_not_requested_or_primary_wav_missing']`
- Final QC evidence ready: `False`
- Final QC evidence blockers: `['final_audio_path_not_file', 'final_qc_failure:qc_not_requested_or_primary_wav_missing', 'final_qc_file_integrity_bit_depth_missing', 'final_qc_file_integrity_channels_missing', 'final_qc_file_integrity_duration_seconds_missing', 'final_qc_file_integrity_sample_rate_missing', 'final_qc_has_failures', 'final_qc_not_passed', 'final_qc_true_peak_above_ceiling', 'final_render_evidence:final_export_state_not_safe', 'final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_render_evidence:primary_wav_render_missing', 'final_render_evidence:selected_export_source_path_missing', 'final_render_evidence_not_ready', 'final_render_manifest_primary_wav_missing']`
- Final approval evidence ready: `False`
- Final approval evidence blockers: `['ab_preview_evidence:ab_preview_final_segment_missing', 'ab_preview_evidence:ab_preview_loudness_match_metrics_missing', 'ab_preview_evidence:ab_preview_manifest_has_warnings', 'ab_preview_evidence:ab_preview_not_created', 'ab_preview_evidence:ab_preview_not_loudness_matched', 'ab_preview_evidence:ab_preview_original_segment_missing', 'ab_preview_evidence:ab_preview_segments_missing', 'ab_preview_evidence:ab_preview_too_few_segments', 'ab_preview_evidence:preview_output_path_missing', 'ab_preview_evidence:source_final_path_missing', 'ab_preview_evidence:source_original_path_missing', 'ab_preview_evidence_not_ready', 'final_human_approval_missing', 'final_qc_evidence:final_audio_path_not_file', 'final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing', 'final_qc_evidence:final_qc_file_integrity_bit_depth_missing', 'final_qc_evidence:final_qc_file_integrity_channels_missing', 'final_qc_evidence:final_qc_file_integrity_duration_seconds_missing', 'final_qc_evidence:final_qc_file_integrity_sample_rate_missing', 'final_qc_evidence:final_qc_has_failures', 'final_qc_evidence:final_qc_not_passed', 'final_qc_evidence:final_qc_true_peak_above_ceiling', 'final_qc_evidence:final_render_evidence:final_export_state_not_safe', 'final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_qc_evidence:final_render_evidence:primary_wav_render_missing', 'final_qc_evidence:final_render_evidence:selected_export_source_path_missing', 'final_qc_evidence:final_render_evidence_not_ready', 'final_qc_evidence:final_render_manifest_primary_wav_missing', 'final_qc_evidence_not_ready', 'final_render_evidence:final_export_state_not_safe', 'final_render_evidence:final_render_manifest_diagnostic_or_report_only', 'final_render_evidence:primary_wav_render_missing', 'final_render_evidence:selected_export_source_path_missing', 'final_render_evidence_not_ready']`
- Rollback evidence ready: `True`
- Rollback evidence blockers: `[]`
- A/B preview ready: `False`
- A/B preview loudness matched: `False`
- A/B preview evidence ready: `False`
- A/B preview evidence blockers: `['ab_preview_final_segment_missing', 'ab_preview_loudness_match_metrics_missing', 'ab_preview_manifest_has_warnings', 'ab_preview_not_created', 'ab_preview_not_loudness_matched', 'ab_preview_original_segment_missing', 'ab_preview_segments_missing', 'ab_preview_too_few_segments', 'preview_output_path_missing', 'source_final_path_missing', 'source_original_path_missing']`
- Human approval recorded: `False`
- Original tracks protected: `True`
- Master unchanged: `True`
- Pending feedback items: `0`

## Evidence Files

- `final_export_state`: exists=`True`, json_valid=`True`
- `final_ab_preview_manifest`: exists=`True`, json_valid=`True`
- `ab_preview_evidence_gate`: exists=`True`, json_valid=`True`
- `final_render_manifest`: exists=`True`, json_valid=`True`
- `final_render_evidence_gate`: exists=`True`, json_valid=`True`
- `final_qc_metrics`: exists=`True`, json_valid=`True`
- `final_qc_evidence_gate`: exists=`True`, json_valid=`True`
- `final_human_approval`: exists=`True`, json_valid=`True`
- `final_approval_evidence_gate`: exists=`True`, json_valid=`True`
- `project_state_manifest`: exists=`True`, json_valid=`True`
- `rollback_evidence_gate`: exists=`True`, json_valid=`True`
- `source_acceptance_gate`: exists=`True`, json_valid=`True`
- `source_handoff_readiness`: exists=`True`, json_valid=`True`
- `artifact_evidence_gate`: exists=`True`, json_valid=`True`
- `artifact_signal_audit`: exists=`True`, json_valid=`True`
- `plugin_semantic_validation_gate`: exists=`True`, json_valid=`True`
- `plugin_validation_preflight`: exists=`True`, json_valid=`True`
