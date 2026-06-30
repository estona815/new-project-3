# Final QC Evidence Gate

- Project: `project`
- Created UTC: `2026-06-02T16:27:57Z`
- Ready for delivery QC: `False`
- Ready for approval readiness: `False`
- Final audio: `.`
- QC passed: `False`
- True peak dBTP: `0.0`
- True peak ceiling dBTP: `-1.0`
- Render evidence ready: `False`
- Final audio matches render evidence: `False`

This gate does not approve audio or claim quality. It only checks measured final QC evidence.

## Blockers

- `final_audio_path_not_file`
- `final_qc_failure:qc_not_requested_or_primary_wav_missing`
- `final_qc_file_integrity_bit_depth_missing`
- `final_qc_file_integrity_channels_missing`
- `final_qc_file_integrity_duration_seconds_missing`
- `final_qc_file_integrity_sample_rate_missing`
- `final_qc_has_failures`
- `final_qc_not_passed`
- `final_qc_true_peak_above_ceiling`
- `final_render_evidence:final_export_state_not_safe`
- `final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- `final_render_evidence:primary_wav_render_missing`
- `final_render_evidence:selected_export_source_path_missing`
- `final_render_evidence_not_ready`
- `final_render_manifest_primary_wav_missing`

## Warnings

- none

## Audio File

- Path: `.`
- Valid WAV: `False`
- Duration seconds: ``
- Sample rate: ``
- Bit depth: ``
- Channels: ``
