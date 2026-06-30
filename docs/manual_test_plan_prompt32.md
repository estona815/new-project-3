# Manual Test Plan Prompt 32

Use a saved copy of any REAPER project. Do not test on the only copy of a
session.

## Safety Gate

1. Run `python3 scripts/run_pitch_safety_workflow.py --input SOURCE.wav --track "Lead Vocal" --dry-run`.
2. Confirm a chain plan and human report are created.
3. Confirm high full-mix likelihood produces `full_mix_unsafe`.
4. Confirm low pitch confidence produces `apply=false`.
5. Confirm missing adapter mapping produces `plugin_mapping_required`.

## Draft Guard

1. Keep `allow_draft_pitch_correction=false` in the Lua applicator and run it.
2. Confirm no track or FX is created.
3. On a project copy, enable the flag only after reviewing an `apply=true` plan.
4. Confirm the original track is unchanged.
5. Confirm the draft track is named `_PITCH_DRAFT` and muted.
6. Confirm rollback metadata exists under `automix/rollback/`.

## Evaluation

1. Run the analyzer without a processed render.
2. Confirm `evaluation_passed=false`.
3. Render a draft and run with `--processed`.
4. Confirm loudness-matched and difference files are created.
5. Confirm any damage warning rejects or requires manual review.

## Human Review

Reject the pitch draft if the vocal becomes more robotic, metallic, phasey,
fake, thin, smeared, or AI-like, even if pitch appears more locked.
