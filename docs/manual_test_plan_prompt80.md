# Manual Test Plan Prompt80

## Scope

Validate that the runtime report authoring package prepares review-only
templates from accepted raw REAPER observations without creating validation
reports or granting parameter write safety.

## Preconditions

- Run `scripts/run_plugin_semantic_validation_runtime_collector_package.py`.
- Run the generated REAPER collector only in a saved test copy or temporary
  muted test context.
- Run `scripts/run_plugin_semantic_validation_runtime_observation_gate.py`.

## Commands

```sh
python3 scripts/run_plugin_semantic_validation_runtime_report_authoring_package.py \
  --project-name project \
  --output-dir automix
```

Use `--require-ready` when the operator expects at least one accepted raw
observation and wants a nonzero exit code otherwise.

## Expected Blocked State

- With no accepted raw observations, status is
  `no_accepted_runtime_observations`.
- `runtime_report_authoring_package_ready=false`.
- `templates_total=0`.
- `safe_to_write_parameters=false`.
- `creates_validation_reports=false`.
- `writes_analysis_reports=false`.

## Expected Ready State

- Accepted raw observations produce templates under
  `automix/review/plugin_semantic_validation_runtime_report_authoring_templates/`.
- Each template has status `authoring_template_not_validation_evidence`.
- `safe_for_automix=false`, `no_fake_success=false`, and all candidate controls
  remain `write_allowed=false`.
- No file is written under `automix/analysis_reports/` by this package.

## Follow-Up

Human-authored `automix-plugin-parameter-validation-report-v1` reports may be
created only after semantic controls, confidence, and safe bounds are reviewed.
Then rerun the runtime evidence gate and semantic validation gate before any
write-safety decision.
