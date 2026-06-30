# Compact Mix/Master Context

The compact context keeps ordinary mix/master turns short. Instead of pasting or
re-reading long operating prompts, build a small state file from the existing
reports and use the compact run card.

## Command

```sh
python3 scripts/run_compact_mix_context.py --project-name project
```

Outputs:

- `work/state/RUN_CONTEXT.compact.json`
- `work/state/RUN_CONTEXT.compact.md`

## What It Captures

- Current delivery and QC state from `automix/eval_reports/current_state_summary.json`.
- Mix/master readiness from `automix/eval_reports/mix_master_quality_harness.json`.
- Stem and reference counts from `work/assets/asset_manifest.json`.
- Plugin trace highlights from `work/traces/plugin_trace.json`.
- QC headline from `work/qc/qc_report.json` or final QC metrics when present.
- Top blockers and next evidence actions.

## Token Policy

For normal revisions, read only:

1. `work/state/RUN_CONTEXT.compact.json`
2. `prompts/mix_master_compact_run_card.md`
3. `REAPER_REFERENCE_MIX_PIPELINE.md`

Open the longer runbooks only for the gate being touched: source acceptance,
plugin semantic validation, final render evidence, final QC, A/B review,
approval/export, or package consistency.

## Quality Policy

The compact file is a state summary, not evidence by itself. Delivery claims
still require render files, plugin traces, QC files, A/B evidence, approval
evidence, and final package consistency. When those files are missing, the
compact context must keep the status at `review_copy` or `blocked`.

