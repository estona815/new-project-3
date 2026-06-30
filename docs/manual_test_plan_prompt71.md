# Manual Test Plan Prompt71 Plugin Availability Resolution Plan

## Purpose

Verify that unavailable plugins are converted into explicit operator choices:
install, disable for automatic drafts, or keep manual-review only. This report
does not install plugins, open REAPER, write parameters, render, or approve
fallback writes.

## Steps

1. Run the plugin validation action plan.

```sh
python3 scripts/run_plugin_validation_action_plan.py \
  --project-name project \
  --output-dir automix
```

2. Run the availability resolution plan.

```sh
python3 scripts/run_plugin_availability_resolution_plan.py \
  --project-name project \
  --output-dir automix
```

3. Confirm these files exist:

- `automix/eval_reports/plugin_availability_resolution_plan.json`
- `automix/eval_reports/plugin_availability_resolution_plan.md`
- `automix/review/plugin_availability_resolution_request.md`
- `automix/review/plugin_availability_disable_manifest_template.json`

4. Confirm unavailable third-party plugins are recommended for automatic-draft
   disable unless the operator installs and validates them.
5. Confirm fallback candidates are marked validation-required.

## Expected Result

- `safe_to_write_parameters` remains false.
- Unavailable required JSFX/stock plugins stay blockers.
- Optional unavailable third-party plugins require operator acknowledgement
  before they are disabled from automatic drafts.
