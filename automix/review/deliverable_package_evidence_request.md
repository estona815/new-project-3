# Deliverable Package Evidence Request

Create or repair the final deliverable ZIP only after render, QC, A/B, rollback, and final approval evidence are ready.

## Current Status

- Ready for delivery package: `False`
- Package manifest: `automix/export/deliverable_package_manifest.json`
- Template: `automix/review/deliverable_package_evidence_manifest_template.json`

## Required Evidence

- `automix/export/final_render_manifest.json`
- `automix/eval_reports/final_render_evidence_gate.json`
- `automix/eval_reports/final_qc_metrics.json`
- `automix/eval_reports/final_qc_evidence_gate.json`
- `automix/eval_reports/final_ab_preview_manifest.json`
- `automix/eval_reports/ab_preview_evidence_gate.json`
- `automix/review/final_human_approval.json`
- `automix/eval_reports/final_approval_evidence_gate.json`
- `automix/rollback/global_rollback_registry.json`
- `automix/eval_reports/rollback_evidence_gate.json`
- `automix/eval_reports/final_qc_report.md`
- `automix/export/project_state_manifest.json`
- `automix/export/plugin_mapping_summary.md`

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

## Limits

- Do not include raw stems, references, source packages, credentials, tokens, or secret files in the delivery package by default.
- Do not mark unsafe review copies as final-safe deliverables.
- This request does not replace human listening approval.
