# Prompt77 Manual Test Plan

## Scope

Validate `scripts/run_plugin_availability_operator_decision_package.py`. This
package prepares operator decisions for unavailable plugins without accepting
those decisions or enabling fallback writes.

## Preconditions

- `automix/eval_reports/plugin_availability_resolution_plan.json` exists.
- `automix/eval_reports/plugin_availability_decision_gate.json` may exist and
  usually reports missing operator decisions.
- No automatic parameter writes are allowed.

## Command

```sh
python3 scripts/run_plugin_availability_operator_decision_package.py \
  --project-name project \
  --output-dir automix
```

Strict readiness check:

```sh
python3 scripts/run_plugin_availability_operator_decision_package.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

## Expected Outputs

- `automix/eval_reports/plugin_availability_operator_decision_package.json`
- `automix/eval_reports/plugin_availability_operator_decision_package.md`
- `automix/review/plugin_availability_operator_decision_checklist.md`
- `automix/review/plugin_availability_disable_manifest_candidate.json`

## Acceptance

- Candidate manifest schema is
  `automix-plugin-availability-disable-manifest-candidate-v1`.
- The candidate manifest is not written to
  `automix/review/plugin_availability_disable_manifest.json`.
- `safe_to_write_parameters=false`.
- Fallback candidates still require semantic validation reports.
- `scripts/run_plugin_availability_decision_gate.py` must reject the candidate
  schema if it is passed as the accepted manifest.

## Follow-Up

After explicit operator acknowledgement, write the accepted manifest with schema
`automix-plugin-availability-disable-manifest-v1` and rerun:

```sh
python3 scripts/run_plugin_availability_decision_gate.py \
  --project-name project \
  --output-dir automix
```
