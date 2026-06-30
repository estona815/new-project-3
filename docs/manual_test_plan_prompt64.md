# Prompt64 Manual Test Plan - Rollback Evidence Gate

## Scope

Validate that final delivery readiness requires explicit rollback evidence, not
only a general safety claim.

## Checks

1. Run or generate the global rollback registry for a saved project copy:

```sh
python3 scripts/run_rollback_evidence_gate.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

2. Confirm `automix/eval_reports/rollback_evidence_gate.json` reports
   `ready_for_delivery_readiness: true` only when:
   - `automix/rollback/global_rollback_registry.json` exists and is valid;
   - `original_tracks_protected` is true;
   - `original_master_protected` is true;
   - `validation.passed` is true;
   - every declared rollback file exists and is nonempty;
   - every entry has `safe_to_rollback: true`.
3. Rename a rollback file and confirm the gate blocks.
4. Set `safe_to_rollback: false` on an entry and confirm the gate blocks.
5. Set `original_tracks_protected` or `original_master_protected` false and
   confirm the gate blocks.
6. Run approval export readiness and confirm rollback evidence blockers are
   included until this gate is ready.

## Non-Goals

- This gate does not approve audio.
- This gate does not run REAPER rollback.
- This gate does not replace final QC, A/B review, or human approval.
