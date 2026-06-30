# Prompt72 Manual Test Plan

Prompt72 validates accepted operator decisions for unavailable plugin handling.
It does not install plugins, open REAPER, write parameters, render, or approve
audio.

## Steps

1. Generate upstream plugin reports:

   ```sh
   python3 scripts/run_plugin_validation_action_plan.py \
     --project-name project \
     --output-dir automix

   python3 scripts/run_plugin_availability_resolution_plan.py \
     --project-name project \
     --output-dir automix
   ```

2. Review `automix/review/plugin_availability_disable_manifest_template.json`.
3. If approving disable/manual-review decisions, create
   `automix/review/plugin_availability_disable_manifest.json` with schema
   `automix-plugin-availability-disable-manifest-v1`,
   `operator_acknowledged=true`, and
   `automatic_parameter_writes_allowed=false` for each unavailable plugin.
4. Run:

   ```sh
   python3 scripts/run_plugin_availability_decision_gate.py \
     --project-name project \
     --output-dir automix
   ```

5. Confirm these outputs:

   - `automix/eval_reports/plugin_availability_decision_gate.json`
   - `automix/eval_reports/plugin_availability_decision_gate.md`
   - `automix/review/plugin_availability_decision_request.md`

## Pass Criteria

- The gate blocks if the accepted manifest is missing, invalid, still uses the
  template schema, lacks operator acknowledgement, or allows automatic
  parameter writes for unavailable plugins.
- The gate can become ready when every required unavailable plugin has an
  acknowledged disable/manual-review decision and fallback validation remains
  required.
- `safe_to_write_parameters` remains false.
