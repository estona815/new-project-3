# Prompt79 Manual Test Plan

## Scope

Validate `scripts/run_plugin_semantic_validation_runtime_observation_gate.py`.
This gate checks raw observation JSON files produced by the Prompt78 REAPER Lua
collector. It does not create validation reports, render audio, save a REAPER
project, or grant parameter write safety.

## Preconditions

- `automix/eval_reports/plugin_semantic_validation_runtime_collector_package.json`
  exists.
- The Prompt78 Lua collector has been run in a saved test copy or temporary
  muted test context if you expect observations to be present.
- No automatic parameter writes are allowed.

## Command

```sh
python3 scripts/run_plugin_semantic_validation_runtime_observation_gate.py \
  --project-name project \
  --output-dir automix
```

Strict readiness check:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_observation_gate.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

## Expected Outputs

- `automix/eval_reports/plugin_semantic_validation_runtime_observation_gate.json`
- `automix/eval_reports/plugin_semantic_validation_runtime_observation_gate.md`
- `automix/review/plugin_semantic_validation_runtime_observation_request.md`
- `automix/review/plugin_semantic_validation_runtime_report_authoring_request.md`

## Acceptance

- Missing raw observation files produce `runtime_observation_missing:*`.
- Accepted observations keep `safe_to_write_parameters=false`.
- Accepted observations keep `creates_validation_reports=false`.
- Observations that claim write safety or validation report creation are blocked.
- Passing this gate means manual report authoring may begin; it does not satisfy
  the runtime evidence gate.

## Follow-Up

After accepted raw observations exist, manually author real
`automix-plugin-parameter-validation-report-v1` reports, update the runtime
manifest, then rerun:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_evidence_gate.py \
  --project-name project \
  --output-dir automix
```
