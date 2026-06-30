# Plugin Semantic Validation Runtime Evidence Request

- Project: `project`
- Runtime manifest: `automix/review/plugin_semantic_validation_runtime_manifest.json`
- Runtime manifest schema required: `automix-plugin-semantic-validation-runtime-manifest-v1`
- Queue jobs: `9`
- Runtime evidence ready: `False`
- Safe to write parameters: `False`

Fill the runtime manifest only after the queued jobs ran in a saved test copy or temporary muted test context. Then rerun this gate and rerun the semantic validation gate.

## Required Manifest Fields Per Job

- `operator_acknowledged=true`
- `runtime_observed=true`
- `report_written=true`
- `report_reaudited_by_semantic_gate=true`

## Open Job Evidence

- `semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx` `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx` -> `automix/analysis_reports/plugin_parameter_validation_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_reaper_observed.json` blockers=`['runtime_manifest_job_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx', 'runtime_validation_report_missing:semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx']`
- `semantic_validation_02_reaverbate_cockos` `ReaVerbate (Cockos)` -> `automix/analysis_reports/plugin_parameter_validation_reaverbate_cockos_reaper_observed.json` blockers=`['runtime_manifest_job_missing:semantic_validation_02_reaverbate_cockos', 'runtime_validation_report_missing:semantic_validation_02_reaverbate_cockos']`
- `semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx` `Vocal Clarity Repair/vocal_air_guard.jsfx` -> `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_air_guard.jsfx_reaper_observed.json` blockers=`['runtime_manifest_job_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx', 'runtime_validation_report_missing:semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx']`
- `semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx` `Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx` -> `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_reaper_observed.json` blockers=`['runtime_manifest_job_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx', 'runtime_validation_report_missing:semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx']`
- `semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx` `Vocal Clarity Repair/vocal_output_guard.jsfx` -> `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_output_guard.jsfx_reaper_observed.json` blockers=`['runtime_manifest_job_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx', 'runtime_validation_report_missing:semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx']`
- `semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx` `Vocal Clarity Repair/vocal_presence_enhancer.jsfx` -> `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_presence_enhancer.jsfx_reaper_observed.json` blockers=`['runtime_manifest_job_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx', 'runtime_validation_report_missing:semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx']`
- `semantic_validation_07_reacomp_cockos` `ReaComp (Cockos)` -> `automix/analysis_reports/plugin_parameter_validation_reacomp_cockos_rerun_reaper_observed.json` blockers=`['runtime_manifest_job_missing:semantic_validation_07_reacomp_cockos', 'runtime_validation_report_missing:semantic_validation_07_reacomp_cockos']`
- `semantic_validation_08_readelay_cockos` `ReaDelay (Cockos)` -> `automix/analysis_reports/plugin_parameter_validation_readelay_cockos_rerun_reaper_observed.json` blockers=`['runtime_manifest_job_missing:semantic_validation_08_readelay_cockos', 'runtime_validation_report_missing:semantic_validation_08_readelay_cockos']`
- `semantic_validation_09_reaeq_cockos` `ReaEQ (Cockos)` -> `automix/analysis_reports/plugin_parameter_validation_reaeq_cockos_rerun_reaper_observed.json` blockers=`['runtime_manifest_job_missing:semantic_validation_09_reaeq_cockos', 'runtime_validation_report_missing:semantic_validation_09_reaeq_cockos']`

## Blocked Queue Jobs

- `OTT (Xfer Records)`: `['availability_decision_missing:OTT (Xfer Records)']`
- `TDR Nova (Tokyo Dawn Labs)`: `['availability_decision_missing:TDR Nova (Tokyo Dawn Labs)']`
