# Final Placement Adapter Validation

This stage validates whether the final vocal-space carving chain can be applied
inside REAPER without guessing plugin parameters.

It is intentionally fail-closed.

## What It Checks

- The final vocal-space chain plan exists.
- The chain plan is draft-only.
- Pitch correction and master-limiter changes are absent.
- Original tracks must remain untouched.
- Every placement category has a detected, validated, safe adapter.
- Every required semantic control is write-safe.
- Disallowed plugins such as AutoTune, MAutoPitch, OTT, Ozone, Decapitator, and
  Valhalla are blocked for this finishing stage.

## Outputs

- `automix/eval_reports/final_placement_adapter_mapping_report.json`
- `automix/eval_reports/final_placement_adapter_mapping_report.md`
- `automix/chain_plans/final_vocal_space_applicator_plan.json`
- `automix/chain_plans/final_vocal_space_applicator_plan.lua`
- `automix/logs/final_placement_adapter_validation_log.json`

## CLI

```sh
python3 scripts/run_final_placement_adapter_validation.py \
  --output-dir automix \
  --chain-plan automix/chain_plans/final_vocal_space_carving_chain_plan.json \
  --write-configured-applicator
```

The configured applicator remains disabled unless both are true:

- `--enable-configured-applicator` is supplied
- the mapping report has `apply_allowed=true`

## REAPER Applicator

Static script:

- `automix/apply_final_vocal_space_placement_draft.lua`

Configured script:

- `automix/apply_final_vocal_space_placement_draft_configured.lua`

The applicator:

- requires exactly one selected accepted recovery vocal draft
- duplicates it as a muted draft
- creates a muted `FINAL VOCAL SPACE BUS`
- inserts only validated plugins from the Lua applicator plan
- writes parameters only by parameter-name lookup
- accepts only normalized 0-1 parameter values
- writes rollback metadata
- does not save, render, or create final delivery

## Current Project Note

If the current project has no accepted recovery source or no validated adapter
mapping, this stage should block. That is a correct safety result, not a failure
of the guard.
