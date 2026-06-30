# Final Approval Evidence Gate

- Project: `project`
- Created UTC: `2026-06-02T16:41:26Z`
- Ready for delivery request: `False`
- Approval pending only: `False`
- Approved: `False`
- Review decision: ``
- Loudness-matched A/B reviewed: `False`
- Final accepted at matched loudness: `False`
- Final QC evidence reviewed: `False`
- A/B evidence ready: `False`
- Final QC evidence ready: `False`

This gate does not approve audio. It checks that the human approval record is auditable.

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
- `final_render_evidence:final_export_state_not_safe`
- `final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- `final_render_evidence:primary_wav_render_missing`
- `final_render_evidence:selected_export_source_path_missing`
- `final_render_evidence_not_ready`

## Warnings

- none
