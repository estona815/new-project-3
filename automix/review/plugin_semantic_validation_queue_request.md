# Plugin Semantic Validation Queue Request

- Project: `project`
- Runtime manifest template: `automix/review/plugin_semantic_validation_runtime_manifest_template.json`
- Queue jobs: `9`
- Blocked jobs: `2`

Run these only in a saved test copy or temporary muted test context. Convert observations into validation reports, then rerun the semantic validation gate.

## Queue

- `semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx` `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx` -> `automix/analysis_reports/plugin_parameter_validation_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_reaper_observed.json`
- `semantic_validation_02_reaverbate_cockos` `ReaVerbate (Cockos)` -> `automix/analysis_reports/plugin_parameter_validation_reaverbate_cockos_reaper_observed.json`
- `semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx` `Vocal Clarity Repair/vocal_air_guard.jsfx` -> `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_air_guard.jsfx_reaper_observed.json`
- `semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx` `Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx` -> `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_reaper_observed.json`
- `semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx` `Vocal Clarity Repair/vocal_output_guard.jsfx` -> `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_output_guard.jsfx_reaper_observed.json`
- `semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx` `Vocal Clarity Repair/vocal_presence_enhancer.jsfx` -> `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_presence_enhancer.jsfx_reaper_observed.json`
- `semantic_validation_07_reacomp_cockos` `ReaComp (Cockos)` -> `automix/analysis_reports/plugin_parameter_validation_reacomp_cockos_rerun_reaper_observed.json`
- `semantic_validation_08_readelay_cockos` `ReaDelay (Cockos)` -> `automix/analysis_reports/plugin_parameter_validation_readelay_cockos_rerun_reaper_observed.json`
- `semantic_validation_09_reaeq_cockos` `ReaEQ (Cockos)` -> `automix/analysis_reports/plugin_parameter_validation_reaeq_cockos_rerun_reaper_observed.json`

## Blocked Jobs

- `OTT (Xfer Records)`: `['availability_decision_missing:OTT (Xfer Records)']`
- `TDR Nova (Tokyo Dawn Labs)`: `['availability_decision_missing:TDR Nova (Tokyo Dawn Labs)']`
