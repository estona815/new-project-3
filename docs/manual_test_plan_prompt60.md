# Prompt 60 Manual Test Plan - Plugin Semantic Validation Gate

## Purpose

Verify that plugin parameter validation reports are audited before any semantic
parameter writes are allowed.

## Command

```sh
python3 scripts/run_plugin_semantic_validation_gate.py \
  --project-name project \
  --output-dir automix
```

Use `--require-ready` when parameter-write readiness must fail closed:

```sh
python3 scripts/run_plugin_semantic_validation_gate.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

## Expected Outputs

- `automix/eval_reports/plugin_semantic_validation_gate.json`
- `automix/eval_reports/plugin_semantic_validation_gate.md`
- `automix/review/plugin_semantic_validation_manifest_template.json`
- `automix/review/plugin_semantic_validation_request.md`

## Pass Conditions

- Missing reports produce `semantic_validation_reports_missing` or
  `validation_report_missing:<plugin>`.
- `validation_unavailable` reports do not become safe.
- Fake success is blocked when `no_fake_success` is absent or no validated
  write-safe controls exist.
- A safe report requires `status=passed`, `safe_for_automix=true`,
  `no_fake_success=true`, and at least one control with `validated=true`,
  `write_allowed=true`, `confidence>=0.85`, and `target_name`.

## Safety Limits

This check does not open REAPER, insert FX, write parameters, render, or save a
project. Availability alone is never semantic write safety.
