# Prompt63 Manual Test Plan - Final Render Evidence Gate

## Scope

Validate that final delivery readiness requires a real primary WAV render, not
only a render manifest or diagnostic/report-only package.

## Checks

1. Run final export packaging on a saved project copy with a user-owned accepted
   source WAV and `--render`.
2. Run:

```sh
python3 scripts/run_final_render_evidence_gate.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

3. Confirm `automix/eval_reports/final_render_evidence_gate.json` reports
   `ready_for_final_qc: true` only when:
   - `automix/export/final_render_manifest.json` exists and is valid;
   - `automix/export/final_export_state.json` exists and is safe;
   - a primary WAV render exists, is readable, nonempty, and non-silent;
   - the primary WAV path differs from the selected accepted source path;
   - hidden limiter and normalization flags are false;
   - the render is not diagnostic/report-only.
4. Rename the primary WAV and confirm the gate blocks.
5. Set `hidden_limiter_added` or `normalization_applied` to true in a copy of
   the manifest and confirm the gate blocks.
6. Run approval export readiness and confirm final render evidence blockers are
   included until this gate is ready.

## Non-Goals

- This gate does not approve audio.
- This gate does not run final QC.
- This gate does not prove the render sounds better than the source.
