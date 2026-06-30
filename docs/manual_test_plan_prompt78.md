# Prompt78 Manual Test Plan

## Scope

Validate `scripts/run_plugin_semantic_validation_runtime_collector_package.py`.
This package prepares a REAPER Lua raw-observation collector for queued semantic
validation jobs. It does not run REAPER from Python, create passing validation
reports, render audio, save a project, or grant parameter write safety.

## Preconditions

- `automix/eval_reports/plugin_semantic_validation_runtime_collection_package.json`
  exists, or `automix/eval_reports/plugin_semantic_validation_queue.json` exists
  for fallback packaging.
- No automatic parameter writes are allowed.
- REAPER runtime collection must happen only in a saved test copy or temporary
  muted test context.

## Command

```sh
python3 scripts/run_plugin_semantic_validation_runtime_collector_package.py \
  --project-name project \
  --output-dir automix
```

Strict readiness check:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_collector_package.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

## Expected Outputs

- `automix/eval_reports/plugin_semantic_validation_runtime_collector_package.json`
- `automix/eval_reports/plugin_semantic_validation_runtime_collector_package.md`
- `automix/reaper_scripts/collect_plugin_semantic_validation_runtime.lua`
- `automix/reaper_scripts/plugin_semantic_validation_runtime_queue.json`
- `automix/reaper_scripts/plugin_semantic_validation_runtime_observations_template.json`
- `automix/review/plugin_semantic_validation_runtime_collector_operator_runbook.md`

## Acceptance

- `safe_to_write_parameters=false`.
- `creates_validation_reports=false`.
- The Lua collector contains `TrackFX_AddByName`, `TrackFX_GetNumParams`, and
  `TrackFX_GetParamName`.
- The Lua collector does not contain `TrackFX_SetParam` or
  `TrackFX_SetParamNormalized`.
- Raw observations remain under `automix/reaper_scripts/observations/`.

## Follow-Up

After running the Lua collector in REAPER, manually review raw observations,
write real `automix-plugin-parameter-validation-report-v1` reports only when
semantic controls are confirmed, then rerun:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_evidence_gate.py \
  --project-name project \
  --output-dir automix
```
