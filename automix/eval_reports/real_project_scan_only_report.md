# Real Project Scan-Only Audit Report

## Summary

- Project: `mesi_1_v37_VOCAL_CLARITY_FINAL`
- Mode: `real_project_scan_only`
- Read-only status: `True`
- Prompt 41 validation status: `PASS`
- Safe-draft readiness: `False`
- Recommended next mode: `validate_plugin_mappings`

## Read-Only Guard

- Modified: `False`
- Safe: `True`
- Warnings: `none`

## Track Role Map

| Track | Role | Confidence | Source Type | Vocal Likelihood | Full Mix Likelihood | Risk | Recommended Next Action |
|---|---|---:|---|---:|---:|---|---|
| `SOURCE full mix reference muted` | `full_mix_reference` | 0.86 | `full_mix` | 0.25 | 0.82 | `unsafe` | `provide_isolated_stems` |
| `V37 INSTRUMENTAL BUS free EQ pocket` | `instrumental_bus` | 0.8 | `full_mix` | 0.1 | 0.82 | `unsafe` | `provide_isolated_stems` |
| `V37 LEAD VOCAL CLARITY MAX GUARDED` | `lead_vocal` | 0.86 | `raw_vocal` | 0.72 | 0.1 | `unsafe` | `validate_plugin_mappings_first` |
| `V37 BACKGROUND DOUBLE SUPPORT L/R` | `backing_vocal` | 0.82 | `raw_vocal` | 0.72 | 0.1 | `unsafe` | `validate_plugin_mappings_first` |
| `V37 PRINTED VOCAL REVERB SEND` | `reverb_send` | 0.76 | `unknown` | 0.2 | 0.18 | `unsafe` | `analyze_manually` |
| `V37 PRINTED VOCAL DELAY SEND` | `delay_send` | 0.76 | `unknown` | 0.2 | 0.18 | `unsafe` | `analyze_manually` |
| `V37 RETURN ReaVerbate dark send` | `unknown` | 0.35 | `unknown` | 0.2 | 0.1 | `unsafe` | `analyze_manually` |
| `V37 RETURN ReaDelay filtered throw` | `delay_send` | 0.76 | `unknown` | 0.2 | 0.18 | `unsafe` | `analyze_manually` |

## Track Warnings

- `SOURCE full mix reference muted`: `audio_read_failed:source_full_mix_reference.wav:Error, full mix source is unsafe for vocal-forward placement automation, full mix unsafe for vocal recovery, full_mix_unsafe_for_pitch_correction`
- `V37 INSTRUMENTAL BUS free EQ pocket`: `audio_read_failed:instrumental_vocal_pocket.wav:Error, full mix source is unsafe for vocal-forward placement automation, full mix unsafe for vocal recovery, full_mix_unsafe_for_pitch_correction`
- `V37 LEAD VOCAL CLARITY MAX GUARDED`: `audio_read_failed:lead_vocal_clarity_processed.wav:Error, pitch_plugin_mapping_required`
- `V37 BACKGROUND DOUBLE SUPPORT L/R`: `audio_read_failed:backing_vocal_side_support.wav:Error, pitch_plugin_mapping_required`
- `V37 PRINTED VOCAL REVERB SEND`: `audio_read_failed:vocal_reverb_send_print.wav:Error, unknown_source_skipped`
- `V37 PRINTED VOCAL DELAY SEND`: `audio_read_failed:vocal_delay_send_print.wav:Error, unknown_source_skipped`
- `V37 RETURN ReaVerbate dark send`: `unknown_source_skipped`
- `V37 RETURN ReaDelay filtered throw`: `unknown_source_skipped`

## Source Safety

- Safe vocal candidates: `2`
- AI/already processed vocals: `0`
- Source-separated vocals: `0`
- Full-mix unsafe tracks: `2`
- Stem-required tracks: `2`
- Unknown tracks: `4`

## Plugin Readiness

- Safe adapters: `0`
- Provisional adapters: `3`
- Unsafe/unmapped: `11`
- Stock fallbacks: `4`
- JSFX fallbacks: `0`
- Missing mappings: `15`

## Pitch Correction Dry-Run

- Tracks eligible: `0`
- Tracks skipped: `4`
- Already tuned skipped: `0`
- Full mix unsafe: `2`
- Source-separated high risk: `0`
- Plugin mapping required: `True`
- Manual tuning required: `true if pitch plugin mapping remains unsafe`

## Vocal Recovery Dry-Run

- Tracks eligible: `0`
- Tracks blocked: `4`
- Suggested profiles: `conservative_ai_vocal_cleanup`
- Stem required: `2`

## Vocal Placement Dry-Run

- Lead vocal candidate: `V37 LEAD VOCAL CLARITY MAX GUARDED`
- Instrumental bus candidate: `V37 INSTRUMENTAL BUS free EQ pocket`
- Masking risk: `not fully measured unless track audio was available`
- Placement readiness: `False`

## Premaster Dry-Run

- Premaster readiness: `False`
- Loudness/peak measurement availability: `scan-only; source-dependent`
- Translation check readiness: `blocked until accepted mix draft exists`
- Warnings: `no premaster render created`

## Reference / Target Profile

- Target profile: `digicore_hyperpop_hiphop_vocal_forward`
- References found: `0`
- Reference analysis status: `manifest-only unless WAV references were supplied`
- Safe adjustment readiness: `False`

## Stem Request Plan

- See `automix/eval_reports/real_project_stem_request_plan.md`.

## Safe-Draft Readiness

- Score: `0.714286`
- Ready: `False`
- Blockers: `isolated_stems_required, validated_plugin_mapping_required`
- Warnings: `unknown_tracks_skipped`

## Next Required Actions

- `isolated_stems_required`
- `validated_plugin_mapping_required`

## Final Recommendation

`validate_plugin_mappings_first`
