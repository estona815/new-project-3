# Mix/Master Quality Harness

This harness imports the extracted `reaper-auto-mix-handoff` package as a
planning contract for the current AutoMix workspace.

It does not render audio, open REAPER, approve delivery, or claim reference
matching. It checks whether the handoff package contains the recipe, Lua
scripts, analysis tools, and QC revision contract needed to run a high-quality
mix/master workflow later.

## Command

```sh
python3 scripts/run_mix_master_quality_harness.py \
  --project-name project \
  --output-dir automix \
  --handoff-root "$REAPER_AUTOMIX_HANDOFF_ROOT"
```

## Outputs

- `automix/eval_reports/mix_master_quality_harness.json`
- `automix/eval_reports/mix_master_quality_harness.md`
- `automix/chain_plans/high_quality_mix_master_readiness_plan.json`

## Readiness Meaning

- `ready_for_high_quality_offline_planning`: the ZIP/handoff recipe and scripts
  are complete enough to plan the workflow.
- `ready_for_reaper_dry_run`: the handoff scripts are complete enough to run a
  future dry-run/classification pass.
- `ready_for_applied_mix_or_master_parameter_writes`: current project gates have
  accepted source evidence and semantic plugin validation.
- `ready_for_delivery_claims`: render, final QC, and A/B evidence gates are all
  ready.

If render evidence is missing, that is expected for this harness. It stays a
blocker for delivery claims, not for offline planning.
