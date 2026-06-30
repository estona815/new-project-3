# Manual Test Plan Prompt 36

Use a saved copy of a REAPER project. Do not test on the only copy of a
session.

## Premaster Analysis

1. Render or provide the current mix print.
2. Run `python3 scripts/run_premaster_safety_workflow.py --source-mix MIX.wav --dry-run`.
3. Confirm `automix/analysis_reports/project_premaster_safety_analysis.json`
   exists.
4. Confirm loudness, tonal, artifact, vocal-preservation, stereo, and
   translation profiles are present.

## Policy Safety

1. A rejected vocal placement status must produce `mix_revision_required`.
2. Weak vocal forwardness must produce `mix_revision_required`.
3. Already limited or already mastered mixes must select
   `already_mastered_safety`.
4. High AI artifact risk must select `safety_only_premaster`.
5. `loud_but_safe_premaster` must downgrade unless risk is low.

## Chain Plan

1. Confirm `automix/chain_plans/project_premaster_chain_plan.json` exists.
2. Confirm `draft_only=true`.
3. Confirm `original_master_must_remain_untouched=true`.
4. Confirm `contains_pitch_correction=false`.
5. Confirm low-confidence semantic controls are skipped rather than guessed.
6. Confirm no chain category adds master widening by default.

## Draft Safety

1. Keep `allow_draft_premaster=false` in the Lua applicator and run it.
2. Confirm no track, FX, routing, master, media, save, or render changes occur.
3. On a project copy, enable only after reviewing `safe_to_apply=true`.
4. Confirm the draft is named `_PREMASTER_DRAFT`.
5. Confirm the original master bus FX count, volume, pan, and media state are
   unchanged.

## A/B Evaluation

1. Render original mix, premaster draft, loudness-matched draft, and difference.
2. Confirm missing renders fail evaluation.
3. Reject if the draft is only louder.
4. Reject if vocal harshness, sibilance, metallic artifacts, high fizz, vocal
   thinness, phase shift, limiter pumping, or reverb-tail pumping increases.
5. Reject if beat impact or low-end weight drops.

## Translation Check

1. Confirm `automix/eval_reports/project_translation_check.json` exists.
2. Check mono fold-down, phone speaker, earbud harshness, and low-end warnings.
3. Treat translation warnings as manual review triggers, not as approval.

## Human Review

Accept only if the premaster is slightly safer or more controlled without
damaging vocal clarity, consonants, air, ambience, low end, transients, stereo
stability, or original texture.
