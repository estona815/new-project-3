# Prompt 43 Manual Test Plan

Use this plan when REAPER runtime is available. The pilot must remain
recovery-only.

## A. Preconditions

- Missing Prompt 42 blocks applied recovery.
- Failed read-only guard blocks applied recovery.
- Safe-draft readiness false with plugin blockers blocks recovery.
- Prompt 41 missing creates a warning or blocker through Prompt 42 readiness.

## B. Eligibility

- Lead vocal AI stem is eligible for conservative cleanup when plugin mapping is
  validated.
- Full mix is blocked.
- Unknown track is blocked.
- Instrumental bus is blocked.
- Severe source-separated track is blocked or marked stem-required.
- Thin vocal selects `thin_vocal_body_preserve`.

## C. Draft Safety

- Dry-run creates no tracks.
- `--apply-drafts` creates only `_RECOVERY_DRAFT_v01` tracks.
- Original FX unchanged.
- Original media unchanged.
- Original master unchanged.
- Rollback file created for every draft.

## D. Pitch Block

- Pitch stage blocked.
- No pitch plugins inserted.
- No pitch semantic controls written.
- Pitch report says blocked.

## E. Plugin Safety

- Unknown parameters skipped.
- Low-confidence mappings skipped.
- No fixed index writes.
- Commercial plugin not used unless validated.
- Stock/JSFX fallback used only when mapped safely.

## F. Render / Evaluation

- Render plan created.
- If render disabled, evaluation does not pass.
- Missing render fails evaluation.
- Damage metrics can reject recovery.
- Iteration reduces processing rather than intensifying it.

## G. Reports

- Track selection report exists.
- Pitch block report exists.
- Original protection report exists.
- Rollback registry exists.
- Recovery-only pilot report exists.
- Skipped/blocked tracks are visible.

