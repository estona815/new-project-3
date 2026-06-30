# Plugin Semantic Validation Queue

- Project: `project`
- Created UTC: `2026-06-05T11:07:59Z`
- Status: `queue_ready_with_blocked_unavailable_decisions`
- Queue jobs: `9`
- Blocked jobs: `2`
- Ready to run REAPER collection: `True`
- Safe to write parameters: `False`

This queue packages REAPER-observed semantic validation jobs. It does not grant write safety.

## Blockers

- `collection_job_blocked:OTT (Xfer Records):availability_decision_missing:OTT (Xfer Records)`
- `collection_job_blocked:TDR Nova (Tokyo Dawn Labs):availability_decision_missing:TDR Nova (Tokyo Dawn Labs)`

## Next Queue Job

- `semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx` `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx` -> `automix/analysis_reports/plugin_parameter_validation_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_reaper_observed.json`

## Queue Jobs

### semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx

- Plugin: `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- Action: `collect_missing_reaper_observed_semantic_report`
- Target report: `automix/analysis_reports/plugin_parameter_validation_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_reaper_observed.json`
- Requires temporary muted test context: `True`
- Disallowed actions: `['do not validate on a production track without a saved test copy or temporary muted test context', "do not write parameters to the user's mix from this queue", 'do not mark a report passed from plugin availability alone', 'do not use fixed parameter indexes unless observed in the target REAPER runtime']`

### semantic_validation_02_reaverbate_cockos

- Plugin: `ReaVerbate (Cockos)`
- Action: `collect_missing_reaper_observed_semantic_report`
- Target report: `automix/analysis_reports/plugin_parameter_validation_reaverbate_cockos_reaper_observed.json`
- Requires temporary muted test context: `True`
- Disallowed actions: `['do not validate on a production track without a saved test copy or temporary muted test context', "do not write parameters to the user's mix from this queue", 'do not mark a report passed from plugin availability alone', 'do not use fixed parameter indexes unless observed in the target REAPER runtime']`

### semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx

- Plugin: `Vocal Clarity Repair/vocal_air_guard.jsfx`
- Action: `collect_missing_reaper_observed_semantic_report`
- Target report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_air_guard.jsfx_reaper_observed.json`
- Requires temporary muted test context: `True`
- Disallowed actions: `['do not validate on a production track without a saved test copy or temporary muted test context', "do not write parameters to the user's mix from this queue", 'do not mark a report passed from plugin availability alone', 'do not use fixed parameter indexes unless observed in the target REAPER runtime']`

### semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx

- Plugin: `Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx`
- Action: `collect_missing_reaper_observed_semantic_report`
- Target report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_reaper_observed.json`
- Requires temporary muted test context: `True`
- Disallowed actions: `['do not validate on a production track without a saved test copy or temporary muted test context', "do not write parameters to the user's mix from this queue", 'do not mark a report passed from plugin availability alone', 'do not use fixed parameter indexes unless observed in the target REAPER runtime']`

### semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx

- Plugin: `Vocal Clarity Repair/vocal_output_guard.jsfx`
- Action: `collect_missing_reaper_observed_semantic_report`
- Target report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_output_guard.jsfx_reaper_observed.json`
- Requires temporary muted test context: `True`
- Disallowed actions: `['do not validate on a production track without a saved test copy or temporary muted test context', "do not write parameters to the user's mix from this queue", 'do not mark a report passed from plugin availability alone', 'do not use fixed parameter indexes unless observed in the target REAPER runtime']`

### semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx

- Plugin: `Vocal Clarity Repair/vocal_presence_enhancer.jsfx`
- Action: `collect_missing_reaper_observed_semantic_report`
- Target report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_presence_enhancer.jsfx_reaper_observed.json`
- Requires temporary muted test context: `True`
- Disallowed actions: `['do not validate on a production track without a saved test copy or temporary muted test context', "do not write parameters to the user's mix from this queue", 'do not mark a report passed from plugin availability alone', 'do not use fixed parameter indexes unless observed in the target REAPER runtime']`

### semantic_validation_07_reacomp_cockos

- Plugin: `ReaComp (Cockos)`
- Action: `rerun_failed_semantic_report_or_keep_read_only`
- Target report: `automix/analysis_reports/plugin_parameter_validation_reacomp_cockos_rerun_reaper_observed.json`
- Requires temporary muted test context: `True`
- Disallowed actions: `['do not validate on a production track without a saved test copy or temporary muted test context', "do not write parameters to the user's mix from this queue", 'do not mark a report passed from plugin availability alone', 'do not use fixed parameter indexes unless observed in the target REAPER runtime']`

### semantic_validation_08_readelay_cockos

- Plugin: `ReaDelay (Cockos)`
- Action: `rerun_failed_semantic_report_or_keep_read_only`
- Target report: `automix/analysis_reports/plugin_parameter_validation_readelay_cockos_rerun_reaper_observed.json`
- Requires temporary muted test context: `True`
- Disallowed actions: `['do not validate on a production track without a saved test copy or temporary muted test context', "do not write parameters to the user's mix from this queue", 'do not mark a report passed from plugin availability alone', 'do not use fixed parameter indexes unless observed in the target REAPER runtime']`

### semantic_validation_09_reaeq_cockos

- Plugin: `ReaEQ (Cockos)`
- Action: `rerun_failed_semantic_report_or_keep_read_only`
- Target report: `automix/analysis_reports/plugin_parameter_validation_reaeq_cockos_rerun_reaper_observed.json`
- Requires temporary muted test context: `True`
- Disallowed actions: `['do not validate on a production track without a saved test copy or temporary muted test context', "do not write parameters to the user's mix from this queue", 'do not mark a report passed from plugin availability alone', 'do not use fixed parameter indexes unless observed in the target REAPER runtime']`


## Blocked Jobs

- `OTT (Xfer Records)`: `['availability_decision_missing:OTT (Xfer Records)']`
- `TDR Nova (Tokyo Dawn Labs)`: `['availability_decision_missing:TDR Nova (Tokyo Dawn Labs)']`
