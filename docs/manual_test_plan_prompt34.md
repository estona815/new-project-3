# Manual Test Plan Prompt 34

Use a saved copy of a REAPER project. Do not test on the only copy of a
session.

## Recovery Analysis

1. Run batch triage with `python3 scripts/run_batch_pitch_triage.py --project SESSION.rpp --dry-run`.
2. Confirm vocal-like tracks produce
   `automix/analysis_reports/{track_name}_vocal_recovery_analysis.json`.
3. Confirm the artifact profile includes metallic harshness, high fizz, watery
   phase, sibilance warble, reverb smear, transient smear, and thinness scores.
4. Confirm the processing profile includes compression limiting, baked reverb,
   stereo width, mono risk, and phase correlation.

## Policy Safety

1. Full-mix or reference tracks must produce `stem_required`.
2. Already compressed vocals must keep `compression_amount=0.0`.
3. Already wet vocals must not add reverb.
4. Phasey vocals must not widen.
5. Thin vocals must use body preservation or minimal cleanup.
6. Low-artifact vocals should skip or use minimal cleanup only.

## Draft Plan

1. Confirm recovery plans target `{track_name}_RECOVERY_DRAFT`.
2. Confirm the chain contains no pitch correction.
3. Confirm unknown or low-confidence semantic controls are skipped.
4. Confirm commercial plugins are not required.
5. Confirm rollback JSON is written under `automix/rollback/`.

## A/B Evaluation

1. Render original, recovered, loudness-matched recovered, and difference files.
2. Confirm missing renders fail evaluation.
3. Reject if the recovered vocal becomes dull, thin, phasey, smeared, lispy,
   less emotional, or more AI-like.
4. Reject if the difference signal contains too much main vocal body.

## Pitch Integration

1. Confirm pitch triage runs after vocal recovery analysis.
2. Confirm failed or unevaluated recovery draft blocks pitch correction.
3. Confirm full mixes block both recovery and pitch unless an explicit
   experiment mode is approved.
