# Premaster Safety Report

## Summary

- Final recommendation: `mix_revision_required`
- Premaster action: `mix_revision_required`
- Selected profile: `skip_premaster`
- Draft required: `False`
- Original master untouched: `true`
- Pitch correction added: `false`
- Master widening added: `false`

## Source Metrics

- integrated_lufs: `0.0`
- true_peak_dbTP: `0.0`
- lra: `0.0`
- crest_factor: `0.0`
- limiter_pressure_risk: `0.0`
- max_ai_artifact_risk: `0.175`
- vocal_forwardness_score: `0.0`
- mono_compatibility_risk: `0.0`

## Chain Plan

- semantic settings: `{"apply": false}`
- plugin chain: `[]`
- controls written: `{}`
- controls skipped: `{}`
- safe_to_apply: `False`
- warnings: `source mix render missing; analysis is report-only, vocal forwardness is weak; prefer mix placement revision over master boost`

## A/B Evaluation

- renders created: `{"difference": false, "loudness_matched": false, "original_mix": false, "premaster_draft": false}`
- loudness results: `{"gain_increase_db": 0.0, "original_lra": 0.0, "original_lufs": 0.0, "original_true_peak_dbTP": 0.0, "premaster_lra": 0.0, "premaster_lufs": 0.0, "premaster_true_peak_dbTP": 0.0}`
- improvement scores: `{"low_end_translation_delta": 0.0, "mix_glue_delta": 0.0, "overall_loudness_control": 0.0, "peak_control_delta": 0.0, "vocal_clarity_delta": 0.0, "vocal_forwardness_delta": 0.0}`
- damage scores: `{"beat_impact_loss": 0.0, "high_fizz_increase": 0.0, "limiter_pumping_score": 0.0, "low_end_loss_db": 0.0, "metallic_artifact_increase": 0.0, "phase_correlation_worsening": 0.0, "reverb_tail_pumping_score": 0.0, "sibilance_splatter_increase": 0.0, "stereo_width_shift": 0.0, "transient_loss": 0.0, "vocal_forwardness_loss": 0.0, "vocal_harshness_increase": 0.0, "vocal_thinness_increase": 0.0}`
- evaluation passed: `False`
- eval warnings: `missing premaster A/B renders`

## Translation Check

- status: `manual_review_required`
- warnings: `phone_speaker_vocal_loss_recommend_mix_revision, low_end_translation_manual_review`

## Iteration History

- iteration 0: `not run`
- iteration 1: `not run`
- iteration 2: `not run`
- iteration 3: `not run`

## Manual Listening Checklist

- Is the premaster only slightly more controlled, not simply louder?
- Did the vocal stay forward without added sibilance?
- Did consonants, air, and transients survive?
- Did kick and bass impact survive?
- Did reverb or delay tails avoid pumping?
- Does mono fold-down keep the vocal and low end intact?
- Does the difference file contain mostly level/control changes, not musical damage?

## Final Recommendation

`mix_revision_required`
