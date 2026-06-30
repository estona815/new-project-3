# Reference Matching / Genre Targeting Report

## Summary

- Final recommendation: `target_profile_only_used`
- Target profile: `digicore_hyperpop_hiphop_vocal_forward`
- References used: `0`
- Draft created: `false`
- Original mix untouched: `true`
- Match strategy: `broad feature comparison with safety overrides`

## Reference Safety Note

References were used only for broad tonal, energy, loudness, and mix-balance comparison. The system did not copy melody, lyrics, arrangement, artist identity, or reference audio.

## Current Mix vs Target Profile

- vocal_forwardness: `0.0`
- lead_melody_prominence: `0.0`
- drum_energy: `0.0`
- 808_energy: `0.0`
- low_end_control: `1.0`
- presence_clarity: `0.0`
- harshness: `0.0`
- sibilance: `0.0`
- stereo_width: `0.0`
- mono_compatibility: `1.0`
- loudness: `0.0`
- AI artifact exposure: `0.0`

## Current Mix vs References

- target profile only; no reference audio analyzed

## Safe Adjustment Priorities

- vocal_forward_space
- lead_melody_space
- drum_energy_support
- 808_support
- stereo_safety

## Blocked Adjustments

- none

## Draft Adjustment Plan

- target tracks: ``
- plugin chain: `[]`
- semantic controls written: `none - draft metadata only`
- semantic controls skipped: `unknown plugin parameters are not written`
- routing changes: `none applied in Python workflow`
- warnings: `current mix missing; target profile scan only, current_mix_missing_target_profile_only, target_profile_only_used_no_reference_files`

## A/B Render Files

- current mix: `None`
- reference-match draft: `None`
- loudness matched: `None`
- difference: `None`

## Evaluation Metrics

- match improvement scores: `{"808_translation_delta": 0.0, "drum_energy_delta": 0.0, "lead_melody_prominence_delta": 0.0, "low_end_control_delta": 0.0, "overall_safe_match_delta": 0.0, "phone_translation_delta": 0.0, "stereo_match_delta": 0.0, "vocal_forwardness_delta": 0.0}`
- damage scores: `{"ai_fizz_increase": 0.0, "beat_impact_loss": 0.0, "lead_melody_masking_increase": 0.0, "limiter_pressure_increase": 0.0, "low_end_mud_increase": 0.0, "metallic_artifact_increase": 0.0, "phase_correlation_worsening": 0.0, "sibilance_splatter_increase": 0.0, "stereo_width_shift": 0.0, "vocal_forwardness_loss": 0.0, "vocal_harshness_increase": 0.0}`
- evaluation passed: `False`

## Iteration History

- iteration 0: `not run`
- iteration 1: `not run`
- iteration 2: `not run`
- iteration 3: `not run`

## Manual Listening Checklist

- Does the mix move toward the target without copying the reference?
- Is the vocal still emotionally clear?
- Is the lead melody stronger without masking the vocal?
- Do drums/808 feel stronger without muddying the low-end?
- Did the high-end become fake, fizzy, or metallic?
- Did the vocal become more AI-like?
- Did the stereo image become unstable?
- Is the result better at equal loudness?

## Final Recommendation

`target_profile_only_used`
