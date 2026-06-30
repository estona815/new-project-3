# Plugin Semantic Validation Runtime Collector Package

- Project: `project`
- Created UTC: `2026-06-05T12:24:11Z`
- Status: `runtime_collector_package_ready`
- Ready for REAPER runtime collection: `True`
- Collector jobs: `9`
- Safe to write parameters: `False`
- Creates validation reports: `False`
- Lua collector: `automix/reaper_scripts/collect_plugin_semantic_validation_runtime.lua`
- Queue payload: `automix/reaper_scripts/plugin_semantic_validation_runtime_queue.json`
- Required safety audit: `automix/eval_reports/reaper_runtime_collector_safety_audit.json`

This collector writes raw observations only. It does not approve plugin write safety.

## Blockers

- none

## Warnings

- `blocked_queue_jobs_remain:2`

## Collector Jobs

### semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx

- Plugin: `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_observation.json`
- Target validation report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_validation_report_template.json`

### semantic_validation_02_reaverbate_cockos

- Plugin: `ReaVerbate (Cockos)`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_02_reaverbate_cockos_observation.json`
- Target validation report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_reaverbate_cockos_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_02_reaverbate_cockos_validation_report_template.json`

### semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx

- Plugin: `Vocal Clarity Repair/vocal_air_guard.jsfx`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx_observation.json`
- Target validation report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_air_guard.jsfx_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx_validation_report_template.json`

### semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx

- Plugin: `Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_observation.json`
- Target validation report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_validation_report_template.json`

### semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx

- Plugin: `Vocal Clarity Repair/vocal_output_guard.jsfx`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx_observation.json`
- Target validation report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_output_guard.jsfx_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx_validation_report_template.json`

### semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx

- Plugin: `Vocal Clarity Repair/vocal_presence_enhancer.jsfx`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx_observation.json`
- Target validation report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_presence_enhancer.jsfx_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx_validation_report_template.json`

### semantic_validation_07_reacomp_cockos

- Plugin: `ReaComp (Cockos)`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_07_reacomp_cockos_observation.json`
- Target validation report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_reacomp_cockos_rerun_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_07_reacomp_cockos_validation_report_template.json`

### semantic_validation_08_readelay_cockos

- Plugin: `ReaDelay (Cockos)`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_08_readelay_cockos_observation.json`
- Target validation report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_readelay_cockos_rerun_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_08_readelay_cockos_validation_report_template.json`

### semantic_validation_09_reaeq_cockos

- Plugin: `ReaEQ (Cockos)`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_09_reaeq_cockos_observation.json`
- Target validation report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_reaeq_cockos_rerun_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_09_reaeq_cockos_validation_report_template.json`
