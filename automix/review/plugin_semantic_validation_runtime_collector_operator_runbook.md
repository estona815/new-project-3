# Plugin Semantic Validation Runtime Collector Operator Runbook

## Preconditions

- Open a saved REAPER test copy or a temporary muted test context.
- Do not run this against a production mix if you are not prepared to undo/remove the temporary probe track.
- Confirm the collector is being used for raw observations only.
- Confirm `reaper_runtime_collector_safety_audit.json` passed before running the Lua collector.
- Keep `safe_to_write_parameters=false` until the semantic validation gate passes.

## Run

Inside REAPER, run:

`automix/reaper_scripts/collect_plugin_semantic_validation_runtime.lua`

## Expected Outputs

- `automix/reaper_scripts/plugin_semantic_validation_runtime_queue.json`
- `automix/reaper_scripts/plugin_semantic_validation_runtime_observations_template.json`
- `automix/eval_reports/reaper_runtime_collector_safety_audit.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_02_reaverbate_cockos_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_07_reacomp_cockos_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_08_readelay_cockos_observation.json`
- `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_09_reaeq_cockos_observation.json`

## Follow-Up

- Review raw observation JSON manually.
- Rerun `scripts/run_reaper_runtime_collector_safety_audit.py --require-passed` after regenerating the collector.
- Write real `automix-plugin-parameter-validation-report-v1` reports only after confirming semantic controls by name.
- Create/update `automix/review/plugin_semantic_validation_runtime_manifest.json` only after the reports exist.
- Rerun the runtime evidence gate, then rerun the semantic validation gate before any parameter write decision.

## Disallowed

- Do not copy raw observation files into `automix/analysis_reports` as passing validation reports.
- Do not infer write safety from plugin insertability.
- Do not hard-code parameter indexes from this collector without semantic review.
