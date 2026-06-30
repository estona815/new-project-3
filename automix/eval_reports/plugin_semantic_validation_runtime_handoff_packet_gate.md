# Plugin Semantic Validation Runtime Handoff Packet Gate

- Project: `project`
- Created UTC: `2026-06-05T12:24:39Z`
- Status: `partial_operator_runtime_handoff_packet_ready`
- Passed: `True`
- Packet ready: `True`
- Complete packet ready: `False`
- Safe to run Lua collector: `True`
- Safe to write parameters: `False`

This report checks operator handoff packet completeness only. It does not grant parameter write safety.

## Counts

- `queue_jobs_total`: `9`
- `collection_jobs_total`: `9`
- `collector_jobs_total`: `9`
- `handoff_jobs_ready_total`: `9`
- `blocked_queue_jobs_total`: `2`
- `availability_missing_decisions_total`: `2`
- `required_operator_artifacts_total`: `6`

## Blockers

- none

## Warnings

- `availability_operator_decisions_missing:2`
- `blocked_unavailable_queue_jobs_remain:2`

## Required Operator Artifacts

- `lua_collector_script_path` exists `True` valid `None` schema `` blockers `[]`
- `operator_runbook_path` exists `True` valid `None` schema `` blockers `[]`
- `queue_payload_path` exists `True` valid `True` schema `automix-plugin-semantic-validation-reaper-runtime-queue-v1` blockers `[]`
- `observation_template_path` exists `True` valid `True` schema `automix-plugin-semantic-validation-runtime-observation-template-v1` blockers `[]`
- `manifest_candidate_path` exists `True` valid `True` schema `automix-plugin-semantic-validation-runtime-manifest-v1` blockers `[]`
- `checklist_path` exists `True` valid `None` schema `` blockers `[]`

## Jobs

### semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx

- Plugin: `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- Status: `handoff_job_ready`
- Target report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_reaper_observed.json`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_observation.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_validation_report_template.json`
- Blockers: `[]`

### semantic_validation_02_reaverbate_cockos

- Plugin: `ReaVerbate (Cockos)`
- Status: `handoff_job_ready`
- Target report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_reaverbate_cockos_reaper_observed.json`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_02_reaverbate_cockos_observation.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_02_reaverbate_cockos_validation_report_template.json`
- Blockers: `[]`

### semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx

- Plugin: `Vocal Clarity Repair/vocal_air_guard.jsfx`
- Status: `handoff_job_ready`
- Target report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_air_guard.jsfx_reaper_observed.json`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx_observation.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx_validation_report_template.json`
- Blockers: `[]`

### semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx

- Plugin: `Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx`
- Status: `handoff_job_ready`
- Target report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_reaper_observed.json`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_observation.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_validation_report_template.json`
- Blockers: `[]`

### semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx

- Plugin: `Vocal Clarity Repair/vocal_output_guard.jsfx`
- Status: `handoff_job_ready`
- Target report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_output_guard.jsfx_reaper_observed.json`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx_observation.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx_validation_report_template.json`
- Blockers: `[]`

### semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx

- Plugin: `Vocal Clarity Repair/vocal_presence_enhancer.jsfx`
- Status: `handoff_job_ready`
- Target report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_presence_enhancer.jsfx_reaper_observed.json`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx_observation.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx_validation_report_template.json`
- Blockers: `[]`

### semantic_validation_07_reacomp_cockos

- Plugin: `ReaComp (Cockos)`
- Status: `handoff_job_ready`
- Target report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_reacomp_cockos_rerun_reaper_observed.json`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_07_reacomp_cockos_observation.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_07_reacomp_cockos_validation_report_template.json`
- Blockers: `[]`

### semantic_validation_08_readelay_cockos

- Plugin: `ReaDelay (Cockos)`
- Status: `handoff_job_ready`
- Target report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_readelay_cockos_rerun_reaper_observed.json`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_08_readelay_cockos_observation.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_08_readelay_cockos_validation_report_template.json`
- Blockers: `[]`

### semantic_validation_09_reaeq_cockos

- Plugin: `ReaEQ (Cockos)`
- Status: `handoff_job_ready`
- Target report: `/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_reaeq_cockos_rerun_reaper_observed.json`
- Raw observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_09_reaeq_cockos_observation.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_09_reaeq_cockos_validation_report_template.json`
- Blockers: `[]`

## Review Items

- `availability_decision_missing:OTT (Xfer Records)`
- `availability_decision_missing:TDR Nova (Tokyo Dawn Labs)`
- `blocked_queue_job:OTT (Xfer Records)`
- `blocked_queue_job:TDR Nova (Tokyo Dawn Labs)`

## Limits

- This gate does not open REAPER, execute Lua, write parameters, render, save, or approve delivery.
- Report templates and manifest candidates are not runtime evidence.
- Raw observations must be manually converted into validation reports and rerun through runtime and semantic evidence gates.
- A partial-ready packet may still have blocked unavailable plugin decisions.
