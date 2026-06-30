# Manual Test Plan Prompt70 Plugin Validation Action Plan

## Purpose

Verify that plugin availability and semantic validation blockers are converted
into plugin-level next actions. This report does not open REAPER, write
parameters, render, or approve audio.

## Steps

1. Run plugin validation preflight.

```sh
python3 scripts/run_plugin_validation_preflight.py \
  --project-name project \
  --output-dir automix
```

2. Run plugin semantic validation gate.

```sh
python3 scripts/run_plugin_semantic_validation_gate.py \
  --project-name project \
  --output-dir automix
```

3. Run the action plan.

```sh
python3 scripts/run_plugin_validation_action_plan.py \
  --project-name project \
  --output-dir automix
```

4. Confirm `automix/eval_reports/plugin_validation_action_plan.json`, `.md`,
   and `automix/review/plugin_validation_action_request.md` exist.
5. Confirm unavailable plugins are marked install/disable, available plugins
   without reports request REAPER-observed validation, and failed reports stay
   read-only/manual-review.

## Expected Result

- `safe_to_write_parameters` remains false while any blocker plugin action
  remains.
- `next_plugin_action` points to the earliest plugin validation blocker.
- The report states that plugin availability is not semantic write safety.
