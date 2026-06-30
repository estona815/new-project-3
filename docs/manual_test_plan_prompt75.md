# Prompt75 Manual Test Plan

## Scope

Validate `scripts/run_plugin_semantic_validation_runtime_evidence_gate.py` after
Prompt74 has generated a semantic validation queue.

## Preconditions

- `automix/eval_reports/plugin_semantic_validation_queue.json` exists.
- Queued jobs were run only in a saved test copy or temporary muted REAPER test
  context.
- Runtime observations were converted into
  `automix/analysis_reports/plugin_parameter_validation_*.json` reports.
- Operator evidence was recorded in
  `automix/review/plugin_semantic_validation_runtime_manifest.json` with schema
  `automix-plugin-semantic-validation-runtime-manifest-v1`.

## Commands

```sh
python3 scripts/run_plugin_semantic_validation_runtime_evidence_gate.py \
  --project-name project \
  --output-dir automix
```

Strict check:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_evidence_gate.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

## Expected Results

- Missing runtime manifest returns `status=runtime_manifest_missing`.
- A template manifest is blocked as
  `plugin_semantic_validation_runtime_manifest_is_template`.
- Every queued job requires operator acknowledgement, runtime observation,
  report-written status, semantic gate reaudit status, and a passing validation
  report.
- `safe_to_write_parameters` remains `false`.
- `ready_for_semantic_gate_rerun=true` only when all queued reports are accepted.

## Follow-Up

After this gate is ready, rerun:

```sh
python3 scripts/run_plugin_semantic_validation_gate.py \
  --project-name project \
  --output-dir automix
```
