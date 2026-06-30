# Recovery-Only Pilot Report

## Summary

- Project: `mesi_1_v37_VOCAL_CLARITY_FINAL`
- Mode: `recovery_only_pilot`
- Recovery drafts created: `0`
- Pitch correction blocked: `True`
- Original tracks untouched: `True`
- Original master untouched: `True`
- Render enabled: `False`
- Evaluation status: `render_required`

## Preconditions

- Prompt 41 validation: `see Prompt42 readiness`
- Prompt 42 scan-only report: `True`
- Read-only guard: `True`
- Safe-draft readiness: `False`
- Recovery-only precondition blockers: `validated_plugin_mapping_required`

## Track Selection

| Track | Role | Source Type | Risk | Recovery Action | Draft Created | Blockers | Warnings |
|---|---|---|---|---|---:|---|---|
| `SOURCE full mix reference muted` | `full_mix_reference` | `full_mix` | `blocked` |  | `False` | `FULL_MIX_UNSAFE_FOR_VOCAL_RECOVERY, PLUGIN_MAPPING_UNSAFE, ROLE_NOT_RECOVERY_ELIGIBLE, VOCAL_LIKELIHOOD_LOW, validated_plugin_mapping_required` | `audio_read_failed:source_full_mix_reference.wav:Error, full mix source is unsafe for vocal-forward placement automation, full mix unsafe for vocal recovery` |
| `V37 INSTRUMENTAL BUS free EQ pocket` | `instrumental_bus` | `full_mix` | `blocked` |  | `False` | `FULL_MIX_UNSAFE_FOR_VOCAL_RECOVERY, PLUGIN_MAPPING_UNSAFE, ROLE_NOT_RECOVERY_ELIGIBLE, VOCAL_LIKELIHOOD_LOW, validated_plugin_mapping_required` | `audio_read_failed:instrumental_vocal_pocket.wav:Error, full mix source is unsafe for vocal-forward placement automation, full mix unsafe for vocal recovery` |
| `V37 LEAD VOCAL CLARITY MAX GUARDED` | `lead_vocal` | `raw_vocal` | `blocked` |  | `False` | `PLUGIN_MAPPING_UNSAFE, validated_plugin_mapping_required` | `audio_read_failed:lead_vocal_clarity_processed.wav:Error, pitch_plugin_mapping_required` |
| `V37 BACKGROUND DOUBLE SUPPORT L/R` | `backing_vocal` | `raw_vocal` | `blocked` |  | `False` | `PLUGIN_MAPPING_UNSAFE, validated_plugin_mapping_required` | `audio_read_failed:backing_vocal_side_support.wav:Error, pitch_plugin_mapping_required` |
| `V37 PRINTED VOCAL REVERB SEND` | `reverb_send` | `unknown` | `blocked` |  | `False` | `PLUGIN_MAPPING_UNSAFE, ROLE_NOT_RECOVERY_ELIGIBLE, UNKNOWN_SOURCE_BLOCKED, VOCAL_LIKELIHOOD_LOW, validated_plugin_mapping_required` | `audio_read_failed:vocal_reverb_send_print.wav:Error, unknown_source_skipped` |
| `V37 PRINTED VOCAL DELAY SEND` | `delay_send` | `unknown` | `blocked` |  | `False` | `PLUGIN_MAPPING_UNSAFE, ROLE_NOT_RECOVERY_ELIGIBLE, UNKNOWN_SOURCE_BLOCKED, VOCAL_LIKELIHOOD_LOW, validated_plugin_mapping_required` | `audio_read_failed:vocal_delay_send_print.wav:Error, unknown_source_skipped` |
| `V37 RETURN ReaVerbate dark send` | `unknown` | `unknown` | `blocked` |  | `False` | `PLUGIN_MAPPING_UNSAFE, ROLE_NOT_RECOVERY_ELIGIBLE, UNKNOWN_SOURCE_BLOCKED, VOCAL_LIKELIHOOD_LOW, validated_plugin_mapping_required` | `unknown_source_skipped` |
| `V37 RETURN ReaDelay filtered throw` | `delay_send` | `unknown` | `blocked` |  | `False` | `PLUGIN_MAPPING_UNSAFE, ROLE_NOT_RECOVERY_ELIGIBLE, UNKNOWN_SOURCE_BLOCKED, VOCAL_LIKELIHOOD_LOW, validated_plugin_mapping_required` | `unknown_source_skipped` |

## Blocked Tracks

- `SOURCE full mix reference muted`: `FULL_MIX_UNSAFE_FOR_VOCAL_RECOVERY, PLUGIN_MAPPING_UNSAFE, ROLE_NOT_RECOVERY_ELIGIBLE, VOCAL_LIKELIHOOD_LOW, validated_plugin_mapping_required`; recommended `provide_isolated_stem`; stem required `True`
- `V37 INSTRUMENTAL BUS free EQ pocket`: `FULL_MIX_UNSAFE_FOR_VOCAL_RECOVERY, PLUGIN_MAPPING_UNSAFE, ROLE_NOT_RECOVERY_ELIGIBLE, VOCAL_LIKELIHOOD_LOW, validated_plugin_mapping_required`; recommended `provide_isolated_stem`; stem required `True`
- `V37 LEAD VOCAL CLARITY MAX GUARDED`: `PLUGIN_MAPPING_UNSAFE, validated_plugin_mapping_required`; recommended `validate_plugins_first`; stem required `False`
- `V37 BACKGROUND DOUBLE SUPPORT L/R`: `PLUGIN_MAPPING_UNSAFE, validated_plugin_mapping_required`; recommended `validate_plugins_first`; stem required `False`
- `V37 PRINTED VOCAL REVERB SEND`: `PLUGIN_MAPPING_UNSAFE, ROLE_NOT_RECOVERY_ELIGIBLE, UNKNOWN_SOURCE_BLOCKED, VOCAL_LIKELIHOOD_LOW, validated_plugin_mapping_required`; recommended `validate_plugins_first`; stem required `False`
- `V37 PRINTED VOCAL DELAY SEND`: `PLUGIN_MAPPING_UNSAFE, ROLE_NOT_RECOVERY_ELIGIBLE, UNKNOWN_SOURCE_BLOCKED, VOCAL_LIKELIHOOD_LOW, validated_plugin_mapping_required`; recommended `validate_plugins_first`; stem required `False`
- `V37 RETURN ReaVerbate dark send`: `PLUGIN_MAPPING_UNSAFE, ROLE_NOT_RECOVERY_ELIGIBLE, UNKNOWN_SOURCE_BLOCKED, VOCAL_LIKELIHOOD_LOW, validated_plugin_mapping_required`; recommended `validate_plugins_first`; stem required `False`
- `V37 RETURN ReaDelay filtered throw`: `PLUGIN_MAPPING_UNSAFE, ROLE_NOT_RECOVERY_ELIGIBLE, UNKNOWN_SOURCE_BLOCKED, VOCAL_LIKELIHOOD_LOW, validated_plugin_mapping_required`; recommended `validate_plugins_first`; stem required `False`

## Recovery Drafts

- none

## Pitch Correction Block

- pitch stage blocked: `True`
- pitch plugins inserted: `False`
- pitch parameters written: `False`
- status: `blocked`

## A/B Render Plan

- original render: `False`
- recovery render: `False`
- loudness matched: `False`
- difference: `False`
- status: `plan_only`

## Evaluation

- no rendered recovery draft evaluations

## Original Protection

- original tracks modified: `False`
- original master modified: `False`
- routing modified: `False`
- media modified: `False`
- safe: `True`

## Manual Listening Checklist

- Does the recovered draft sound less metallic without becoming dull?
- Did sibilance become lispy or watery?
- Did the vocal lose body?
- Did consonants smear?
- Did reverb tails become strange?
- Did phase or stereo image become unstable?
- Does the result sound less AI-like, or just darker/quieter?

## Final Recommendation

`validate_plugins_first`
