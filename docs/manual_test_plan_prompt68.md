# Prompt68 Manual Test Plan

## Scope

Validate final delivery cross-report consistency after render, QC, A/B preview,
approval, rollback, package, and project-state evidence exist. This plan checks
evidence linkage only; it does not approve audio.

## Steps

1. Generate a final export package with `--render`, `--make-ab-preview`, `--qc`,
   and `--zip`.
2. Run final render, final QC, A/B preview, final approval, rollback, and
   deliverable package evidence gates.
3. Run:

```sh
python3 scripts/run_final_delivery_consistency_gate.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

4. Confirm these files exist:

- `automix/eval_reports/final_delivery_consistency_gate.json`
- `automix/eval_reports/final_delivery_consistency_gate.md`
- `automix/review/final_delivery_consistency_manifest_template.json`
- `automix/review/final_delivery_consistency_request.md`

## Expected Pass Conditions

- `ready_for_delivery_consistency` is `true`.
- Final audio path is consistent across render manifest, render evidence, final
  QC metrics, final QC evidence, A/B preview, and approval records.
- A/B preview path is consistent across preview manifest, A/B evidence, final
  approval evidence, and human approval record.
- Approved source and stage match final export state.
- Project state protects original tracks and master and records the selected
  source when one exists.
- Package manifest and package evidence agree on ZIP path and size.
- Package manifest lists the final audio and A/B preview filenames.

## Expected Fail Conditions

- Any required final-delivery evidence report is missing, invalid, or has an
  unexpected schema.
- Supporting render/QC/A-B/approval/package/rollback gates are not ready.
- Final audio path differs across render, QC, A/B, or approval records.
- A/B preview path differs across A/B and approval records.
- Approval source/stage differs from final export state.
- Final audio or preview file is missing from package manifest.
- Package ZIP path or size differs between manifest and package evidence.
