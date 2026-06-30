# Manual Test Plan: Final Placement Adapter Validation

Run this only after `final_vocal_space_carving_chain_plan.json` exists.

## Tests

- Missing chain plan blocks.
- Chain plan with pitch correction blocks.
- Chain plan with master limiter blocks.
- Unvalidated ReaEQ/ReaComp/ReaXcomp adapters block.
- Validated semantic controls are required for every placement category.
- MAutoPitch, AutoTune, OTT, Ozone, Decapitator, Valhalla, and similar plugins
  remain blocked for this stage.
- Configured applicator is disabled unless mapping is safe and explicitly
  enabled.
- REAPER applicator creates only muted draft tracks/buses.
- Original selected track remains unchanged.
- Original master remains unchanged.
- No project save or render is triggered.
- Rollback JSON is written.

## Dry Run

```sh
python3 scripts/run_final_placement_adapter_validation.py \
  --output-dir automix \
  --write-configured-applicator
```

Expected on an unmapped project:

- `apply_allowed=false`
- configured applicator exists but remains disabled
- blocked reasons list unsafe or unvalidated adapter categories
