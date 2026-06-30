# Deliverable Package Evidence Gate

- Project: `project`
- Created UTC: `2026-06-02T16:55:07Z`
- Ready for delivery package: `False`
- Ready for professional readiness: `False`
- Package created: `False`
- ZIP path: ``
- ZIP valid: `False`
- ZIP entries: `0`
- Included files: `18`
- Missing files: `['automix/eval_reports/final_qc_report.md']`
- Original tracks protected: `True`
- Master unchanged: `True`

This gate validates the deliverable package evidence only. It does not approve audio.

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
- `ab_preview_evidence_gate_not_ready`
- `deliverable_package_manifest_has_missing_files`
- `deliverable_package_not_created`
- `deliverable_package_size_missing_or_zero`
- `deliverable_zip_path_missing`
- `final_approval_evidence:ab_preview_evidence:ab_preview_final_segment_missing`
- `final_approval_evidence:ab_preview_evidence:ab_preview_loudness_match_metrics_missing`
- `final_approval_evidence:ab_preview_evidence:ab_preview_manifest_has_warnings`
- `final_approval_evidence:ab_preview_evidence:ab_preview_not_created`
- `final_approval_evidence:ab_preview_evidence:ab_preview_not_loudness_matched`
- `final_approval_evidence:ab_preview_evidence:ab_preview_original_segment_missing`
- `final_approval_evidence:ab_preview_evidence:ab_preview_segments_missing`
- `final_approval_evidence:ab_preview_evidence:ab_preview_too_few_segments`
- `final_approval_evidence:ab_preview_evidence:preview_output_path_missing`
- `final_approval_evidence:ab_preview_evidence:source_final_path_missing`
- `final_approval_evidence:ab_preview_evidence:source_original_path_missing`
- `final_approval_evidence:ab_preview_evidence_not_ready`
- `final_approval_evidence:final_human_approval_missing`
- `final_approval_evidence:final_qc_evidence:final_audio_path_not_file`
- `final_approval_evidence:final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing`
- `final_approval_evidence:final_qc_evidence:final_qc_file_integrity_bit_depth_missing`
- `final_approval_evidence:final_qc_evidence:final_qc_file_integrity_channels_missing`
- `final_approval_evidence:final_qc_evidence:final_qc_file_integrity_duration_seconds_missing`
- `final_approval_evidence:final_qc_evidence:final_qc_file_integrity_sample_rate_missing`
- `final_approval_evidence:final_qc_evidence:final_qc_has_failures`
- `final_approval_evidence:final_qc_evidence:final_qc_not_passed`
- `final_approval_evidence:final_qc_evidence:final_qc_true_peak_above_ceiling`
- `final_approval_evidence:final_qc_evidence:final_render_evidence:final_export_state_not_safe`
- `final_approval_evidence:final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- `final_approval_evidence:final_qc_evidence:final_render_evidence:primary_wav_render_missing`
- `final_approval_evidence:final_qc_evidence:final_render_evidence:selected_export_source_path_missing`
- `final_approval_evidence:final_qc_evidence:final_render_evidence_not_ready`
- `final_approval_evidence:final_qc_evidence:final_render_manifest_primary_wav_missing`
- `final_approval_evidence:final_qc_evidence_not_ready`
- `final_approval_evidence:final_render_evidence:final_export_state_not_safe`
- `final_approval_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- `final_approval_evidence:final_render_evidence:primary_wav_render_missing`
- `final_approval_evidence:final_render_evidence:selected_export_source_path_missing`
- `final_approval_evidence:final_render_evidence_not_ready`
- `final_approval_evidence_gate_not_ready`
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
- `final_qc_evidence_gate_not_ready`
- `final_render_evidence:final_export_state_not_safe`
- `final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- `final_render_evidence:primary_wav_render_missing`
- `final_render_evidence:selected_export_source_path_missing`
- `final_render_evidence_gate_not_ready`

## Warnings

- none

## Required Evidence Files

- `export/final_render_manifest.json`: disk=`True`, manifest=`True`, satisfied=`True`
- `eval_reports/final_render_evidence_gate.json`: disk=`True`, manifest=`False`, satisfied=`True`
- `eval_reports/final_qc_metrics.json`: disk=`True`, manifest=`True`, satisfied=`True`
- `eval_reports/final_qc_evidence_gate.json`: disk=`True`, manifest=`False`, satisfied=`True`
- `eval_reports/final_ab_preview_manifest.json`: disk=`True`, manifest=`True`, satisfied=`True`
- `eval_reports/ab_preview_evidence_gate.json`: disk=`True`, manifest=`False`, satisfied=`True`
- `review/final_human_approval.json`: disk=`True`, manifest=`False`, satisfied=`True`
- `eval_reports/final_approval_evidence_gate.json`: disk=`True`, manifest=`False`, satisfied=`True`
- `rollback/global_rollback_registry.json`: disk=`True`, manifest=`False`, satisfied=`True`
- `eval_reports/rollback_evidence_gate.json`: disk=`True`, manifest=`False`, satisfied=`True`
- `eval_reports/final_qc_report.md`: disk=`True`, manifest=`False`, satisfied=`True`
- `export/project_state_manifest.json`: disk=`True`, manifest=`True`, satisfied=`True`
- `export/plugin_mapping_summary.md`: disk=`True`, manifest=`True`, satisfied=`True`

## Supporting Gates

- `final_render_evidence` ready=`False` schema_valid=`True`
- `final_qc_evidence` ready=`False` schema_valid=`True`
- `ab_preview_evidence` ready=`False` schema_valid=`True`
- `final_approval_evidence` ready=`False` schema_valid=`True`
- `rollback_evidence` ready=`True` schema_valid=`True`
