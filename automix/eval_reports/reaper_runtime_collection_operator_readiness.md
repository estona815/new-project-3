# REAPER Runtime Collection Operator Readiness

- Project: `project`
- Created UTC: `2026-06-05T12:24:11Z`
- Status: `partial_operator_runtime_collection_ready`
- Partial collection ready: `True`
- Complete collection ready: `False`
- Safe to run Lua collector: `True`
- Safe to write parameters: `False`
- Collector jobs: `9`
- Blocked queue jobs: `2`

This gate is pre-run only. It does not open REAPER or execute the collector.

## Blockers

- none

## Warnings

- `availability_decisions_not_ready_for_complete_collection`
- `availability_operator_decisions_missing:2`
- `complete_operator_collection_blocked_by_queue_jobs:2`

## Review Items

- `availability_decision_missing:OTT (Xfer Records)`
- `availability_decision_missing:TDR Nova (Tokyo Dawn Labs)`
- `blocked_queue_job:OTT (Xfer Records)`
- `blocked_queue_job:TDR Nova (Tokyo Dawn Labs)`

## Required Paths

- `lua_collector_script_path`: `automix/reaper_scripts/collect_plugin_semantic_validation_runtime.lua`
- `operator_runbook_path`: `automix/review/plugin_semantic_validation_runtime_collector_operator_runbook.md`
- `safety_audit_path`: `automix/eval_reports/reaper_runtime_collector_safety_audit.json`
- `local_device_qc_path`: `automix/eval_reports/local_device_qc.json`

## Expected Observation Outputs

- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_02_reaverbate_cockos_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_07_reacomp_cockos_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_08_readelay_cockos_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_09_reaeq_cockos_observation.json`

## Next Operator Actions

- Open a saved REAPER test copy or a temporary muted test context before running the Lua collector.
- Run the Lua collector only for raw plugin parameter observations.
- Do not promote raw observations to validation reports without manual semantic review.
- Resolve missing availability decisions before claiming complete runtime collection readiness.

## Limits

- This gate does not open REAPER, run the collector, write parameters, render, save, or approve delivery.
- Partial readiness means collectable jobs can be observed; it does not resolve unavailable plugin decisions.
- Raw observations are not plugin semantic validation reports.
- A passing gate does not prove audio quality or delivery readiness.
