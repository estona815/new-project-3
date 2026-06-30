# Prompt76 Manual Test Plan

## Scope

Validate `scripts/run_plugin_semantic_validation_runtime_collection_package.py`.
This package prepares REAPER runtime collection materials for Prompt74 queue jobs
without opening REAPER, inserting FX, writing parameters, rendering, or approving
audio.

## Preconditions

- `automix/eval_reports/plugin_semantic_validation_queue.json` exists.
- Queue jobs must be intended for a saved test copy or temporary muted REAPER
  test context.
- No generated template should be treated as passing evidence.

## Command

```sh
python3 scripts/run_plugin_semantic_validation_runtime_collection_package.py \
  --project-name project \
  --output-dir automix
```

Strict package readiness check:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_collection_package.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

## Expected Outputs

- `automix/eval_reports/plugin_semantic_validation_runtime_collection_package.json`
- `automix/eval_reports/plugin_semantic_validation_runtime_collection_package.md`
- `automix/review/plugin_semantic_validation_runtime_collection_checklist.md`
- `automix/review/plugin_semantic_validation_runtime_manifest_candidate.json`
- `automix/review/plugin_semantic_validation_runtime_report_templates/*.json`

## Acceptance

- `safe_to_write_parameters=false`.
- Report templates use schema
  `automix-plugin-parameter-validation-report-template-v1`.
- Templates are written under `automix/review/`, not
  `automix/analysis_reports/`.
- The package is ready only when queue jobs exist and the queue report is valid.
- Blocked unavailable-plugin decisions remain warnings or carried queue context,
  not proof that those plugins were validated.

## Follow-Up

After collecting real REAPER observations:

```sh
python3 scripts/run_plugin_semantic_validation_gate.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_semantic_validation_runtime_evidence_gate.py \
  --project-name project \
  --output-dir automix
```
