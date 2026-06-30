# Plugin Semantic Validation Collection Plan

- Project: `project`
- Created UTC: `2026-06-05T11:07:55Z`
- Status: `availability_decisions_required_before_full_collection`
- Open jobs: `11`
- Collectable in REAPER: `9`
- Decision-blocked jobs: `2`
- Safe to write parameters: `False`

This report sequences REAPER-observed semantic validation collection. It does not grant write safety.

## Blockers

- `availability_decision_missing:OTT (Xfer Records)`
- `availability_decision_missing:TDR Nova (Tokyo Dawn Labs)`

## Next Job

- `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`: `collect_missing_reaper_observed_semantic_report` -> `automix/analysis_reports/plugin_parameter_validation_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_reaper_observed.json`

## Jobs

### OTT (Xfer Records)

- Action: `operator_availability_decision_required`
- Collectable in REAPER: `False`
- Target report: `automix/analysis_reports/plugin_parameter_validation_ott_xfer_records_after_install_reaper_observed.json`
- Source blockers: `['validation_report_missing:OTT (Xfer Records)']`
- Blockers: `['availability_decision_missing:OTT (Xfer Records)']`

### TDR Nova (Tokyo Dawn Labs)

- Action: `operator_availability_decision_required`
- Collectable in REAPER: `False`
- Target report: `automix/analysis_reports/plugin_parameter_validation_tdr_nova_tokyo_dawn_labs_after_install_reaper_observed.json`
- Source blockers: `['validation_report_missing:TDR Nova (Tokyo Dawn Labs)']`
- Blockers: `['availability_decision_missing:TDR Nova (Tokyo Dawn Labs)']`

### Codex Vocal/vocal_ai_artifact_split_tamer.jsfx

- Action: `collect_missing_reaper_observed_semantic_report`
- Collectable in REAPER: `True`
- Target report: `automix/analysis_reports/plugin_parameter_validation_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_reaper_observed.json`
- Source blockers: `['validation_report_missing:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx']`
- Blockers: `[]`

### ReaVerbate (Cockos)

- Action: `collect_missing_reaper_observed_semantic_report`
- Collectable in REAPER: `True`
- Target report: `automix/analysis_reports/plugin_parameter_validation_reaverbate_cockos_reaper_observed.json`
- Source blockers: `['validation_report_missing:ReaVerbate (Cockos)']`
- Blockers: `[]`

### Vocal Clarity Repair/vocal_air_guard.jsfx

- Action: `collect_missing_reaper_observed_semantic_report`
- Collectable in REAPER: `True`
- Target report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_air_guard.jsfx_reaper_observed.json`
- Source blockers: `['validation_report_missing:Vocal Clarity Repair/vocal_air_guard.jsfx']`
- Blockers: `[]`

### Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx

- Action: `collect_missing_reaper_observed_semantic_report`
- Collectable in REAPER: `True`
- Target report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_reaper_observed.json`
- Source blockers: `['validation_report_missing:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx']`
- Blockers: `[]`

### Vocal Clarity Repair/vocal_output_guard.jsfx

- Action: `collect_missing_reaper_observed_semantic_report`
- Collectable in REAPER: `True`
- Target report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_output_guard.jsfx_reaper_observed.json`
- Source blockers: `['validation_report_missing:Vocal Clarity Repair/vocal_output_guard.jsfx']`
- Blockers: `[]`

### Vocal Clarity Repair/vocal_presence_enhancer.jsfx

- Action: `collect_missing_reaper_observed_semantic_report`
- Collectable in REAPER: `True`
- Target report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_presence_enhancer.jsfx_reaper_observed.json`
- Source blockers: `['validation_report_missing:Vocal Clarity Repair/vocal_presence_enhancer.jsfx']`
- Blockers: `[]`

### ReaComp (Cockos)

- Action: `rerun_failed_semantic_report_or_keep_read_only`
- Collectable in REAPER: `True`
- Target report: `automix/analysis_reports/plugin_parameter_validation_reacomp_cockos_rerun_reaper_observed.json`
- Source blockers: `['ReaComp (Cockos):validation_report_has_no_write_safe_controls', 'ReaComp (Cockos):validation_report_not_passed:validation_unavailable', 'ReaComp (Cockos):validation_report_not_safe_for_automix', 'no_passed_semantic_validation_report:ReaComp (Cockos)']`
- Blockers: `[]`

### ReaDelay (Cockos)

- Action: `rerun_failed_semantic_report_or_keep_read_only`
- Collectable in REAPER: `True`
- Target report: `automix/analysis_reports/plugin_parameter_validation_readelay_cockos_rerun_reaper_observed.json`
- Source blockers: `['ReaDelay (Cockos):validation_report_has_no_write_safe_controls', 'ReaDelay (Cockos):validation_report_not_passed:validation_unavailable', 'ReaDelay (Cockos):validation_report_not_safe_for_automix', 'no_passed_semantic_validation_report:ReaDelay (Cockos)']`
- Blockers: `[]`

### ReaEQ (Cockos)

- Action: `rerun_failed_semantic_report_or_keep_read_only`
- Collectable in REAPER: `True`
- Target report: `automix/analysis_reports/plugin_parameter_validation_reaeq_cockos_rerun_reaper_observed.json`
- Source blockers: `['ReaEQ (Cockos):validation_report_has_no_write_safe_controls', 'ReaEQ (Cockos):validation_report_not_passed:validation_unavailable', 'ReaEQ (Cockos):validation_report_not_safe_for_automix', 'no_passed_semantic_validation_report:ReaEQ (Cockos)']`
- Blockers: `[]`
