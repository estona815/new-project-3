# Manual Test Plan Prompt 31

Use this only on a saved copy of a REAPER project.

## 1. Analyzer Reports

1. Export or locate a user-owned WAV for the target track.
2. Run `python3 automix/analyze_ai_pitch_source.py --input SOURCE.wav --track-name TRACK --output-dir automix`.
3. Confirm these files exist:
   - `automix/analysis_reports/TRACK_source_classification.json`
   - `automix/analysis_reports/TRACK_pitch_analysis.json`
   - `automix/chain_plans/TRACK_pitch_chain_plan.json`
   - `automix/eval_reports/TRACK_pitch_report.md`
4. Confirm `already_mixed_score`, `already_tuned_score`, `full_mix_likelihood`,
   and pitch confidence fields are present.

## 2. Full-Mix Protection

1. Analyze a mastered/full-mix WAV.
2. Confirm the chain plan has `apply=false`.
3. Confirm final recommendation is `full_mix_unsafe`, `stem_required`, or manual
   review.

## 3. Already-Tuned Protection

1. Analyze an obviously already-tuned AI vocal stem.
2. Confirm strong correction is not proposed.
3. Confirm any proposed settings are micro/light only.

## 4. Draft Applicator

1. Keep `allow_draft_pitch_correction=false` and run the Lua script.
2. Confirm no track or FX is created.
3. On a saved copy, set `allow_draft_pitch_correction=true` only after reviewing
   a safe chain plan.
4. Select exactly one original track.
5. Run the Lua script.
6. Confirm the original track is untouched.
7. Confirm `_PITCH_DRAFT` exists and is muted.
8. Confirm unknown plugin parameters were skipped.

## 5. A/B Evaluation

1. Render original and pitch draft.
2. Run analyzer with `--processed`.
3. Review the difference WAV and metrics JSON.
4. Reject correction if the vocal becomes more robotic, metallic, phasey,
   warbly, cloudy, or fake.
