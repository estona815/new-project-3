# Prompt73 Manual Test Plan

Prompt73 creates a REAPER-observed semantic validation collection plan. It does
not open REAPER, insert FX, write parameters, render, or approve audio.

## Steps

1. Generate upstream plugin validation reports:

   ```sh
   python3 scripts/run_plugin_validation_preflight.py \
     --project-name project \
     --output-dir automix

   python3 scripts/run_plugin_semantic_validation_gate.py \
     --project-name project \
     --output-dir automix

   python3 scripts/run_plugin_validation_action_plan.py \
     --project-name project \
     --output-dir automix
   ```

2. Generate the collection plan:

   ```sh
   python3 scripts/run_plugin_semantic_validation_collection_plan.py \
     --project-name project \
     --output-dir automix
   ```

3. Confirm these outputs:

   - `automix/eval_reports/plugin_semantic_validation_collection_plan.json`
   - `automix/eval_reports/plugin_semantic_validation_collection_plan.md`
   - `automix/review/plugin_semantic_validation_collection_request.md`
   - `automix/review/plugin_semantic_validation_collection_manifest_template.json`

## Pass Criteria

- Missing semantic reports become collectable REAPER-observed validation jobs.
- Failed or validation-unavailable reports become rerun-or-read-only jobs.
- Unavailable plugins remain blocked by operator availability decisions unless
  an accepted disable/manual-review decision exists.
- `safe_to_write_parameters` remains false.
