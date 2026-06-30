# Prompt62 Manual Test Plan - A/B Preview Evidence Gate

## Scope

Validate that final approval readiness requires a real, measured,
loudness-matched A/B preview, not only a boolean manifest flag.

## Checks

1. Run the final export packager with `--make-ab-preview` on a saved project copy
   and user-owned WAV sources.
2. Run:

```sh
python3 scripts/run_ab_preview_evidence_gate.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

3. Confirm `automix/eval_reports/ab_preview_evidence_gate.json` reports
   `ready_for_human_ab_review: true` only when:
   - `final_ab_preview_manifest.json` exists;
   - original, final, and preview WAV paths exist and are nonempty;
   - `loudness_match` metrics are present;
   - the final source is linked to `final_render_manifest.json`;
   - the preview has original and final segments.
4. Delete or rename the preview WAV and confirm the gate blocks.
5. Remove `loudness_match` metrics while leaving `loudness_matched: true` and
   confirm the gate blocks unless `--allow-legacy-loudness-flag` is used for a
   legacy review-only audit.
6. Run approval export readiness and confirm A/B evidence blockers are included
   until this gate is ready.

## Non-Goals

- This gate does not approve audio.
- This gate does not replace human matched-loudness listening.
- This gate does not claim the final render is better than the original.
