# Vocal Space Carving + Review Package Report

## Summary

- Project: `mesi_1_v37_VOCAL_CLARITY_FINAL`
- Accepted recovery source: `none`
- Fragile source: `False`
- Placement draft created: `False`
- Premaster draft created: `False`
- Final export created: `No`
- Pitch correction blocked: `True`
- Original tracks untouched: `True`
- Original master untouched: `True`
- Review package: `deliverables/mesi_1_v37_vocal_clarity_final_REVIEW_PACKAGE_v02`

## Target Resolution

- lead vocal: ``
- instrumental bus: `V37 INSTRUMENTAL BUS free EQ pocket`
- backing vocals: `['V37 BACKGROUND DOUBLE SUPPORT L/R']`
- melody tracks: `[]`
- send tracks: `['V37 PRINTED VOCAL REVERB SEND', 'V37 PRINTED VOCAL DELAY SEND']`
- missing targets: `['accepted_lead_vocal_recovery_draft', 'no_accepted_recovery_sources', 'plugin_adapter_gate_not_ready_for_placement']`

## Vocal Space Analysis

- vocal forwardness: `0.0`
- main masking bands: `['250-600 Hz low-mid', '1-4 kHz presence', 'post-phrase reverb/delay tails']`
- backing masking: `0.22`
- send tail masking: `0.65`
- AI artifact exposure risk: `0.0`

## Space Carving Strategy

- selected profile: `vocal_forward_space_carve`
- vocal gain: `0.3`
- instrumental ducking: `-0.9`
- presence ducking: `-1.2`
- low-mid ducking: `-0.7`
- backing vocal ducking: `-1.3`
- send ducking: `-1.0`
- M/S cleanup: `mid 0.1 / side 0.06`
- blocked adjustments: `['pitch_correction', 'full_mix_pitch_experiment', 'robotic_autotune', 'stereo_widening_on_vocal', 'heavy_compression', 'ott', 'aggressive_saturation', 'master_limiter_on_original_master', 'final_delivery_export']`

## Plugin Safety

- plugins used: `[]`
- adapter confidence: `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]`
- controls written: `[]`
- controls skipped: `['vocal_gain_db', 'max_vocal_gain_db', 'instrumental_duck_db', 'presence_duck_db', 'low_mid_duck_db', 'sibilance_conflict_duck_db', 'duck_attack_ms', 'duck_release_ms', 'ms_mid_cleanup', 'ms_side_cleanup', 'backing_vocal_duck_db', 'send_duck_db', 'vocal_harshness_guard', 'vocal_sibilance_guard']`
- fallbacks used: `['REAPER utility gain on draft bus only', 'validated ReaEQ/ReaXcomp/TDR Nova-style dynamic EQ adapter', 'validated ReaXcomp sidechain draft adapter', 'validated JS M/S utility adapter', 'validated ReaComp/ReaXcomp sidechain adapter', 'validated ReaComp send-return ducking adapter', 'validated dynamic EQ/de-esser adapter', 'REAPER utility gain on draft bus only']`
- unmapped plugins skipped: `['utility_gain', 'sidechain_dynamic_eq', 'multiband_ducker', 'ms_cleanup', 'sidechain_ducker', 'send_return_ducker', 'harshness_guard', 'output_gain']`

## Draft and Routing

- draft buses/tracks: `[]`
- sidechain sends: `[]`
- routing changes: `[]`
- rollback file: `automix/rollback/final_vocal_space_carving_rollback.json`

## A/B Evaluation

- current mix: ``
- placement draft: ``
- loudness matched: `False`
- difference: `False`
- evaluation status: `False`

## Damage Checks

- beat impact: `0.0`
- low end: `0.0`
- lead melody: `0.0`
- vocal harshness: `0.0`
- AI artifacts: `0.0`
- stereo/phase: `0.0 / 0.0`

## Premaster Draft

- created: `False`
- selected profile: `blocked_until_placement_review`
- loudness: `not rendered`
- true peak: `not rendered`
- status: `manual_review_required`
- warnings: `['premaster A/B render not enabled; no pass']`

## Review Package

- folder: `deliverables/mesi_1_v37_vocal_clarity_final_REVIEW_PACKAGE_v02`
- zip: `deliverables/mesi_1_v37_vocal_clarity_final_REVIEW_PACKAGE_v02.zip`
- included files: `15`

## Manual Listening Checklist

- Is the vocal clearer without just being louder?
- Does the beat still hit?
- Is the 808/bass still solid?
- Is the lead melody still strong?
- Did backing vocals move behind the lead?
- Are reverb/delay tails cleaner?
- Did the vocal become harsh or thin?
- Did AI fizz or metallic tone become more obvious?
- Is the result better at matched loudness?

## Final Recommendation

`do_not_continue_until_review`
