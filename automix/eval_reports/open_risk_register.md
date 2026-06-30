# Open Risk Register

- Project: `project`
- Created UTC: `2026-06-05T12:47:57Z`
- Passed: `False`
- Blockers: `308`
- Warnings: `118`
- Review items: `2`
- Info items: `1`

This register consolidates report risks and recommended next actions. It does not prove audio quality or user acceptance.

## Category Counts

- `ab_preview` blockers `11`, warnings `2`, review `0`, info `0`
- `artifact` blockers `2`, warnings `8`, review `0`, info `0`
- `delivery_readiness` blockers `81`, warnings `1`, review `0`, info `0`
- `final_export` blockers `1`, warnings `0`, review `0`, info `0`
- `harness` blockers `0`, warnings `1`, review `0`, info `0`
- `human_review` blockers `34`, warnings `1`, review `0`, info `0`
- `intent` blockers `7`, warnings `1`, review `1`, info `1`
- `package` blockers `76`, warnings `0`, review `0`, info `0`
- `plugin` blockers `70`, warnings `61`, review `0`, info `0`
- `processing_policy` blockers `0`, warnings `7`, review `0`, info `0`
- `qc` blockers `17`, warnings `30`, review `0`, info `0`
- `render` blockers `4`, warnings `1`, review `0`, info `0`
- `rollback` blockers `0`, warnings `3`, review `0`, info `0`
- `source` blockers `5`, warnings `2`, review `1`, info `0`

## Open Risks

### risk_001_eval_reports_ab_preview_evidence_gate_json_blocker_ab_preview_final_segment_missing

- Severity: `blocker`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `ab_preview_final_segment_missing`
- Summary: blockers: ab_preview_final_segment_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_002_eval_reports_ab_preview_evidence_gate_json_blocker_ab_preview_loudness_match_metrics_missing

- Severity: `blocker`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `ab_preview_loudness_match_metrics_missing`
- Summary: blockers: ab_preview_loudness_match_metrics_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_003_eval_reports_ab_preview_evidence_gate_json_blocker_ab_preview_manifest_has_warnings

- Severity: `blocker`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `ab_preview_manifest_has_warnings`
- Summary: blockers: ab_preview_manifest_has_warnings
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_004_eval_reports_ab_preview_evidence_gate_json_blocker_ab_preview_not_created

- Severity: `blocker`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `ab_preview_not_created`
- Summary: blockers: ab_preview_not_created
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_005_eval_reports_ab_preview_evidence_gate_json_blocker_ab_preview_not_loudness_matched

- Severity: `blocker`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `ab_preview_not_loudness_matched`
- Summary: blockers: ab_preview_not_loudness_matched
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_006_eval_reports_ab_preview_evidence_gate_json_blocker_ab_preview_original_segment_missing

- Severity: `blocker`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `ab_preview_original_segment_missing`
- Summary: blockers: ab_preview_original_segment_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_007_eval_reports_ab_preview_evidence_gate_json_blocker_ab_preview_segments_missing

- Severity: `blocker`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `ab_preview_segments_missing`
- Summary: blockers: ab_preview_segments_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_008_eval_reports_ab_preview_evidence_gate_json_blocker_ab_preview_too_few_segments

- Severity: `blocker`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `ab_preview_too_few_segments`
- Summary: blockers: ab_preview_too_few_segments
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_009_eval_reports_ab_preview_evidence_gate_json_blocker_preview_output_path_missing

- Severity: `blocker`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `preview_output_path_missing`
- Summary: blockers: preview_output_path_missing
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_010_eval_reports_ab_preview_evidence_gate_json_blocker_source_final_path_missing

- Severity: `blocker`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `source_final_path_missing`
- Summary: blockers: source_final_path_missing
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_011_eval_reports_ab_preview_evidence_gate_json_blocker_source_original_path_missing

- Severity: `blocker`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `source_original_path_missing`
- Summary: blockers: source_original_path_missing
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_012_eval_reports_artifact_evidence_gate_json_blocker_artifact_evidence_not_established

- Severity: `blocker`
- Category: `artifact`
- Source report: `eval_reports/artifact_evidence_gate.json`
- Code: `artifact_evidence_not_established`
- Summary: blockers: artifact_evidence_not_established
- Recommended next action: collect measured artifact metrics, source signal, or user feedback before artifact-focused work

### risk_013_eval_reports_artifact_evidence_gate_json_blocker_measured_artifact_metrics_missing

- Severity: `blocker`
- Category: `artifact`
- Source report: `eval_reports/artifact_evidence_gate.json`
- Code: `measured_artifact_metrics_missing`
- Summary: blockers: measured_artifact_metrics_missing
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_014_eval_reports_approval_export_readiness_json_blocker_ab_preview_evidence_ab_preview_final_segment

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_evidence:ab_preview_final_segment_missing`
- Summary: blockers: ab_preview_evidence:ab_preview_final_segment_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_015_eval_reports_approval_export_readiness_json_blocker_ab_preview_evidence_ab_preview_loudness_matc

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_evidence:ab_preview_loudness_match_metrics_missing`
- Summary: blockers: ab_preview_evidence:ab_preview_loudness_match_metrics_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_016_eval_reports_approval_export_readiness_json_blocker_ab_preview_evidence_ab_preview_manifest_has

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_evidence:ab_preview_manifest_has_warnings`
- Summary: blockers: ab_preview_evidence:ab_preview_manifest_has_warnings
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_017_eval_reports_approval_export_readiness_json_blocker_ab_preview_evidence_ab_preview_not_created

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_evidence:ab_preview_not_created`
- Summary: blockers: ab_preview_evidence:ab_preview_not_created
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_018_eval_reports_approval_export_readiness_json_blocker_ab_preview_evidence_ab_preview_not_loudness

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_evidence:ab_preview_not_loudness_matched`
- Summary: blockers: ab_preview_evidence:ab_preview_not_loudness_matched
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_019_eval_reports_approval_export_readiness_json_blocker_ab_preview_evidence_ab_preview_original_segm

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_evidence:ab_preview_original_segment_missing`
- Summary: blockers: ab_preview_evidence:ab_preview_original_segment_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_020_eval_reports_approval_export_readiness_json_blocker_ab_preview_evidence_ab_preview_segments_miss

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_evidence:ab_preview_segments_missing`
- Summary: blockers: ab_preview_evidence:ab_preview_segments_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_021_eval_reports_approval_export_readiness_json_blocker_ab_preview_evidence_ab_preview_too_few_segme

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_evidence:ab_preview_too_few_segments`
- Summary: blockers: ab_preview_evidence:ab_preview_too_few_segments
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_022_eval_reports_approval_export_readiness_json_blocker_ab_preview_evidence_preview_output_path_miss

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_evidence:preview_output_path_missing`
- Summary: blockers: ab_preview_evidence:preview_output_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_023_eval_reports_approval_export_readiness_json_blocker_ab_preview_evidence_source_final_path_missin

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_evidence:source_final_path_missing`
- Summary: blockers: ab_preview_evidence:source_final_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_024_eval_reports_approval_export_readiness_json_blocker_ab_preview_evidence_source_original_path_mis

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_evidence:source_original_path_missing`
- Summary: blockers: ab_preview_evidence:source_original_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_025_eval_reports_approval_export_readiness_json_blocker_ab_preview_evidence_not_ready

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_evidence_not_ready`
- Summary: blockers: ab_preview_evidence_not_ready
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_026_eval_reports_approval_export_readiness_json_blocker_ab_preview_missing_or_not_loudness_matched

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `ab_preview_missing_or_not_loudness_matched`
- Summary: blockers: ab_preview_missing_or_not_loudness_matched
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_027_eval_reports_approval_export_readiness_json_blocker_accepted_export_source_missing

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `accepted_export_source_missing`
- Summary: blockers: accepted_export_source_missing
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_028_eval_reports_approval_export_readiness_json_blocker_artifact_evidence_artifact_evidence_not_esta

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `artifact_evidence:artifact_evidence_not_established`
- Summary: blockers: artifact_evidence:artifact_evidence_not_established
- Recommended next action: collect measured artifact metrics, source signal, or user feedback before artifact-focused work

### risk_029_eval_reports_approval_export_readiness_json_blocker_artifact_evidence_measured_artifact_metrics

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `artifact_evidence:measured_artifact_metrics_missing`
- Summary: blockers: artifact_evidence:measured_artifact_metrics_missing
- Recommended next action: collect measured artifact metrics, source signal, or user feedback before artifact-focused work

### risk_030_eval_reports_approval_export_readiness_json_blocker_artifact_signal_artifact_signal_not_establis

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `artifact_signal:artifact_signal_not_established`
- Summary: blockers: artifact_signal:artifact_signal_not_established
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_031_eval_reports_approval_export_readiness_json_blocker_artifact_signal_measured_artifact_metrics_no

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `artifact_signal:measured_artifact_metrics_not_established`
- Summary: blockers: artifact_signal:measured_artifact_metrics_not_established
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_032_eval_reports_approval_export_readiness_json_blocker_final_human_approval_missing

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_human_approval_missing`
- Summary: blockers: final_human_approval_missing
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_033_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_audio_path_not_file

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_audio_path_not_file`
- Summary: blockers: final_qc_evidence:final_audio_path_not_file
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_034_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_qc_failure_qc_not_re

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing`
- Summary: blockers: final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_035_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_qc_file_integrity_bi

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_qc_file_integrity_bit_depth_missing`
- Summary: blockers: final_qc_evidence:final_qc_file_integrity_bit_depth_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_036_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_qc_file_integrity_ch

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_qc_file_integrity_channels_missing`
- Summary: blockers: final_qc_evidence:final_qc_file_integrity_channels_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_037_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_qc_file_integrity_du

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_qc_file_integrity_duration_seconds_missing`
- Summary: blockers: final_qc_evidence:final_qc_file_integrity_duration_seconds_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_038_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_qc_file_integrity_sa

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_qc_file_integrity_sample_rate_missing`
- Summary: blockers: final_qc_evidence:final_qc_file_integrity_sample_rate_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_039_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_qc_has_failures

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_qc_has_failures`
- Summary: blockers: final_qc_evidence:final_qc_has_failures
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_040_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_qc_not_passed

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_qc_not_passed`
- Summary: blockers: final_qc_evidence:final_qc_not_passed
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_041_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_qc_true_peak_above_c

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_qc_true_peak_above_ceiling`
- Summary: blockers: final_qc_evidence:final_qc_true_peak_above_ceiling
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_042_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_render_evidence_fina

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_render_evidence:final_export_state_not_safe`
- Summary: blockers: final_qc_evidence:final_render_evidence:final_export_state_not_safe
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_043_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_render_evidence_fina

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- Summary: blockers: final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_044_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_render_evidence_prim

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_render_evidence:primary_wav_render_missing`
- Summary: blockers: final_qc_evidence:final_render_evidence:primary_wav_render_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_045_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_render_evidence_sele

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_render_evidence:selected_export_source_path_missing`
- Summary: blockers: final_qc_evidence:final_render_evidence:selected_export_source_path_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_046_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_render_evidence_not

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_render_evidence_not_ready`
- Summary: blockers: final_qc_evidence:final_render_evidence_not_ready
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_047_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_final_render_manifest_prim

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence:final_render_manifest_primary_wav_missing`
- Summary: blockers: final_qc_evidence:final_render_manifest_primary_wav_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_048_eval_reports_approval_export_readiness_json_blocker_final_qc_evidence_not_ready

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_evidence_not_ready`
- Summary: blockers: final_qc_evidence_not_ready
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_049_eval_reports_approval_export_readiness_json_blocker_final_qc_missing_or_failed

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_qc_missing_or_failed`
- Summary: blockers: final_qc_missing_or_failed
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_050_eval_reports_approval_export_readiness_json_blocker_final_render_evidence_final_export_state_not

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_render_evidence:final_export_state_not_safe`
- Summary: blockers: final_render_evidence:final_export_state_not_safe
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_051_eval_reports_approval_export_readiness_json_blocker_final_render_evidence_final_render_manifest

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- Summary: blockers: final_render_evidence:final_render_manifest_diagnostic_or_report_only
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_052_eval_reports_approval_export_readiness_json_blocker_final_render_evidence_primary_wav_render_mis

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_render_evidence:primary_wav_render_missing`
- Summary: blockers: final_render_evidence:primary_wav_render_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_053_eval_reports_approval_export_readiness_json_blocker_final_render_evidence_selected_export_source

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_render_evidence:selected_export_source_path_missing`
- Summary: blockers: final_render_evidence:selected_export_source_path_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_054_eval_reports_approval_export_readiness_json_blocker_final_render_evidence_not_ready

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_render_evidence_not_ready`
- Summary: blockers: final_render_evidence_not_ready
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_055_eval_reports_approval_export_readiness_json_blocker_final_render_missing_or_diagnostic_only

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `final_render_missing_or_diagnostic_only`
- Summary: blockers: final_render_missing_or_diagnostic_only
- Recommended next action: rerun render or keep the package in diagnostic mode until render evidence exists

### risk_056_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_reacomp__cockos

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:ReaComp (Cockos):validation_report_has_no_write_safe_controls`
- Summary: blockers: plugin_semantic_validation:ReaComp (Cockos):validation_report_has_no_write_safe_controls
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_057_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_reacomp__cockos

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:ReaComp (Cockos):validation_report_not_passed:validation_unavailable`
- Summary: blockers: plugin_semantic_validation:ReaComp (Cockos):validation_report_not_passed:validation_unavailable
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_058_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_reacomp__cockos

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:ReaComp (Cockos):validation_report_not_safe_for_automix`
- Summary: blockers: plugin_semantic_validation:ReaComp (Cockos):validation_report_not_safe_for_automix
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_059_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_readelay__cockos

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:ReaDelay (Cockos):validation_report_has_no_write_safe_controls`
- Summary: blockers: plugin_semantic_validation:ReaDelay (Cockos):validation_report_has_no_write_safe_controls
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_060_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_readelay__cockos

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:ReaDelay (Cockos):validation_report_not_passed:validation_unavailable`
- Summary: blockers: plugin_semantic_validation:ReaDelay (Cockos):validation_report_not_passed:validation_unavailable
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_061_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_readelay__cockos

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:ReaDelay (Cockos):validation_report_not_safe_for_automix`
- Summary: blockers: plugin_semantic_validation:ReaDelay (Cockos):validation_report_not_safe_for_automix
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_062_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_reaeq__cockos__va

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:ReaEQ (Cockos):validation_report_has_no_write_safe_controls`
- Summary: blockers: plugin_semantic_validation:ReaEQ (Cockos):validation_report_has_no_write_safe_controls
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_063_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_reaeq__cockos__va

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:ReaEQ (Cockos):validation_report_not_passed:validation_unavailable`
- Summary: blockers: plugin_semantic_validation:ReaEQ (Cockos):validation_report_not_passed:validation_unavailable
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_064_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_reaeq__cockos__va

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:ReaEQ (Cockos):validation_report_not_safe_for_automix`
- Summary: blockers: plugin_semantic_validation:ReaEQ (Cockos):validation_report_not_safe_for_automix
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_065_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_no_passed_semanti

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:no_passed_semantic_validation_report:ReaComp (Cockos)`
- Summary: blockers: plugin_semantic_validation:no_passed_semantic_validation_report:ReaComp (Cockos)
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_066_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_no_passed_semanti

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:no_passed_semantic_validation_report:ReaDelay (Cockos)`
- Summary: blockers: plugin_semantic_validation:no_passed_semantic_validation_report:ReaDelay (Cockos)
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_067_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_no_passed_semanti

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:no_passed_semantic_validation_report:ReaEQ (Cockos)`
- Summary: blockers: plugin_semantic_validation:no_passed_semantic_validation_report:ReaEQ (Cockos)
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_068_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_semantic_validati

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:semantic_validation_passed_reports_missing`
- Summary: blockers: plugin_semantic_validation:semantic_validation_passed_reports_missing
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_069_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_validation_report

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:validation_report_missing:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- Summary: blockers: plugin_semantic_validation:validation_report_missing:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_070_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_validation_report

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:validation_report_missing:OTT (Xfer Records)`
- Summary: blockers: plugin_semantic_validation:validation_report_missing:OTT (Xfer Records)
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_071_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_validation_report

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:validation_report_missing:ReaVerbate (Cockos)`
- Summary: blockers: plugin_semantic_validation:validation_report_missing:ReaVerbate (Cockos)
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_072_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_validation_report

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:validation_report_missing:TDR Nova (Tokyo Dawn Labs)`
- Summary: blockers: plugin_semantic_validation:validation_report_missing:TDR Nova (Tokyo Dawn Labs)
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_073_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_validation_report

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_air_guard.jsfx`
- Summary: blockers: plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_air_guard.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_074_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_validation_report

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx`
- Summary: blockers: plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_075_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_validation_report

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_output_guard.jsfx`
- Summary: blockers: plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_output_guard.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_076_eval_reports_approval_export_readiness_json_blocker_plugin_semantic_validation_validation_report

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_presence_enhancer.jsfx`
- Summary: blockers: plugin_semantic_validation:validation_report_missing:Vocal Clarity Repair/vocal_presence_enhancer.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_077_eval_reports_approval_export_readiness_json_blocker_plugin_validation_preflight_required_plugin

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_validation_preflight:required_plugin_availability_missing:OTT (Xfer Records)`
- Summary: blockers: plugin_validation_preflight:required_plugin_availability_missing:OTT (Xfer Records)
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_078_eval_reports_approval_export_readiness_json_blocker_plugin_validation_preflight_required_plugin

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_validation_preflight:required_plugin_availability_missing:TDR Nova (Tokyo Dawn Labs)`
- Summary: blockers: plugin_validation_preflight:required_plugin_availability_missing:TDR Nova (Tokyo Dawn Labs)
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_079_eval_reports_approval_export_readiness_json_blocker_plugin_validation_preflight_semantic_paramet

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `plugin_validation_preflight:semantic_parameter_validation_required`
- Summary: blockers: plugin_validation_preflight:semantic_parameter_validation_required
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_080_eval_reports_approval_export_readiness_json_blocker_source_acceptance_source_acceptance_candidat

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `source_acceptance:source_acceptance_candidates_missing`
- Summary: blockers: source_acceptance:source_acceptance_candidates_missing
- Recommended next action: validate accepted source/stem evidence before final export packaging

### risk_081_eval_reports_approval_export_readiness_json_blocker_source_handoff_current_source_file_missing_v

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `source_handoff:current_source_file_missing:V37 RETURN ReaDelay filtered throw`
- Summary: blockers: source_handoff:current_source_file_missing:V37 RETURN ReaDelay filtered throw
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_082_eval_reports_approval_export_readiness_json_blocker_source_handoff_current_source_file_missing_v

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `source_handoff:current_source_file_missing:V37 RETURN ReaVerbate dark send`
- Summary: blockers: source_handoff:current_source_file_missing:V37 RETURN ReaVerbate dark send
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_083_eval_reports_approval_export_readiness_json_blocker_source_handoff_full_mix_unsafe_tracks_2

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `source_handoff:full_mix_unsafe_tracks:2`
- Summary: blockers: source_handoff:full_mix_unsafe_tracks:2
- Recommended next action: do not pitch-correct the full mix; request stems or keep manual review

### risk_084_eval_reports_approval_export_readiness_json_blocker_source_handoff_stem_requests_open_2

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/approval_export_readiness.json`
- Code: `source_handoff:stem_requests_open:2`
- Summary: blockers: source_handoff:stem_requests_open:2
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_085_eval_reports_final_delivery_consistency_gate_json_blocker_ab_preview_evidence_not_ready

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/final_delivery_consistency_gate.json`
- Code: `ab_preview_evidence_not_ready`
- Summary: blockers: ab_preview_evidence_not_ready
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_086_eval_reports_final_delivery_consistency_gate_json_blocker_ab_preview_output_path_missing

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/final_delivery_consistency_gate.json`
- Code: `ab_preview_output_path_missing`
- Summary: blockers: ab_preview_output_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_087_eval_reports_final_delivery_consistency_gate_json_blocker_deliverable_package_evidence_not_ready

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/final_delivery_consistency_gate.json`
- Code: `deliverable_package_evidence_not_ready`
- Summary: blockers: deliverable_package_evidence_not_ready
- Recommended next action: create a real final ZIP and validate package evidence before professional delivery readiness

### risk_088_eval_reports_final_delivery_consistency_gate_json_blocker_final_approval_evidence_not_ready

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/final_delivery_consistency_gate.json`
- Code: `final_approval_evidence_not_ready`
- Summary: blockers: final_approval_evidence_not_ready
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_089_eval_reports_final_delivery_consistency_gate_json_blocker_final_audio_path_missing

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/final_delivery_consistency_gate.json`
- Code: `final_audio_path_missing`
- Summary: blockers: final_audio_path_missing
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_090_eval_reports_final_delivery_consistency_gate_json_blocker_final_export_state_not_safe

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/final_delivery_consistency_gate.json`
- Code: `final_export_state_not_safe`
- Summary: blockers: final_export_state_not_safe
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_091_eval_reports_final_delivery_consistency_gate_json_blocker_final_qc_evidence_not_ready

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/final_delivery_consistency_gate.json`
- Code: `final_qc_evidence_not_ready`
- Summary: blockers: final_qc_evidence_not_ready
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_092_eval_reports_final_delivery_consistency_gate_json_blocker_final_render_evidence_not_ready

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/final_delivery_consistency_gate.json`
- Code: `final_render_evidence_not_ready`
- Summary: blockers: final_render_evidence_not_ready
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_093_eval_reports_final_delivery_consistency_gate_json_blocker_final_render_evidence_primary_wav_miss

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/final_delivery_consistency_gate.json`
- Code: `final_render_evidence_primary_wav_missing`
- Summary: blockers: final_render_evidence_primary_wav_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_094_eval_reports_final_delivery_consistency_gate_json_blocker_final_render_manifest_primary_wav_miss

- Severity: `blocker`
- Category: `delivery_readiness`
- Source report: `eval_reports/final_delivery_consistency_gate.json`
- Code: `final_render_manifest_primary_wav_missing`
- Summary: blockers: final_render_manifest_primary_wav_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_095_export_final_export_state_json_blocker_no_accepted_export_source

- Severity: `blocker`
- Category: `final_export`
- Source report: `export/final_export_state.json`
- Code: `no_accepted_export_source`
- Summary: blocked_reasons: no_accepted_export_source
- Recommended next action: complete and accept a reviewed draft source before final export

### risk_096_eval_reports_final_approval_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_final_segm

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_final_segment_missing`
- Summary: blockers: ab_preview_evidence:ab_preview_final_segment_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_097_eval_reports_final_approval_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_loudness_m

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_loudness_match_metrics_missing`
- Summary: blockers: ab_preview_evidence:ab_preview_loudness_match_metrics_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_098_eval_reports_final_approval_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_manifest_h

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_manifest_has_warnings`
- Summary: blockers: ab_preview_evidence:ab_preview_manifest_has_warnings
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_099_eval_reports_final_approval_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_not_create

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_not_created`
- Summary: blockers: ab_preview_evidence:ab_preview_not_created
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_100_eval_reports_final_approval_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_not_loudne

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_not_loudness_matched`
- Summary: blockers: ab_preview_evidence:ab_preview_not_loudness_matched
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_101_eval_reports_final_approval_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_original_s

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_original_segment_missing`
- Summary: blockers: ab_preview_evidence:ab_preview_original_segment_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_102_eval_reports_final_approval_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_segments_m

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_segments_missing`
- Summary: blockers: ab_preview_evidence:ab_preview_segments_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_103_eval_reports_final_approval_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_too_few_se

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_too_few_segments`
- Summary: blockers: ab_preview_evidence:ab_preview_too_few_segments
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_104_eval_reports_final_approval_evidence_gate_json_blocker_ab_preview_evidence_preview_output_path_m

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `ab_preview_evidence:preview_output_path_missing`
- Summary: blockers: ab_preview_evidence:preview_output_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_105_eval_reports_final_approval_evidence_gate_json_blocker_ab_preview_evidence_source_final_path_mis

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `ab_preview_evidence:source_final_path_missing`
- Summary: blockers: ab_preview_evidence:source_final_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_106_eval_reports_final_approval_evidence_gate_json_blocker_ab_preview_evidence_source_original_path

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `ab_preview_evidence:source_original_path_missing`
- Summary: blockers: ab_preview_evidence:source_original_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_107_eval_reports_final_approval_evidence_gate_json_blocker_ab_preview_evidence_not_ready

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `ab_preview_evidence_not_ready`
- Summary: blockers: ab_preview_evidence_not_ready
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_108_eval_reports_final_approval_evidence_gate_json_blocker_final_human_approval_missing

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_human_approval_missing`
- Summary: blockers: final_human_approval_missing
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_109_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_audio_path_not_fi

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_audio_path_not_file`
- Summary: blockers: final_qc_evidence:final_audio_path_not_file
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_110_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_qc_failure_qc_not

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing`
- Summary: blockers: final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_111_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_qc_file_integrity

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_file_integrity_bit_depth_missing`
- Summary: blockers: final_qc_evidence:final_qc_file_integrity_bit_depth_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_112_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_qc_file_integrity

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_file_integrity_channels_missing`
- Summary: blockers: final_qc_evidence:final_qc_file_integrity_channels_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_113_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_qc_file_integrity

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_file_integrity_duration_seconds_missing`
- Summary: blockers: final_qc_evidence:final_qc_file_integrity_duration_seconds_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_114_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_qc_file_integrity

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_file_integrity_sample_rate_missing`
- Summary: blockers: final_qc_evidence:final_qc_file_integrity_sample_rate_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_115_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_qc_has_failures

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_has_failures`
- Summary: blockers: final_qc_evidence:final_qc_has_failures
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_116_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_qc_not_passed

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_not_passed`
- Summary: blockers: final_qc_evidence:final_qc_not_passed
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_117_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_qc_true_peak_abov

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_true_peak_above_ceiling`
- Summary: blockers: final_qc_evidence:final_qc_true_peak_above_ceiling
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_118_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_render_evidence_f

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_render_evidence:final_export_state_not_safe`
- Summary: blockers: final_qc_evidence:final_render_evidence:final_export_state_not_safe
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_119_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_render_evidence_f

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- Summary: blockers: final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_120_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_render_evidence_p

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_render_evidence:primary_wav_render_missing`
- Summary: blockers: final_qc_evidence:final_render_evidence:primary_wav_render_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_121_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_render_evidence_s

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_render_evidence:selected_export_source_path_missing`
- Summary: blockers: final_qc_evidence:final_render_evidence:selected_export_source_path_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_122_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_render_evidence_n

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_render_evidence_not_ready`
- Summary: blockers: final_qc_evidence:final_render_evidence_not_ready
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_123_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_final_render_manifest_p

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence:final_render_manifest_primary_wav_missing`
- Summary: blockers: final_qc_evidence:final_render_manifest_primary_wav_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_124_eval_reports_final_approval_evidence_gate_json_blocker_final_qc_evidence_not_ready

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_qc_evidence_not_ready`
- Summary: blockers: final_qc_evidence_not_ready
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_125_eval_reports_final_approval_evidence_gate_json_blocker_final_render_evidence_final_export_state

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_render_evidence:final_export_state_not_safe`
- Summary: blockers: final_render_evidence:final_export_state_not_safe
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_126_eval_reports_final_approval_evidence_gate_json_blocker_final_render_evidence_final_render_manife

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- Summary: blockers: final_render_evidence:final_render_manifest_diagnostic_or_report_only
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_127_eval_reports_final_approval_evidence_gate_json_blocker_final_render_evidence_primary_wav_render

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_render_evidence:primary_wav_render_missing`
- Summary: blockers: final_render_evidence:primary_wav_render_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_128_eval_reports_final_approval_evidence_gate_json_blocker_final_render_evidence_selected_export_sou

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_render_evidence:selected_export_source_path_missing`
- Summary: blockers: final_render_evidence:selected_export_source_path_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_129_eval_reports_final_approval_evidence_gate_json_blocker_final_render_evidence_not_ready

- Severity: `blocker`
- Category: `human_review`
- Source report: `eval_reports/final_approval_evidence_gate.json`
- Code: `final_render_evidence_not_ready`
- Summary: blockers: final_render_evidence_not_ready
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_130_eval_reports_intent_classification_json_blocker_aggressive_creative_enhancement_disabled_by_defa

- Severity: `blocker`
- Category: `intent`
- Source report: `eval_reports/intent_classification.json`
- Code: `aggressive_creative_enhancement_disabled_by_default`
- Summary: blockers: aggressive_creative_enhancement_disabled_by_default
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_131_eval_reports_intent_classification_json_blocker_artifact_signal_not_established

- Severity: `blocker`
- Category: `intent`
- Source report: `eval_reports/intent_classification.json`
- Code: `artifact_signal_not_established`
- Summary: blockers: artifact_signal_not_established
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_132_eval_reports_intent_classification_json_blocker_explicit_rebeat_stems_and_arrangement_review_req

- Severity: `blocker`
- Category: `intent`
- Source report: `eval_reports/intent_classification.json`
- Code: `explicit_rebeat_stems_and_arrangement_review_required`
- Summary: blockers: explicit_rebeat_stems_and_arrangement_review_required
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_133_eval_reports_intent_classification_json_blocker_explicit_user_approval_and_preview_required

- Severity: `blocker`
- Category: `intent`
- Source report: `eval_reports/intent_classification.json`
- Code: `explicit_user_approval_and_preview_required`
- Summary: blockers: explicit_user_approval_and_preview_required
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_134_eval_reports_intent_classification_json_blocker_no_safe_vocal_candidate

- Severity: `blocker`
- Category: `intent`
- Source report: `eval_reports/intent_classification.json`
- Code: `no_safe_vocal_candidate`
- Summary: blockers: no_safe_vocal_candidate
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_135_eval_reports_intent_classification_json_blocker_stems_not_ready

- Severity: `blocker`
- Category: `intent`
- Source report: `eval_reports/intent_classification.json`
- Code: `stems_not_ready`
- Summary: blockers: stems_not_ready
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_136_eval_reports_intent_classification_json_blocker_validated_plugin_mapping_required

- Severity: `blocker`
- Category: `intent`
- Source report: `eval_reports/intent_classification.json`
- Code: `validated_plugin_mapping_required`
- Summary: blockers: validated_plugin_mapping_required
- Recommended next action: run plugin inventory and adapter validation before draft processing

### risk_137_eval_reports_deliverable_package_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_final

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_final_segment_missing`
- Summary: blockers: ab_preview_evidence:ab_preview_final_segment_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_138_eval_reports_deliverable_package_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_loudn

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_loudness_match_metrics_missing`
- Summary: blockers: ab_preview_evidence:ab_preview_loudness_match_metrics_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_139_eval_reports_deliverable_package_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_manif

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_manifest_has_warnings`
- Summary: blockers: ab_preview_evidence:ab_preview_manifest_has_warnings
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_140_eval_reports_deliverable_package_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_not_c

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_not_created`
- Summary: blockers: ab_preview_evidence:ab_preview_not_created
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_141_eval_reports_deliverable_package_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_not_l

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_not_loudness_matched`
- Summary: blockers: ab_preview_evidence:ab_preview_not_loudness_matched
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_142_eval_reports_deliverable_package_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_origi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_original_segment_missing`
- Summary: blockers: ab_preview_evidence:ab_preview_original_segment_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_143_eval_reports_deliverable_package_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_segme

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_segments_missing`
- Summary: blockers: ab_preview_evidence:ab_preview_segments_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_144_eval_reports_deliverable_package_evidence_gate_json_blocker_ab_preview_evidence_ab_preview_too_f

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `ab_preview_evidence:ab_preview_too_few_segments`
- Summary: blockers: ab_preview_evidence:ab_preview_too_few_segments
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_145_eval_reports_deliverable_package_evidence_gate_json_blocker_ab_preview_evidence_preview_output_p

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `ab_preview_evidence:preview_output_path_missing`
- Summary: blockers: ab_preview_evidence:preview_output_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_146_eval_reports_deliverable_package_evidence_gate_json_blocker_ab_preview_evidence_source_final_pat

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `ab_preview_evidence:source_final_path_missing`
- Summary: blockers: ab_preview_evidence:source_final_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_147_eval_reports_deliverable_package_evidence_gate_json_blocker_ab_preview_evidence_source_original

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `ab_preview_evidence:source_original_path_missing`
- Summary: blockers: ab_preview_evidence:source_original_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_148_eval_reports_deliverable_package_evidence_gate_json_blocker_ab_preview_evidence_gate_not_ready

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `ab_preview_evidence_gate_not_ready`
- Summary: blockers: ab_preview_evidence_gate_not_ready
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_149_eval_reports_deliverable_package_evidence_gate_json_blocker_deliverable_package_manifest_has_mis

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `deliverable_package_manifest_has_missing_files`
- Summary: blockers: deliverable_package_manifest_has_missing_files
- Recommended next action: create a real final ZIP and validate package evidence before professional delivery readiness

### risk_150_eval_reports_deliverable_package_evidence_gate_json_blocker_deliverable_package_not_created

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `deliverable_package_not_created`
- Summary: blockers: deliverable_package_not_created
- Recommended next action: create a real final ZIP and validate package evidence before professional delivery readiness

### risk_151_eval_reports_deliverable_package_evidence_gate_json_blocker_deliverable_package_size_missing_or

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `deliverable_package_size_missing_or_zero`
- Summary: blockers: deliverable_package_size_missing_or_zero
- Recommended next action: create a real final ZIP and validate package evidence before professional delivery readiness

### risk_152_eval_reports_deliverable_package_evidence_gate_json_blocker_deliverable_zip_path_missing

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `deliverable_zip_path_missing`
- Summary: blockers: deliverable_zip_path_missing
- Recommended next action: create or repair the deliverable ZIP and verify it opens cleanly

### risk_153_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_ab_preview_e

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:ab_preview_evidence:ab_preview_final_segment_missing`
- Summary: blockers: final_approval_evidence:ab_preview_evidence:ab_preview_final_segment_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_154_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_ab_preview_e

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:ab_preview_evidence:ab_preview_loudness_match_metrics_missing`
- Summary: blockers: final_approval_evidence:ab_preview_evidence:ab_preview_loudness_match_metrics_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_155_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_ab_preview_e

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:ab_preview_evidence:ab_preview_manifest_has_warnings`
- Summary: blockers: final_approval_evidence:ab_preview_evidence:ab_preview_manifest_has_warnings
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_156_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_ab_preview_e

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:ab_preview_evidence:ab_preview_not_created`
- Summary: blockers: final_approval_evidence:ab_preview_evidence:ab_preview_not_created
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_157_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_ab_preview_e

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:ab_preview_evidence:ab_preview_not_loudness_matched`
- Summary: blockers: final_approval_evidence:ab_preview_evidence:ab_preview_not_loudness_matched
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_158_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_ab_preview_e

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:ab_preview_evidence:ab_preview_original_segment_missing`
- Summary: blockers: final_approval_evidence:ab_preview_evidence:ab_preview_original_segment_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_159_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_ab_preview_e

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:ab_preview_evidence:ab_preview_segments_missing`
- Summary: blockers: final_approval_evidence:ab_preview_evidence:ab_preview_segments_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_160_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_ab_preview_e

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:ab_preview_evidence:ab_preview_too_few_segments`
- Summary: blockers: final_approval_evidence:ab_preview_evidence:ab_preview_too_few_segments
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_161_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_ab_preview_e

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:ab_preview_evidence:preview_output_path_missing`
- Summary: blockers: final_approval_evidence:ab_preview_evidence:preview_output_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_162_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_ab_preview_e

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:ab_preview_evidence:source_final_path_missing`
- Summary: blockers: final_approval_evidence:ab_preview_evidence:source_final_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_163_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_ab_preview_e

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:ab_preview_evidence:source_original_path_missing`
- Summary: blockers: final_approval_evidence:ab_preview_evidence:source_original_path_missing
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_164_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_ab_preview_e

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:ab_preview_evidence_not_ready`
- Summary: blockers: final_approval_evidence:ab_preview_evidence_not_ready
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_165_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_human

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_human_approval_missing`
- Summary: blockers: final_approval_evidence:final_human_approval_missing
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_166_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_audio_path_not_file`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_audio_path_not_file
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_167_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_168_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_qc_file_integrity_bit_depth_missing`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_qc_file_integrity_bit_depth_missing
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_169_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_qc_file_integrity_channels_missing`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_qc_file_integrity_channels_missing
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_170_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_qc_file_integrity_duration_seconds_missing`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_qc_file_integrity_duration_seconds_missing
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_171_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_qc_file_integrity_sample_rate_missing`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_qc_file_integrity_sample_rate_missing
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_172_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_qc_has_failures`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_qc_has_failures
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_173_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_qc_not_passed`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_qc_not_passed
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_174_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_qc_true_peak_above_ceiling`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_qc_true_peak_above_ceiling
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_175_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_render_evidence:final_export_state_not_safe`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_render_evidence:final_export_state_not_safe
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_176_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_177_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_render_evidence:primary_wav_render_missing`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_render_evidence:primary_wav_render_missing
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_178_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_render_evidence:selected_export_source_path_missing`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_render_evidence:selected_export_source_path_missing
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_179_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_render_evidence_not_ready`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_render_evidence_not_ready
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_180_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence:final_render_manifest_primary_wav_missing`
- Summary: blockers: final_approval_evidence:final_qc_evidence:final_render_manifest_primary_wav_missing
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_181_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_qc_evi

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_qc_evidence_not_ready`
- Summary: blockers: final_approval_evidence:final_qc_evidence_not_ready
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_182_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_render

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_render_evidence:final_export_state_not_safe`
- Summary: blockers: final_approval_evidence:final_render_evidence:final_export_state_not_safe
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_183_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_render

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- Summary: blockers: final_approval_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_184_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_render

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_render_evidence:primary_wav_render_missing`
- Summary: blockers: final_approval_evidence:final_render_evidence:primary_wav_render_missing
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_185_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_render

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_render_evidence:selected_export_source_path_missing`
- Summary: blockers: final_approval_evidence:final_render_evidence:selected_export_source_path_missing
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_186_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_final_render

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence:final_render_evidence_not_ready`
- Summary: blockers: final_approval_evidence:final_render_evidence_not_ready
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_187_eval_reports_deliverable_package_evidence_gate_json_blocker_final_approval_evidence_gate_not_rea

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_approval_evidence_gate_not_ready`
- Summary: blockers: final_approval_evidence_gate_not_ready
- Recommended next action: record matched-loudness A/B approval evidence before delivery request

### risk_188_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_audio_path_n

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_audio_path_not_file`
- Summary: blockers: final_qc_evidence:final_audio_path_not_file
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_189_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_qc_failure_q

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing`
- Summary: blockers: final_qc_evidence:final_qc_failure:qc_not_requested_or_primary_wav_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_190_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_qc_file_inte

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_file_integrity_bit_depth_missing`
- Summary: blockers: final_qc_evidence:final_qc_file_integrity_bit_depth_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_191_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_qc_file_inte

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_file_integrity_channels_missing`
- Summary: blockers: final_qc_evidence:final_qc_file_integrity_channels_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_192_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_qc_file_inte

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_file_integrity_duration_seconds_missing`
- Summary: blockers: final_qc_evidence:final_qc_file_integrity_duration_seconds_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_193_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_qc_file_inte

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_file_integrity_sample_rate_missing`
- Summary: blockers: final_qc_evidence:final_qc_file_integrity_sample_rate_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_194_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_qc_has_failu

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_has_failures`
- Summary: blockers: final_qc_evidence:final_qc_has_failures
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_195_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_qc_not_passe

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_not_passed`
- Summary: blockers: final_qc_evidence:final_qc_not_passed
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_196_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_qc_true_peak

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_qc_true_peak_above_ceiling`
- Summary: blockers: final_qc_evidence:final_qc_true_peak_above_ceiling
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_197_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_render_evide

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_render_evidence:final_export_state_not_safe`
- Summary: blockers: final_qc_evidence:final_render_evidence:final_export_state_not_safe
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_198_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_render_evide

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- Summary: blockers: final_qc_evidence:final_render_evidence:final_render_manifest_diagnostic_or_report_only
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_199_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_render_evide

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_render_evidence:primary_wav_render_missing`
- Summary: blockers: final_qc_evidence:final_render_evidence:primary_wav_render_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_200_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_render_evide

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_render_evidence:selected_export_source_path_missing`
- Summary: blockers: final_qc_evidence:final_render_evidence:selected_export_source_path_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_201_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_render_evide

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_render_evidence_not_ready`
- Summary: blockers: final_qc_evidence:final_render_evidence_not_ready
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_202_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_final_render_manif

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence:final_render_manifest_primary_wav_missing`
- Summary: blockers: final_qc_evidence:final_render_manifest_primary_wav_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_203_eval_reports_deliverable_package_evidence_gate_json_blocker_final_qc_evidence_gate_not_ready

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_qc_evidence_gate_not_ready`
- Summary: blockers: final_qc_evidence_gate_not_ready
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_204_eval_reports_deliverable_package_evidence_gate_json_blocker_final_render_evidence_final_export_s

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_render_evidence:final_export_state_not_safe`
- Summary: blockers: final_render_evidence:final_export_state_not_safe
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_205_eval_reports_deliverable_package_evidence_gate_json_blocker_final_render_evidence_final_render_m

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- Summary: blockers: final_render_evidence:final_render_manifest_diagnostic_or_report_only
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_206_eval_reports_deliverable_package_evidence_gate_json_blocker_final_render_evidence_primary_wav_re

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_render_evidence:primary_wav_render_missing`
- Summary: blockers: final_render_evidence:primary_wav_render_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_207_eval_reports_deliverable_package_evidence_gate_json_blocker_final_render_evidence_selected_expor

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_render_evidence:selected_export_source_path_missing`
- Summary: blockers: final_render_evidence:selected_export_source_path_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_208_eval_reports_deliverable_package_evidence_gate_json_blocker_final_render_evidence_gate_not_ready

- Severity: `blocker`
- Category: `package`
- Source report: `eval_reports/deliverable_package_evidence_gate.json`
- Code: `final_render_evidence_gate_not_ready`
- Summary: blockers: final_render_evidence_gate_not_ready
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_209_export_deliverable_package_manifest_json_blocker_files_missing_automix_eval_reports_final_qc_rep

- Severity: `blocker`
- Category: `package`
- Source report: `export/deliverable_package_manifest.json`
- Code: `files_missing:automix/eval_reports/final_qc_report.md`
- Summary: Deliverable package is missing `automix/eval_reports/final_qc_report.md`
- Recommended next action: repair missing package evidence files before rebuilding the deliverable ZIP

### risk_210_export_deliverable_package_manifest_json_blocker_package_created_false

- Severity: `blocker`
- Category: `package`
- Source report: `export/deliverable_package_manifest.json`
- Code: `package_created_false`
- Summary: Deliverable package manifest does not show a created ZIP
- Recommended next action: create the deliverable ZIP after final render, QC, A/B, approval, and rollback evidence are ready

### risk_211_export_deliverable_package_manifest_json_blocker_package_size_bytes_missing_or_zero

- Severity: `blocker`
- Category: `package`
- Source report: `export/deliverable_package_manifest.json`
- Code: `package_size_bytes_missing_or_zero`
- Summary: Deliverable package manifest has no nonzero package size
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_212_export_deliverable_package_manifest_json_blocker_zip_path_missing

- Severity: `blocker`
- Category: `package`
- Source report: `export/deliverable_package_manifest.json`
- Code: `zip_path_missing`
- Summary: Deliverable package manifest has no ZIP path
- Recommended next action: create or repair the deliverable ZIP and verify it opens cleanly

### risk_213_eval_reports_plugin_availability_decision_gate_json_blocker_operator_decision_missing_ott__xfer

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_availability_decision_gate.json`
- Code: `operator_decision_missing:OTT (Xfer Records)`
- Summary: blockers: operator_decision_missing:OTT (Xfer Records)
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_214_eval_reports_plugin_availability_decision_gate_json_blocker_operator_decision_missing_tdr_nova

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_availability_decision_gate.json`
- Code: `operator_decision_missing:TDR Nova (Tokyo Dawn Labs)`
- Summary: blockers: operator_decision_missing:TDR Nova (Tokyo Dawn Labs)
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_215_eval_reports_plugin_availability_decision_gate_json_blocker_plugin_availability_decision_manifes

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_availability_decision_gate.json`
- Code: `plugin_availability_decision_manifest_missing`
- Summary: blockers: plugin_availability_decision_manifest_missing
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_216_eval_reports_plugin_semantic_validation_collection_plan_json_blocker_availability_decision_missi

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_collection_plan.json`
- Code: `availability_decision_missing:OTT (Xfer Records)`
- Summary: blockers: availability_decision_missing:OTT (Xfer Records)
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_217_eval_reports_plugin_semantic_validation_collection_plan_json_blocker_availability_decision_missi

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_collection_plan.json`
- Code: `availability_decision_missing:TDR Nova (Tokyo Dawn Labs)`
- Summary: blockers: availability_decision_missing:TDR Nova (Tokyo Dawn Labs)
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_218_eval_reports_plugin_semantic_validation_gate_json_blocker_reacomp__cockos__validation_report_has

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `ReaComp (Cockos):validation_report_has_no_write_safe_controls`
- Summary: blockers: ReaComp (Cockos):validation_report_has_no_write_safe_controls
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_219_eval_reports_plugin_semantic_validation_gate_json_blocker_reacomp__cockos__validation_report_not

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `ReaComp (Cockos):validation_report_not_passed:validation_unavailable`
- Summary: blockers: ReaComp (Cockos):validation_report_not_passed:validation_unavailable
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_220_eval_reports_plugin_semantic_validation_gate_json_blocker_reacomp__cockos__validation_report_not

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `ReaComp (Cockos):validation_report_not_safe_for_automix`
- Summary: blockers: ReaComp (Cockos):validation_report_not_safe_for_automix
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_221_eval_reports_plugin_semantic_validation_gate_json_blocker_readelay__cockos__validation_report_ha

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `ReaDelay (Cockos):validation_report_has_no_write_safe_controls`
- Summary: blockers: ReaDelay (Cockos):validation_report_has_no_write_safe_controls
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_222_eval_reports_plugin_semantic_validation_gate_json_blocker_readelay__cockos__validation_report_no

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `ReaDelay (Cockos):validation_report_not_passed:validation_unavailable`
- Summary: blockers: ReaDelay (Cockos):validation_report_not_passed:validation_unavailable
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_223_eval_reports_plugin_semantic_validation_gate_json_blocker_readelay__cockos__validation_report_no

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `ReaDelay (Cockos):validation_report_not_safe_for_automix`
- Summary: blockers: ReaDelay (Cockos):validation_report_not_safe_for_automix
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_224_eval_reports_plugin_semantic_validation_gate_json_blocker_reaeq__cockos__validation_report_has_n

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `ReaEQ (Cockos):validation_report_has_no_write_safe_controls`
- Summary: blockers: ReaEQ (Cockos):validation_report_has_no_write_safe_controls
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_225_eval_reports_plugin_semantic_validation_gate_json_blocker_reaeq__cockos__validation_report_not_p

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `ReaEQ (Cockos):validation_report_not_passed:validation_unavailable`
- Summary: blockers: ReaEQ (Cockos):validation_report_not_passed:validation_unavailable
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_226_eval_reports_plugin_semantic_validation_gate_json_blocker_reaeq__cockos__validation_report_not_s

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `ReaEQ (Cockos):validation_report_not_safe_for_automix`
- Summary: blockers: ReaEQ (Cockos):validation_report_not_safe_for_automix
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_227_eval_reports_plugin_semantic_validation_gate_json_blocker_no_passed_semantic_validation_report_r

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `no_passed_semantic_validation_report:ReaComp (Cockos)`
- Summary: blockers: no_passed_semantic_validation_report:ReaComp (Cockos)
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_228_eval_reports_plugin_semantic_validation_gate_json_blocker_no_passed_semantic_validation_report_r

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `no_passed_semantic_validation_report:ReaDelay (Cockos)`
- Summary: blockers: no_passed_semantic_validation_report:ReaDelay (Cockos)
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_229_eval_reports_plugin_semantic_validation_gate_json_blocker_no_passed_semantic_validation_report_r

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `no_passed_semantic_validation_report:ReaEQ (Cockos)`
- Summary: blockers: no_passed_semantic_validation_report:ReaEQ (Cockos)
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_230_eval_reports_plugin_semantic_validation_gate_json_blocker_semantic_validation_passed_reports_mis

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `semantic_validation_passed_reports_missing`
- Summary: blockers: semantic_validation_passed_reports_missing
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_231_eval_reports_plugin_semantic_validation_gate_json_blocker_validation_report_missing_codex_vocal

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `validation_report_missing:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- Summary: blockers: validation_report_missing:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_232_eval_reports_plugin_semantic_validation_gate_json_blocker_validation_report_missing_ott__xfer_re

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `validation_report_missing:OTT (Xfer Records)`
- Summary: blockers: validation_report_missing:OTT (Xfer Records)
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_233_eval_reports_plugin_semantic_validation_gate_json_blocker_validation_report_missing_reaverbate

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `validation_report_missing:ReaVerbate (Cockos)`
- Summary: blockers: validation_report_missing:ReaVerbate (Cockos)
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_234_eval_reports_plugin_semantic_validation_gate_json_blocker_validation_report_missing_tdr_nova__to

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `validation_report_missing:TDR Nova (Tokyo Dawn Labs)`
- Summary: blockers: validation_report_missing:TDR Nova (Tokyo Dawn Labs)
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_235_eval_reports_plugin_semantic_validation_gate_json_blocker_validation_report_missing_vocal_clarit

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `validation_report_missing:Vocal Clarity Repair/vocal_air_guard.jsfx`
- Summary: blockers: validation_report_missing:Vocal Clarity Repair/vocal_air_guard.jsfx
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_236_eval_reports_plugin_semantic_validation_gate_json_blocker_validation_report_missing_vocal_clarit

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `validation_report_missing:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx`
- Summary: blockers: validation_report_missing:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_237_eval_reports_plugin_semantic_validation_gate_json_blocker_validation_report_missing_vocal_clarit

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `validation_report_missing:Vocal Clarity Repair/vocal_output_guard.jsfx`
- Summary: blockers: validation_report_missing:Vocal Clarity Repair/vocal_output_guard.jsfx
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_238_eval_reports_plugin_semantic_validation_gate_json_blocker_validation_report_missing_vocal_clarit

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `validation_report_missing:Vocal Clarity Repair/vocal_presence_enhancer.jsfx`
- Summary: blockers: validation_report_missing:Vocal Clarity Repair/vocal_presence_enhancer.jsfx
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_239_eval_reports_plugin_semantic_validation_queue_json_blocker_collection_job_blocked_ott__xfer_reco

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_queue.json`
- Code: `collection_job_blocked:OTT (Xfer Records):availability_decision_missing:OTT (Xfer Records)`
- Summary: blockers: collection_job_blocked:OTT (Xfer Records):availability_decision_missing:OTT (Xfer Records)
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_240_eval_reports_plugin_semantic_validation_queue_json_blocker_collection_job_blocked_tdr_nova__toky

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_queue.json`
- Code: `collection_job_blocked:TDR Nova (Tokyo Dawn Labs):availability_decision_missing:TDR Nova (Tokyo Dawn Labs)`
- Summary: blockers: collection_job_blocked:TDR Nova (Tokyo Dawn Labs):availability_decision_missing:TDR Nova (Tokyo Dawn Labs)
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_241_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_plugin_semantic_valid

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `plugin_semantic_validation_runtime_manifest_missing`
- Summary: blockers: plugin_semantic_validation_runtime_manifest_missing
- Recommended next action: validate queued REAPER runtime evidence and rerun semantic validation before parameter writes

### risk_242_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_manifest_job

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_manifest_job_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx`
- Summary: blockers: runtime_manifest_job_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_243_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_manifest_job

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_manifest_job_missing:semantic_validation_02_reaverbate_cockos`
- Summary: blockers: runtime_manifest_job_missing:semantic_validation_02_reaverbate_cockos
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_244_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_manifest_job

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_manifest_job_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx`
- Summary: blockers: runtime_manifest_job_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_245_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_manifest_job

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_manifest_job_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx`
- Summary: blockers: runtime_manifest_job_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_246_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_manifest_job

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_manifest_job_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx`
- Summary: blockers: runtime_manifest_job_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_247_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_manifest_job

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_manifest_job_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx`
- Summary: blockers: runtime_manifest_job_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_248_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_manifest_job

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_manifest_job_missing:semantic_validation_07_reacomp_cockos`
- Summary: blockers: runtime_manifest_job_missing:semantic_validation_07_reacomp_cockos
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_249_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_manifest_job

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_manifest_job_missing:semantic_validation_08_readelay_cockos`
- Summary: blockers: runtime_manifest_job_missing:semantic_validation_08_readelay_cockos
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_250_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_manifest_job

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_manifest_job_missing:semantic_validation_09_reaeq_cockos`
- Summary: blockers: runtime_manifest_job_missing:semantic_validation_09_reaeq_cockos
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_251_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_validation_re

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_validation_report_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx`
- Summary: blockers: runtime_validation_report_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_252_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_validation_re

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_validation_report_missing:semantic_validation_02_reaverbate_cockos`
- Summary: blockers: runtime_validation_report_missing:semantic_validation_02_reaverbate_cockos
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_253_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_validation_re

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_validation_report_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx`
- Summary: blockers: runtime_validation_report_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_254_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_validation_re

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_validation_report_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx`
- Summary: blockers: runtime_validation_report_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_255_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_validation_re

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_validation_report_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx`
- Summary: blockers: runtime_validation_report_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_256_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_validation_re

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_validation_report_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx`
- Summary: blockers: runtime_validation_report_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_257_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_validation_re

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_validation_report_missing:semantic_validation_07_reacomp_cockos`
- Summary: blockers: runtime_validation_report_missing:semantic_validation_07_reacomp_cockos
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_258_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_validation_re

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_validation_report_missing:semantic_validation_08_readelay_cockos`
- Summary: blockers: runtime_validation_report_missing:semantic_validation_08_readelay_cockos
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_259_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_blocker_runtime_validation_re

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `runtime_validation_report_missing:semantic_validation_09_reaeq_cockos`
- Summary: blockers: runtime_validation_report_missing:semantic_validation_09_reaeq_cockos
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_260_eval_reports_plugin_semantic_validation_runtime_observation_gate_json_blocker_runtime_observatio

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_gate.json`
- Code: `runtime_observation_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx`
- Summary: blockers: runtime_observation_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_261_eval_reports_plugin_semantic_validation_runtime_observation_gate_json_blocker_runtime_observatio

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_gate.json`
- Code: `runtime_observation_missing:semantic_validation_02_reaverbate_cockos`
- Summary: blockers: runtime_observation_missing:semantic_validation_02_reaverbate_cockos
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_262_eval_reports_plugin_semantic_validation_runtime_observation_gate_json_blocker_runtime_observatio

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_gate.json`
- Code: `runtime_observation_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx`
- Summary: blockers: runtime_observation_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_263_eval_reports_plugin_semantic_validation_runtime_observation_gate_json_blocker_runtime_observatio

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_gate.json`
- Code: `runtime_observation_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx`
- Summary: blockers: runtime_observation_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_264_eval_reports_plugin_semantic_validation_runtime_observation_gate_json_blocker_runtime_observatio

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_gate.json`
- Code: `runtime_observation_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx`
- Summary: blockers: runtime_observation_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_265_eval_reports_plugin_semantic_validation_runtime_observation_gate_json_blocker_runtime_observatio

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_gate.json`
- Code: `runtime_observation_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx`
- Summary: blockers: runtime_observation_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_266_eval_reports_plugin_semantic_validation_runtime_observation_gate_json_blocker_runtime_observatio

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_gate.json`
- Code: `runtime_observation_missing:semantic_validation_07_reacomp_cockos`
- Summary: blockers: runtime_observation_missing:semantic_validation_07_reacomp_cockos
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_267_eval_reports_plugin_semantic_validation_runtime_observation_gate_json_blocker_runtime_observatio

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_gate.json`
- Code: `runtime_observation_missing:semantic_validation_08_readelay_cockos`
- Summary: blockers: runtime_observation_missing:semantic_validation_08_readelay_cockos
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_268_eval_reports_plugin_semantic_validation_runtime_observation_gate_json_blocker_runtime_observatio

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_gate.json`
- Code: `runtime_observation_missing:semantic_validation_09_reaeq_cockos`
- Summary: blockers: runtime_observation_missing:semantic_validation_09_reaeq_cockos
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_269_eval_reports_plugin_semantic_validation_runtime_report_authoring_gate_json_blocker_runtime_repor

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.json`
- Code: `runtime_report_authoring_package_not_ready:no_accepted_runtime_observations`
- Summary: blockers: runtime_report_authoring_package_not_ready:no_accepted_runtime_observations
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_270_eval_reports_plugin_semantic_validation_runtime_report_authoring_package_json_blocker_accepted_r

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_report_authoring_package.json`
- Code: `accepted_runtime_observations_missing`
- Summary: blockers: accepted_runtime_observations_missing
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_271_eval_reports_plugin_validation_action_plan_json_blocker_codex_vocal_vocal_ai_artifact_split_tame

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx:collect_reaper_observed_semantic_validation`
- Summary: blockers: Codex Vocal/vocal_ai_artifact_split_tamer.jsfx:collect_reaper_observed_semantic_validation
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_272_eval_reports_plugin_validation_action_plan_json_blocker_ott__xfer_records__install_or_disable_un

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `OTT (Xfer Records):install_or_disable_unavailable_plugin`
- Summary: blockers: OTT (Xfer Records):install_or_disable_unavailable_plugin
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_273_eval_reports_plugin_validation_action_plan_json_blocker_reacomp__cockos__rerun_or_keep_plugin_re

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `ReaComp (Cockos):rerun_or_keep_plugin_read_only`
- Summary: blockers: ReaComp (Cockos):rerun_or_keep_plugin_read_only
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_274_eval_reports_plugin_validation_action_plan_json_blocker_readelay__cockos__rerun_or_keep_plugin_r

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `ReaDelay (Cockos):rerun_or_keep_plugin_read_only`
- Summary: blockers: ReaDelay (Cockos):rerun_or_keep_plugin_read_only
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_275_eval_reports_plugin_validation_action_plan_json_blocker_reaeq__cockos__rerun_or_keep_plugin_read

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `ReaEQ (Cockos):rerun_or_keep_plugin_read_only`
- Summary: blockers: ReaEQ (Cockos):rerun_or_keep_plugin_read_only
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_276_eval_reports_plugin_validation_action_plan_json_blocker_reaverbate__cockos__collect_reaper_obser

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `ReaVerbate (Cockos):collect_reaper_observed_semantic_validation`
- Summary: blockers: ReaVerbate (Cockos):collect_reaper_observed_semantic_validation
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_277_eval_reports_plugin_validation_action_plan_json_blocker_tdr_nova__tokyo_dawn_labs__install_or_di

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `TDR Nova (Tokyo Dawn Labs):install_or_disable_unavailable_plugin`
- Summary: blockers: TDR Nova (Tokyo Dawn Labs):install_or_disable_unavailable_plugin
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_278_eval_reports_plugin_validation_action_plan_json_blocker_vocal_clarity_repair_vocal_air_guard_jsf

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `Vocal Clarity Repair/vocal_air_guard.jsfx:collect_reaper_observed_semantic_validation`
- Summary: blockers: Vocal Clarity Repair/vocal_air_guard.jsfx:collect_reaper_observed_semantic_validation
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_279_eval_reports_plugin_validation_action_plan_json_blocker_vocal_clarity_repair_vocal_demud_dynamic

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx:collect_reaper_observed_semantic_validation`
- Summary: blockers: Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx:collect_reaper_observed_semantic_validation
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_280_eval_reports_plugin_validation_action_plan_json_blocker_vocal_clarity_repair_vocal_output_guard

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `Vocal Clarity Repair/vocal_output_guard.jsfx:collect_reaper_observed_semantic_validation`
- Summary: blockers: Vocal Clarity Repair/vocal_output_guard.jsfx:collect_reaper_observed_semantic_validation
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_281_eval_reports_plugin_validation_action_plan_json_blocker_vocal_clarity_repair_vocal_presence_enha

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `Vocal Clarity Repair/vocal_presence_enhancer.jsfx:collect_reaper_observed_semantic_validation`
- Summary: blockers: Vocal Clarity Repair/vocal_presence_enhancer.jsfx:collect_reaper_observed_semantic_validation
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_282_eval_reports_real_project_plugin_readiness_json_blocker_safe_draft_plugin_ready_false

- Severity: `blocker`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `safe_draft_plugin_ready_false`
- Summary: No validated safe plugin adapter set is ready for safe draft automation
- Recommended next action: run plugin inventory and adapter validation before draft processing

### risk_283_eval_reports_final_qc_evidence_gate_json_blocker_final_audio_path_not_file

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_audio_path_not_file`
- Summary: blockers: final_audio_path_not_file
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_284_eval_reports_final_qc_evidence_gate_json_blocker_final_qc_failure_qc_not_requested_or_primary_wa

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_qc_failure:qc_not_requested_or_primary_wav_missing`
- Summary: blockers: final_qc_failure:qc_not_requested_or_primary_wav_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_285_eval_reports_final_qc_evidence_gate_json_blocker_final_qc_file_integrity_bit_depth_missing

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_qc_file_integrity_bit_depth_missing`
- Summary: blockers: final_qc_file_integrity_bit_depth_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_286_eval_reports_final_qc_evidence_gate_json_blocker_final_qc_file_integrity_channels_missing

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_qc_file_integrity_channels_missing`
- Summary: blockers: final_qc_file_integrity_channels_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_287_eval_reports_final_qc_evidence_gate_json_blocker_final_qc_file_integrity_duration_seconds_missin

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_qc_file_integrity_duration_seconds_missing`
- Summary: blockers: final_qc_file_integrity_duration_seconds_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_288_eval_reports_final_qc_evidence_gate_json_blocker_final_qc_file_integrity_sample_rate_missing

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_qc_file_integrity_sample_rate_missing`
- Summary: blockers: final_qc_file_integrity_sample_rate_missing
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_289_eval_reports_final_qc_evidence_gate_json_blocker_final_qc_has_failures

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_qc_has_failures`
- Summary: blockers: final_qc_has_failures
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_290_eval_reports_final_qc_evidence_gate_json_blocker_final_qc_not_passed

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_qc_not_passed`
- Summary: blockers: final_qc_not_passed
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_291_eval_reports_final_qc_evidence_gate_json_blocker_final_qc_true_peak_above_ceiling

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_qc_true_peak_above_ceiling`
- Summary: blockers: final_qc_true_peak_above_ceiling
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_292_eval_reports_final_qc_evidence_gate_json_blocker_final_render_evidence_final_export_state_not_sa

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_render_evidence:final_export_state_not_safe`
- Summary: blockers: final_render_evidence:final_export_state_not_safe
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_293_eval_reports_final_qc_evidence_gate_json_blocker_final_render_evidence_final_render_manifest_dia

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_render_evidence:final_render_manifest_diagnostic_or_report_only`
- Summary: blockers: final_render_evidence:final_render_manifest_diagnostic_or_report_only
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_294_eval_reports_final_qc_evidence_gate_json_blocker_final_render_evidence_primary_wav_render_missin

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_render_evidence:primary_wav_render_missing`
- Summary: blockers: final_render_evidence:primary_wav_render_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_295_eval_reports_final_qc_evidence_gate_json_blocker_final_render_evidence_selected_export_source_pa

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_render_evidence:selected_export_source_path_missing`
- Summary: blockers: final_render_evidence:selected_export_source_path_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_296_eval_reports_final_qc_evidence_gate_json_blocker_final_render_evidence_not_ready

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_render_evidence_not_ready`
- Summary: blockers: final_render_evidence_not_ready
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_297_eval_reports_final_qc_evidence_gate_json_blocker_final_render_manifest_primary_wav_missing

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_evidence_gate.json`
- Code: `final_render_manifest_primary_wav_missing`
- Summary: blockers: final_render_manifest_primary_wav_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_298_eval_reports_final_qc_metrics_json_blocker_qc_not_requested_or_primary_wav_missing

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/final_qc_metrics.json`
- Code: `qc_not_requested_or_primary_wav_missing`
- Summary: failures: qc_not_requested_or_primary_wav_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_299_eval_reports_global_qc_summary_json_blocker_qc_failure_for_final_delivery

- Severity: `blocker`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `qc_failure_for_final_delivery`
- Summary: critical_blockers: qc_failure_for_final_delivery
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_300_eval_reports_final_render_evidence_gate_json_blocker_final_export_state_not_safe

- Severity: `blocker`
- Category: `render`
- Source report: `eval_reports/final_render_evidence_gate.json`
- Code: `final_export_state_not_safe`
- Summary: blockers: final_export_state_not_safe
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_301_eval_reports_final_render_evidence_gate_json_blocker_final_render_manifest_diagnostic_or_report

- Severity: `blocker`
- Category: `render`
- Source report: `eval_reports/final_render_evidence_gate.json`
- Code: `final_render_manifest_diagnostic_or_report_only`
- Summary: blockers: final_render_manifest_diagnostic_or_report_only
- Recommended next action: rerun render or keep the package in diagnostic mode until render evidence exists

### risk_302_eval_reports_final_render_evidence_gate_json_blocker_primary_wav_render_missing

- Severity: `blocker`
- Category: `render`
- Source report: `eval_reports/final_render_evidence_gate.json`
- Code: `primary_wav_render_missing`
- Summary: blockers: primary_wav_render_missing
- Recommended next action: create a real primary WAV render and validate render evidence before final QC

### risk_303_eval_reports_final_render_evidence_gate_json_blocker_selected_export_source_path_missing

- Severity: `blocker`
- Category: `render`
- Source report: `eval_reports/final_render_evidence_gate.json`
- Code: `selected_export_source_path_missing`
- Summary: blockers: selected_export_source_path_missing
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_304_eval_reports_real_project_source_safety_map_json_blocker_full_mix_unsafe_tracks_2

- Severity: `blocker`
- Category: `source`
- Source report: `eval_reports/real_project_source_safety_map.json`
- Code: `full_mix_unsafe_tracks:2`
- Summary: 2 full mix unsafe tracks require review before automation
- Recommended next action: do not pitch-correct the full mix; request stems or keep manual review

### risk_305_eval_reports_real_project_source_safety_map_json_blocker_high_risk_track_unsafe_source_full_mix

- Severity: `blocker`
- Category: `source`
- Source report: `eval_reports/real_project_source_safety_map.json`
- Code: `high_risk_track:unsafe:SOURCE full mix reference muted`
- Summary: High-risk source track `SOURCE full mix reference muted` needs `provide_isolated_stems`
- Recommended next action: provide_isolated_stems

### risk_306_eval_reports_real_project_source_safety_map_json_blocker_high_risk_track_unsafe_v37_instrumental

- Severity: `blocker`
- Category: `source`
- Source report: `eval_reports/real_project_source_safety_map.json`
- Code: `high_risk_track:unsafe:V37 INSTRUMENTAL BUS free EQ pocket`
- Summary: High-risk source track `V37 INSTRUMENTAL BUS free EQ pocket` needs `provide_isolated_stems`
- Recommended next action: provide_isolated_stems

### risk_307_eval_reports_real_project_source_safety_map_json_blocker_stem_required_tracks_2

- Severity: `blocker`
- Category: `source`
- Source report: `eval_reports/real_project_source_safety_map.json`
- Code: `stem_required_tracks:2`
- Summary: 2 stem required tracks require review before automation
- Recommended next action: provide isolated stems before vocal recovery, placement, or pitch work

### risk_308_eval_reports_source_acceptance_gate_json_blocker_source_acceptance_candidates_missing

- Severity: `blocker`
- Category: `source`
- Source report: `eval_reports/source_acceptance_gate.json`
- Code: `source_acceptance_candidates_missing`
- Summary: blockers: source_acceptance_candidates_missing
- Recommended next action: validate accepted source/stem evidence before final export packaging

### risk_309_eval_reports_ab_preview_evidence_gate_json_warning_final_render_manifest_missing_ab_link_unverif

- Severity: `warning`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `final_render_manifest_missing_ab_link_unverified`
- Summary: warnings: final_render_manifest_missing_ab_link_unverified
- Recommended next action: rerun render or keep the package in diagnostic mode until render evidence exists

### risk_310_eval_reports_ab_preview_evidence_gate_json_warning_manifest_ab_preview_not_requested_or_missing

- Severity: `warning`
- Category: `ab_preview`
- Source report: `eval_reports/ab_preview_evidence_gate.json`
- Code: `manifest:ab_preview_not_requested_or_missing_sources`
- Summary: warnings: manifest:ab_preview_not_requested_or_missing_sources
- Recommended next action: create and validate a measured loudness-matched A/B preview before approval

### risk_311_eval_reports_artifact_evidence_gate_json_warning_feedback_feedback_baseline_is_not_user_evidence

- Severity: `warning`
- Category: `artifact`
- Source report: `eval_reports/artifact_evidence_gate.json`
- Code: `feedback:feedback_baseline_is_not_user_evidence`
- Summary: warnings: feedback:feedback_baseline_is_not_user_evidence
- Recommended next action: record or resolve user feedback with measured QC and loudness-matched A/B evidence

### risk_312_eval_reports_artifact_evidence_gate_json_warning_feedback_user_artifact_feedback_missing

- Severity: `warning`
- Category: `artifact`
- Source report: `eval_reports/artifact_evidence_gate.json`
- Code: `feedback:user_artifact_feedback_missing`
- Summary: warnings: feedback:user_artifact_feedback_missing
- Recommended next action: record or resolve user feedback with measured QC and loudness-matched A/B evidence

### risk_313_eval_reports_artifact_evidence_gate_json_warning_report_only_metric_final_qc_vocal_preservation

- Severity: `warning`
- Category: `artifact`
- Source report: `eval_reports/artifact_evidence_gate.json`
- Code: `report_only_metric:final_qc.vocal_preservation.ai_fizz_score`
- Summary: warnings: report_only_metric:final_qc.vocal_preservation.ai_fizz_score
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_314_eval_reports_artifact_evidence_gate_json_warning_report_only_metric_final_qc_vocal_preservation

- Severity: `warning`
- Category: `artifact`
- Source report: `eval_reports/artifact_evidence_gate.json`
- Code: `report_only_metric:final_qc.vocal_preservation.metallic_artifact_score`
- Summary: warnings: report_only_metric:final_qc.vocal_preservation.metallic_artifact_score
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_315_eval_reports_artifact_evidence_gate_json_warning_report_only_metric_final_qc_vocal_preservation

- Severity: `warning`
- Category: `artifact`
- Source report: `eval_reports/artifact_evidence_gate.json`
- Code: `report_only_metric:final_qc.vocal_preservation.sibilance_splatter_score`
- Summary: warnings: report_only_metric:final_qc.vocal_preservation.sibilance_splatter_score
- Recommended next action: run final QC on the primary WAV and validate the metrics against render evidence

### risk_316_eval_reports_artifact_evidence_gate_json_warning_report_only_metric_premaster_ai_artifact_risk_p

- Severity: `warning`
- Category: `artifact`
- Source report: `eval_reports/artifact_evidence_gate.json`
- Code: `report_only_metric:premaster.ai_artifact_risk_profile.high_fizz_risk`
- Summary: warnings: report_only_metric:premaster.ai_artifact_risk_profile.high_fizz_risk
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_317_eval_reports_artifact_evidence_gate_json_warning_report_only_metric_premaster_ai_artifact_risk_p

- Severity: `warning`
- Category: `artifact`
- Source report: `eval_reports/artifact_evidence_gate.json`
- Code: `report_only_metric:premaster.ai_artifact_risk_profile.metallic_harshness_risk`
- Summary: warnings: report_only_metric:premaster.ai_artifact_risk_profile.metallic_harshness_risk
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_318_eval_reports_artifact_evidence_gate_json_warning_report_only_metric_premaster_ai_artifact_risk_p

- Severity: `warning`
- Category: `artifact`
- Source report: `eval_reports/artifact_evidence_gate.json`
- Code: `report_only_metric:premaster.ai_artifact_risk_profile.sibilance_splatter_risk`
- Summary: warnings: report_only_metric:premaster.ai_artifact_risk_profile.sibilance_splatter_risk
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_319_eval_reports_professional_readiness_audit_json_warning_final_delivery_not_requested_readiness_is

- Severity: `warning`
- Category: `delivery_readiness`
- Source report: `eval_reports/professional_readiness_audit.json`
- Code: `final_delivery_not_requested_readiness_is_documentation_and_gate_inventory_only`
- Summary: warnings: final_delivery_not_requested_readiness_is_documentation_and_gate_inventory_only
- Recommended next action: run final-delivery readiness only after accepted source, render, package, QC, A/B, and approval exist

### risk_320_eval_reports_fixture_coverage_audit_json_warning_fixture_coverage_complete_static_only

- Severity: `warning`
- Category: `harness`
- Source report: `eval_reports/fixture_coverage_audit.json`
- Code: `fixture_coverage_complete_static_only`
- Summary: warnings: fixture_coverage_complete_static_only
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_321_review_recovery_review_gate_summary_json_warning_no_recovery_drafts_to_review

- Severity: `warning`
- Category: `human_review`
- Source report: `review/recovery_review_gate_summary.json`
- Code: `no_recovery_drafts_to_review`
- Summary: warnings: no_recovery_drafts_to_review
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_322_eval_reports_intent_classification_json_warning_no_validated_safe_plugin_adapters

- Severity: `warning`
- Category: `intent`
- Source report: `eval_reports/intent_classification.json`
- Code: `no_validated_safe_plugin_adapters`
- Summary: warnings: no_validated_safe_plugin_adapters
- Recommended next action: validate stock/JSFX/plugin adapter mappings before safe draft work

### risk_323_eval_reports_plugin_availability_operator_decision_package_json_warning_operator_disable_or_inst

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_availability_operator_decision_package.json`
- Code: `operator_disable_or_install_decision_required`
- Summary: warnings: operator_disable_or_install_decision_required
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_324_eval_reports_plugin_availability_resolution_plan_json_warning_operator_disable_or_install_decisi

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_availability_resolution_plan.json`
- Code: `operator_disable_or_install_decision_required`
- Summary: warnings: operator_disable_or_install_decision_required
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_325_eval_reports_plugin_semantic_validation_collection_plan_json_warning_reacomp__cockos__some_seman

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_collection_plan.json`
- Code: `ReaComp (Cockos):some_semantic_controls_remain_write_blocked`
- Summary: warnings: ReaComp (Cockos):some_semantic_controls_remain_write_blocked
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_326_eval_reports_plugin_semantic_validation_collection_plan_json_warning_readelay__cockos__some_sema

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_collection_plan.json`
- Code: `ReaDelay (Cockos):some_semantic_controls_remain_write_blocked`
- Summary: warnings: ReaDelay (Cockos):some_semantic_controls_remain_write_blocked
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_327_eval_reports_plugin_semantic_validation_collection_plan_json_warning_reaeq__cockos__some_semanti

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_collection_plan.json`
- Code: `ReaEQ (Cockos):some_semantic_controls_remain_write_blocked`
- Summary: warnings: ReaEQ (Cockos):some_semantic_controls_remain_write_blocked
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_328_eval_reports_plugin_semantic_validation_gate_json_warning_reacomp__cockos__some_semantic_control

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `ReaComp (Cockos):some_semantic_controls_remain_write_blocked`
- Summary: warnings: ReaComp (Cockos):some_semantic_controls_remain_write_blocked
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_329_eval_reports_plugin_semantic_validation_gate_json_warning_readelay__cockos__some_semantic_contro

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `ReaDelay (Cockos):some_semantic_controls_remain_write_blocked`
- Summary: warnings: ReaDelay (Cockos):some_semantic_controls_remain_write_blocked
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_330_eval_reports_plugin_semantic_validation_gate_json_warning_reaeq__cockos__some_semantic_controls

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_gate.json`
- Code: `ReaEQ (Cockos):some_semantic_controls_remain_write_blocked`
- Summary: warnings: ReaEQ (Cockos):some_semantic_controls_remain_write_blocked
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_331_eval_reports_plugin_semantic_validation_queue_json_warning_reacomp__cockos__some_semantic_contro

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_queue.json`
- Code: `ReaComp (Cockos):some_semantic_controls_remain_write_blocked`
- Summary: warnings: ReaComp (Cockos):some_semantic_controls_remain_write_blocked
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_332_eval_reports_plugin_semantic_validation_queue_json_warning_readelay__cockos__some_semantic_contr

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_queue.json`
- Code: `ReaDelay (Cockos):some_semantic_controls_remain_write_blocked`
- Summary: warnings: ReaDelay (Cockos):some_semantic_controls_remain_write_blocked
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_333_eval_reports_plugin_semantic_validation_queue_json_warning_reaeq__cockos__some_semantic_controls

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_queue.json`
- Code: `ReaEQ (Cockos):some_semantic_controls_remain_write_blocked`
- Summary: warnings: ReaEQ (Cockos):some_semantic_controls_remain_write_blocked
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_334_eval_reports_plugin_semantic_validation_runtime_collection_package_json_warning_blocked_queue_jo

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_collection_package.json`
- Code: `blocked_queue_jobs_remain:2`
- Summary: warnings: blocked_queue_jobs_remain:2
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_335_eval_reports_plugin_semantic_validation_runtime_collector_package_json_warning_blocked_queue_job

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_collector_package.json`
- Code: `blocked_queue_jobs_remain:2`
- Summary: warnings: blocked_queue_jobs_remain:2
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_336_eval_reports_plugin_semantic_validation_runtime_evidence_gate_json_warning_blocked_queue_jobs_re

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`
- Code: `blocked_queue_jobs_remain:2`
- Summary: warnings: blocked_queue_jobs_remain:2
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_337_eval_reports_plugin_semantic_validation_runtime_observation_gate_json_warning_blocked_queue_jobs

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_gate.json`
- Code: `blocked_queue_jobs_remain:2`
- Summary: warnings: blocked_queue_jobs_remain:2
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_338_eval_reports_plugin_semantic_validation_runtime_observation_provenance_gate_json_warning_runtime

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json`
- Code: `runtime_observation_files_missing:9`
- Summary: warnings: runtime_observation_files_missing:9
- Recommended next action: repair missing package evidence files before rebuilding the deliverable ZIP

### risk_339_eval_reports_plugin_semantic_validation_runtime_observation_provenance_gate_json_warning_semanti

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json`
- Code: `semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx:runtime_observation_file_missing`
- Summary: warnings: semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx:runtime_observation_file_missing
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_340_eval_reports_plugin_semantic_validation_runtime_observation_provenance_gate_json_warning_semanti

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json`
- Code: `semantic_validation_02_reaverbate_cockos:runtime_observation_file_missing`
- Summary: warnings: semantic_validation_02_reaverbate_cockos:runtime_observation_file_missing
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_341_eval_reports_plugin_semantic_validation_runtime_observation_provenance_gate_json_warning_semanti

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json`
- Code: `semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx:runtime_observation_file_missing`
- Summary: warnings: semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx:runtime_observation_file_missing
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_342_eval_reports_plugin_semantic_validation_runtime_observation_provenance_gate_json_warning_semanti

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json`
- Code: `semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx:runtime_observation_file_missing`
- Summary: warnings: semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx:runtime_observation_file_missing
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_343_eval_reports_plugin_semantic_validation_runtime_observation_provenance_gate_json_warning_semanti

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json`
- Code: `semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx:runtime_observation_file_missing`
- Summary: warnings: semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx:runtime_observation_file_missing
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_344_eval_reports_plugin_semantic_validation_runtime_observation_provenance_gate_json_warning_semanti

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json`
- Code: `semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx:runtime_observation_file_missing`
- Summary: warnings: semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx:runtime_observation_file_missing
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_345_eval_reports_plugin_semantic_validation_runtime_observation_provenance_gate_json_warning_semanti

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json`
- Code: `semantic_validation_07_reacomp_cockos:runtime_observation_file_missing`
- Summary: warnings: semantic_validation_07_reacomp_cockos:runtime_observation_file_missing
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_346_eval_reports_plugin_semantic_validation_runtime_observation_provenance_gate_json_warning_semanti

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json`
- Code: `semantic_validation_08_readelay_cockos:runtime_observation_file_missing`
- Summary: warnings: semantic_validation_08_readelay_cockos:runtime_observation_file_missing
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_347_eval_reports_plugin_semantic_validation_runtime_observation_provenance_gate_json_warning_semanti

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json`
- Code: `semantic_validation_09_reaeq_cockos:runtime_observation_file_missing`
- Summary: warnings: semantic_validation_09_reaeq_cockos:runtime_observation_file_missing
- Recommended next action: collect REAPER-observed semantic parameter validation reports before parameter writes

### risk_348_eval_reports_plugin_validation_action_plan_json_warning_codex_vocal_vocal_ai_artifact_split_tame

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx:availability_only_not_write_safety`
- Summary: warnings: Codex Vocal/vocal_ai_artifact_split_tamer.jsfx:availability_only_not_write_safety
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_349_eval_reports_plugin_validation_action_plan_json_warning_reacomp__cockos__availability_only_not_w

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `ReaComp (Cockos):availability_only_not_write_safety`
- Summary: warnings: ReaComp (Cockos):availability_only_not_write_safety
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_350_eval_reports_plugin_validation_action_plan_json_warning_reacomp__cockos__some_semantic_controls

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `ReaComp (Cockos):some_semantic_controls_remain_write_blocked`
- Summary: warnings: ReaComp (Cockos):some_semantic_controls_remain_write_blocked
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_351_eval_reports_plugin_validation_action_plan_json_warning_readelay__cockos__availability_only_not

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `ReaDelay (Cockos):availability_only_not_write_safety`
- Summary: warnings: ReaDelay (Cockos):availability_only_not_write_safety
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_352_eval_reports_plugin_validation_action_plan_json_warning_readelay__cockos__some_semantic_controls

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `ReaDelay (Cockos):some_semantic_controls_remain_write_blocked`
- Summary: warnings: ReaDelay (Cockos):some_semantic_controls_remain_write_blocked
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_353_eval_reports_plugin_validation_action_plan_json_warning_reaeq__cockos__availability_only_not_wri

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `ReaEQ (Cockos):availability_only_not_write_safety`
- Summary: warnings: ReaEQ (Cockos):availability_only_not_write_safety
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_354_eval_reports_plugin_validation_action_plan_json_warning_reaeq__cockos__some_semantic_controls_re

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `ReaEQ (Cockos):some_semantic_controls_remain_write_blocked`
- Summary: warnings: ReaEQ (Cockos):some_semantic_controls_remain_write_blocked
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_355_eval_reports_plugin_validation_action_plan_json_warning_reaverbate__cockos__availability_only_no

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `ReaVerbate (Cockos):availability_only_not_write_safety`
- Summary: warnings: ReaVerbate (Cockos):availability_only_not_write_safety
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_356_eval_reports_plugin_validation_action_plan_json_warning_vocal_clarity_repair_vocal_air_guard_jsf

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `Vocal Clarity Repair/vocal_air_guard.jsfx:availability_only_not_write_safety`
- Summary: warnings: Vocal Clarity Repair/vocal_air_guard.jsfx:availability_only_not_write_safety
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_357_eval_reports_plugin_validation_action_plan_json_warning_vocal_clarity_repair_vocal_demud_dynamic

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx:availability_only_not_write_safety`
- Summary: warnings: Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx:availability_only_not_write_safety
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_358_eval_reports_plugin_validation_action_plan_json_warning_vocal_clarity_repair_vocal_output_guard

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `Vocal Clarity Repair/vocal_output_guard.jsfx:availability_only_not_write_safety`
- Summary: warnings: Vocal Clarity Repair/vocal_output_guard.jsfx:availability_only_not_write_safety
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_359_eval_reports_plugin_validation_action_plan_json_warning_vocal_clarity_repair_vocal_presence_enha

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `Vocal Clarity Repair/vocal_presence_enhancer.jsfx:availability_only_not_write_safety`
- Summary: warnings: Vocal Clarity Repair/vocal_presence_enhancer.jsfx:availability_only_not_write_safety
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_360_eval_reports_plugin_validation_action_plan_json_warning_adapter_validation_reports_unavailable

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `adapter_validation_reports_unavailable`
- Summary: warnings: adapter_validation_reports_unavailable
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_361_eval_reports_plugin_validation_action_plan_json_warning_availability_does_not_grant_write_safety

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/plugin_validation_action_plan.json`
- Code: `availability_does_not_grant_write_safety`
- Summary: warnings: availability_does_not_grant_write_safety
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_362_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_codex_v

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- Summary: Plugin mapping is missing or unsafe: `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_363_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_ott__xf

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:OTT (Xfer Records)`
- Summary: Plugin mapping is missing or unsafe: `OTT (Xfer Records)`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_364_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_reacomp

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:ReaComp (Cockos)`
- Summary: Plugin mapping is missing or unsafe: `ReaComp (Cockos)`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_365_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_readela

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:ReaDelay (Cockos)`
- Summary: Plugin mapping is missing or unsafe: `ReaDelay (Cockos)`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_366_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_reaeq

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:ReaEQ (Cockos)`
- Summary: Plugin mapping is missing or unsafe: `ReaEQ (Cockos)`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_367_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_reaverb

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:ReaVerbate (Cockos)`
- Summary: Plugin mapping is missing or unsafe: `ReaVerbate (Cockos)`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_368_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_tdr_nov

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:TDR Nova (Tokyo Dawn Labs)`
- Summary: Plugin mapping is missing or unsafe: `TDR Nova (Tokyo Dawn Labs)`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_369_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_vocal_c

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:Vocal Clarity Repair/vocal_air_guard.jsfx`
- Summary: Plugin mapping is missing or unsafe: `Vocal Clarity Repair/vocal_air_guard.jsfx`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_370_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_vocal_c

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx`
- Summary: Plugin mapping is missing or unsafe: `Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_371_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_vocal_c

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:Vocal Clarity Repair/vocal_output_guard.jsfx`
- Summary: Plugin mapping is missing or unsafe: `Vocal Clarity Repair/vocal_output_guard.jsfx`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_372_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_vocal_c

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:Vocal Clarity Repair/vocal_presence_enhancer.jsfx`
- Summary: Plugin mapping is missing or unsafe: `Vocal Clarity Repair/vocal_presence_enhancer.jsfx`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_373_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_validat

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:validated EQ/dynamic EQ or JSFX artifact guard adapter`
- Summary: Plugin mapping is missing or unsafe: `validated EQ/dynamic EQ or JSFX artifact guard adapter`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_374_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_validat

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:validated EQ/dynamics/limiter adapter`
- Summary: Plugin mapping is missing or unsafe: `validated EQ/dynamics/limiter adapter`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_375_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_validat

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:validated EQ/dynamics/utility adapter`
- Summary: Plugin mapping is missing or unsafe: `validated EQ/dynamics/utility adapter`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_376_eval_reports_real_project_plugin_readiness_json_warning_missing_or_unsafe_plugin_mapping_validat

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `missing_or_unsafe_plugin_mapping:validated pitch correction adapter`
- Summary: Plugin mapping is missing or unsafe: `validated pitch correction adapter`
- Recommended next action: map, validate, or explicitly disable this plugin before automation

### risk_377_eval_reports_real_project_plugin_readiness_json_warning_no_validated_safe_plugin_adapters

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/real_project_plugin_readiness.json`
- Code: `no_validated_safe_plugin_adapters`
- Summary: warnings: no_validated_safe_plugin_adapters
- Recommended next action: validate stock/JSFX/plugin adapter mappings before safe draft work

### risk_378_eval_reports_reaper_runtime_collection_operator_readiness_json_warning_availability_decisions_no

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/reaper_runtime_collection_operator_readiness.json`
- Code: `availability_decisions_not_ready_for_complete_collection`
- Summary: warnings: availability_decisions_not_ready_for_complete_collection
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_379_eval_reports_reaper_runtime_collection_operator_readiness_json_warning_availability_operator_dec

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/reaper_runtime_collection_operator_readiness.json`
- Code: `availability_operator_decisions_missing:2`
- Summary: warnings: availability_operator_decisions_missing:2
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_380_eval_reports_reaper_runtime_collection_operator_readiness_json_warning_complete_operator_collect

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/reaper_runtime_collection_operator_readiness.json`
- Code: `complete_operator_collection_blocked_by_queue_jobs:2`
- Summary: warnings: complete_operator_collection_blocked_by_queue_jobs:2
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_381_eval_reports_reaper_runtime_collector_safety_audit_json_warning_blocked_queue_jobs_remain_2

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/reaper_runtime_collector_safety_audit.json`
- Code: `blocked_queue_jobs_remain:2`
- Summary: warnings: blocked_queue_jobs_remain:2
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_382_eval_reports_reaper_runtime_collector_safety_audit_json_warning_collector_writes_raw_observation

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/reaper_runtime_collector_safety_audit.json`
- Code: `collector_writes_raw_observation_files`
- Summary: warnings: collector_writes_raw_observation_files
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_383_eval_reports_reaper_runtime_collector_safety_audit_json_warning_temporary_probe_track_mutation_d

- Severity: `warning`
- Category: `plugin`
- Source report: `eval_reports/reaper_runtime_collector_safety_audit.json`
- Code: `temporary_probe_track_mutation_detected`
- Summary: warnings: temporary_probe_track_mutation_detected
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_384_eval_reports_processing_policy_audit_json_warning_chain_plan_policy_clean_final_safe_premaster_c

- Severity: `warning`
- Category: `processing_policy`
- Source report: `eval_reports/processing_policy_audit.json`
- Code: `chain_plan_policy_clean:final_safe_premaster_chain_plan.json`
- Summary: warnings: chain_plan_policy_clean:final_safe_premaster_chain_plan.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_385_eval_reports_processing_policy_audit_json_warning_chain_plan_policy_clean_final_vocal_space_appl

- Severity: `warning`
- Category: `processing_policy`
- Source report: `eval_reports/processing_policy_audit.json`
- Code: `chain_plan_policy_clean:final_vocal_space_applicator_plan.json`
- Summary: warnings: chain_plan_policy_clean:final_vocal_space_applicator_plan.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_386_eval_reports_processing_policy_audit_json_warning_chain_plan_policy_clean_final_vocal_space_carv

- Severity: `warning`
- Category: `processing_policy`
- Source report: `eval_reports/processing_policy_audit.json`
- Code: `chain_plan_policy_clean:final_vocal_space_carving_chain_plan.json`
- Summary: warnings: chain_plan_policy_clean:final_vocal_space_carving_chain_plan.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_387_eval_reports_processing_policy_audit_json_warning_chain_plan_policy_clean_high_quality_mix_maste

- Severity: `warning`
- Category: `processing_policy`
- Source report: `eval_reports/processing_policy_audit.json`
- Code: `chain_plan_policy_clean:high_quality_mix_master_readiness_plan.json`
- Summary: warnings: chain_plan_policy_clean:high_quality_mix_master_readiness_plan.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_388_eval_reports_processing_policy_audit_json_warning_chain_plan_policy_clean_project_premaster_chai

- Severity: `warning`
- Category: `processing_policy`
- Source report: `eval_reports/processing_policy_audit.json`
- Code: `chain_plan_policy_clean:project_premaster_chain_plan.json`
- Summary: warnings: chain_plan_policy_clean:project_premaster_chain_plan.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_389_eval_reports_processing_policy_audit_json_warning_chain_plan_policy_clean_project_reference_matc

- Severity: `warning`
- Category: `processing_policy`
- Source report: `eval_reports/processing_policy_audit.json`
- Code: `chain_plan_policy_clean:project_reference_match_adjustment_plan.json`
- Summary: warnings: chain_plan_policy_clean:project_reference_match_adjustment_plan.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_390_eval_reports_processing_policy_audit_json_warning_chain_plan_policy_clean_real_project_dry_run_c

- Severity: `warning`
- Category: `processing_policy`
- Source report: `eval_reports/processing_policy_audit.json`
- Code: `chain_plan_policy_clean:real_project_dry_run_chain_proposals.json`
- Summary: warnings: chain_plan_policy_clean:real_project_dry_run_chain_proposals.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_391_eval_reports_global_qc_summary_json_warning_analysis_only_no_audio_recovery_rendered

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `analysis_only_no_audio_recovery_rendered`
- Summary: warnings: analysis_only_no_audio_recovery_rendered
- Recommended next action: rerun render or keep the package in diagnostic mode until render evidence exists

### risk_392_eval_reports_global_qc_summary_json_warning_audio_source_classification_not_run_no_track_audio

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `audio_source_classification_not_run_no_track_audio`
- Summary: warnings: audio_source_classification_not_run_no_track_audio
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_393_eval_reports_global_qc_summary_json_warning_chain_plan_policy_clean_final_safe_premaster_chain_p

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `chain_plan_policy_clean:final_safe_premaster_chain_plan.json`
- Summary: warnings: chain_plan_policy_clean:final_safe_premaster_chain_plan.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_394_eval_reports_global_qc_summary_json_warning_chain_plan_policy_clean_final_vocal_space_applicator

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `chain_plan_policy_clean:final_vocal_space_applicator_plan.json`
- Summary: warnings: chain_plan_policy_clean:final_vocal_space_applicator_plan.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_395_eval_reports_global_qc_summary_json_warning_chain_plan_policy_clean_final_vocal_space_carving_ch

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `chain_plan_policy_clean:final_vocal_space_carving_chain_plan.json`
- Summary: warnings: chain_plan_policy_clean:final_vocal_space_carving_chain_plan.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_396_eval_reports_global_qc_summary_json_warning_chain_plan_policy_clean_high_quality_mix_master_read

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `chain_plan_policy_clean:high_quality_mix_master_readiness_plan.json`
- Summary: warnings: chain_plan_policy_clean:high_quality_mix_master_readiness_plan.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_397_eval_reports_global_qc_summary_json_warning_chain_plan_policy_clean_project_premaster_chain_plan

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `chain_plan_policy_clean:project_premaster_chain_plan.json`
- Summary: warnings: chain_plan_policy_clean:project_premaster_chain_plan.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_398_eval_reports_global_qc_summary_json_warning_chain_plan_policy_clean_project_reference_match_adju

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `chain_plan_policy_clean:project_reference_match_adjustment_plan.json`
- Summary: warnings: chain_plan_policy_clean:project_reference_match_adjustment_plan.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_399_eval_reports_global_qc_summary_json_warning_chain_plan_policy_clean_real_project_dry_run_chain_p

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `chain_plan_policy_clean:real_project_dry_run_chain_proposals.json`
- Summary: warnings: chain_plan_policy_clean:real_project_dry_run_chain_proposals.json
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_400_eval_reports_global_qc_summary_json_warning_github_integration_dry_run_only

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `github_integration_dry_run_only`
- Summary: warnings: github_integration_dry_run_only
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_401_eval_reports_global_qc_summary_json_warning_intent_blocker_aggressive_creative_enhancement_disab

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `intent_blocker:aggressive_creative_enhancement_disabled_by_default`
- Summary: warnings: intent_blocker:aggressive_creative_enhancement_disabled_by_default
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_402_eval_reports_global_qc_summary_json_warning_intent_blocker_artifact_signal_not_established

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `intent_blocker:artifact_signal_not_established`
- Summary: warnings: intent_blocker:artifact_signal_not_established
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_403_eval_reports_global_qc_summary_json_warning_intent_blocker_explicit_rebeat_stems_and_arrangement

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `intent_blocker:explicit_rebeat_stems_and_arrangement_review_required`
- Summary: warnings: intent_blocker:explicit_rebeat_stems_and_arrangement_review_required
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_404_eval_reports_global_qc_summary_json_warning_intent_blocker_explicit_user_approval_and_preview_re

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `intent_blocker:explicit_user_approval_and_preview_required`
- Summary: warnings: intent_blocker:explicit_user_approval_and_preview_required
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_405_eval_reports_global_qc_summary_json_warning_intent_blocker_no_safe_vocal_candidate

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `intent_blocker:no_safe_vocal_candidate`
- Summary: warnings: intent_blocker:no_safe_vocal_candidate
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_406_eval_reports_global_qc_summary_json_warning_intent_blocker_stems_not_ready

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `intent_blocker:stems_not_ready`
- Summary: warnings: intent_blocker:stems_not_ready
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_407_eval_reports_global_qc_summary_json_warning_intent_blocker_validated_plugin_mapping_required

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `intent_blocker:validated_plugin_mapping_required`
- Summary: warnings: intent_blocker:validated_plugin_mapping_required
- Recommended next action: run plugin inventory and adapter validation before draft processing

### risk_408_eval_reports_global_qc_summary_json_warning_inventory_file_missing

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `inventory_file_missing`
- Summary: warnings: inventory_file_missing
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_409_eval_reports_global_qc_summary_json_warning_no_accepted_export_source

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `no_accepted_export_source`
- Summary: warnings: no_accepted_export_source
- Recommended next action: complete and accept a reviewed draft source before final export

### risk_410_eval_reports_global_qc_summary_json_warning_no_reference_audio_provided_target_profile_only

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `no_reference_audio_provided_target_profile_only`
- Summary: warnings: no_reference_audio_provided_target_profile_only
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_411_eval_reports_global_qc_summary_json_warning_no_tracks_available_for_role_detection

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `no_tracks_available_for_role_detection`
- Summary: warnings: no_tracks_available_for_role_detection
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_412_eval_reports_global_qc_summary_json_warning_no_validated_plugin_adapters_available

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `no_validated_plugin_adapters_available`
- Summary: warnings: no_validated_plugin_adapters_available
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_413_eval_reports_global_qc_summary_json_warning_no_validated_safe_plugin_adapters

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `no_validated_safe_plugin_adapters`
- Summary: warnings: no_validated_safe_plugin_adapters
- Recommended next action: validate stock/JSFX/plugin adapter mappings before safe draft work

### risk_414_eval_reports_global_qc_summary_json_warning_not_a_live_reaper_bridge

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `not_a_live_reaper_bridge`
- Summary: warnings: not_a_live_reaper_bridge
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_415_eval_reports_global_qc_summary_json_warning_not_safe_to_write_parameters

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `not_safe_to_write_parameters`
- Summary: warnings: not_safe_to_write_parameters
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_416_eval_reports_global_qc_summary_json_warning_pitch_triage_report_only_no_audio

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `pitch_triage_report_only_no_audio`
- Summary: warnings: pitch_triage_report_only_no_audio
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_417_eval_reports_global_qc_summary_json_warning_placement_analysis_report_only

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `placement analysis report-only`
- Summary: warnings: placement analysis report-only
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_418_eval_reports_global_qc_summary_json_warning_project_file_missing_or_not_provided

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `project_file_missing_or_not_provided`
- Summary: warnings: project_file_missing_or_not_provided
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_419_eval_reports_global_qc_summary_json_warning_project_path_empty_report_only_context

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `project_path_empty_report_only_context`
- Summary: warnings: project_path_empty_report_only_context
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_420_eval_reports_global_qc_summary_json_warning_source_mix_not_supplied_report_only

- Severity: `warning`
- Category: `qc`
- Source report: `eval_reports/global_qc_summary.json`
- Code: `source_mix_not_supplied_report_only`
- Summary: warnings: source_mix_not_supplied_report_only
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_421_export_final_render_manifest_json_warning_diagnostic_report_only_mode__no_final_audio_rendered

- Severity: `warning`
- Category: `render`
- Source report: `export/final_render_manifest.json`
- Code: `diagnostic/report-only mode; no final audio rendered`
- Summary: warnings: diagnostic/report-only mode; no final audio rendered
- Recommended next action: produce an accepted render only after delivery gates are ready

### risk_422_eval_reports_rollback_evidence_gate_json_warning_no_applied_stages_declared

- Severity: `warning`
- Category: `rollback`
- Source report: `eval_reports/rollback_evidence_gate.json`
- Code: `no_applied_stages_declared`
- Summary: warnings: no_applied_stages_declared
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_423_eval_reports_rollback_evidence_gate_json_warning_unknown_rollback_entry_rollback_entry_points_to

- Severity: `warning`
- Category: `rollback`
- Source report: `eval_reports/rollback_evidence_gate.json`
- Code: `unknown:rollback_entry:rollback_entry_points_to_global_registry`
- Summary: warnings: unknown:rollback_entry:rollback_entry_points_to_global_registry
- Recommended next action: repair rollback metadata before any applied-stage confidence or delivery

### risk_424_eval_reports_rollback_evidence_gate_json_warning_unknown_rollback_entry_rollback_stage_unknown

- Severity: `warning`
- Category: `rollback`
- Source report: `eval_reports/rollback_evidence_gate.json`
- Code: `unknown:rollback_entry:rollback_stage_unknown`
- Summary: warnings: unknown:rollback_entry:rollback_stage_unknown
- Recommended next action: repair rollback metadata before any applied-stage confidence or delivery

### risk_425_eval_reports_real_project_source_safety_map_json_warning_unknown_tracks_are_not_eligible_for_aut

- Severity: `warning`
- Category: `source`
- Source report: `eval_reports/real_project_source_safety_map.json`
- Code: `unknown_tracks_are_not_eligible_for_automatic_processing`
- Summary: warnings: unknown_tracks_are_not_eligible_for_automatic_processing
- Recommended next action: classify unknown tracks manually or rerun scan with clearer project labels

### risk_426_eval_reports_source_acceptance_gate_json_warning_accepted_final_export_source_not_recorded

- Severity: `warning`
- Category: `source`
- Source report: `eval_reports/source_acceptance_gate.json`
- Code: `accepted_final_export_source_not_recorded`
- Summary: warnings: accepted_final_export_source_not_recorded
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_427_eval_reports_intent_classification_json_review_no_safe_draft_intents

- Severity: `review`
- Category: `intent`
- Source report: `eval_reports/intent_classification.json`
- Code: `no_safe_draft_intents`
- Summary: No safe draft intents are currently available
- Recommended next action: review the source report and choose the safest next manual or dry-run step

### risk_428_eval_reports_real_project_source_safety_map_json_review_unknown_tracks_4

- Severity: `review`
- Category: `source`
- Source report: `eval_reports/real_project_source_safety_map.json`
- Code: `unknown_tracks:4`
- Summary: 4 unknown tracks require review before automation
- Recommended next action: classify unknown tracks manually or rerun scan with clearer project labels

### risk_429_eval_reports_intent_classification_json_info_safe_next_mode_validate_plugin_mappings

- Severity: `info`
- Category: `intent`
- Source report: `eval_reports/intent_classification.json`
- Code: `safe_next_mode:validate_plugin_mappings`
- Summary: Recommended safe next mode is `validate_plugin_mappings`
- Recommended next action: validate_plugin_mappings

## Missing Reports

- none
