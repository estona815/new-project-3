# Prompt74 Manual Test Plan

Prompt74 packages collectable REAPER-observed semantic validation jobs into a
runtime queue. It does not open REAPER, insert FX, write parameters, render, or
approve audio.

## Steps

1. Generate the upstream plugin validation sequence:

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

   python3 scripts/run_plugin_availability_resolution_plan.py \
     --project-name project \
     --output-dir automix

   python3 scripts/run_plugin_availability_decision_gate.py \
     --project-name project \
     --output-dir automix

   python3 scripts/run_plugin_semantic_validation_collection_plan.py \
     --project-name project \
     --output-dir automix
   ```

2. Package the queue:

   ```sh
   python3 scripts/run_plugin_semantic_validation_queue.py \
     --project-name project \
     --output-dir automix
   ```

3. Confirm these outputs:

   - `automix/eval_reports/plugin_semantic_validation_queue.json`
   - `automix/eval_reports/plugin_semantic_validation_queue.md`
   - `automix/review/plugin_semantic_validation_queue_request.md`
   - `automix/review/plugin_semantic_validation_runtime_manifest_template.json`

## Pass Criteria

- Collectable jobs are sorted into a runtime queue with target report paths.
- Unavailable plugin decisions remain in blocked jobs until operator decisions
  are accepted.
- Queue jobs require a saved test copy or temporary muted test context.
- `safe_to_write_parameters` remains false.
