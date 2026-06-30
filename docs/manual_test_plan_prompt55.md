# Manual Test Plan: Prompt55 Plugin Validation Preflight

## Purpose

Confirm local plugin availability without claiming semantic parameter write
safety.

## Static Test

```sh
python3 -m pytest tests/test_prompt55_plugin_validation_preflight.py
```

Expected:

- local stock/plugin/JSFX files are reported as availability evidence;
- `safe_to_write_parameters` remains `false` when semantic validation is not
  proven;
- `--require-safe-write` returns non-zero while write safety is unproven.

## Current Project Preflight

```sh
python3 scripts/run_plugin_validation_preflight.py \
  --project-name project \
  --output-dir automix
```

Review:

- `automix/eval_reports/plugin_validation_preflight.json`
- `automix/eval_reports/plugin_validation_preflight.md`

Acceptance for safe draft automation is not plugin file presence. It requires
validated semantic controls, safe bounds, and readiness evidence that keeps
`safe_to_write_parameters=true`.
