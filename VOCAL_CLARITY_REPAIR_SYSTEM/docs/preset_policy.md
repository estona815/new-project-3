# Preset Policy

Canonical preset data lives in `VOCAL_CLARITY_REPAIR_SYSTEM/presets/factory_presets_safe_defaults.json`.

## Philosophy

The plugin is source-preserving first. Presets must not chase maximum noise reduction if that damages vocal presence, consonants, high-frequency air, transients, harmonic texture, ambience, stereo width, or original timbre.

## Factory Presets

| Preset | Priority | Mode | Release role |
| --- | --- | --- | --- |
| Preserve | P1 source preservation | Preserve | Fresh default |
| Balanced | P1 source preservation | Balanced | General use |
| AI Metallic Surgical | P1 artifact targeting | Surgical AI | Source-specific metallic artifacts |
| Hiss / Room Tone Gentle | P1 air preservation | Preserve | Gentle broadband noise |
| Voiceover Clean | P1 intelligibility | Balanced | Spoken word |
| Strong Test / Repair | P0/P1 safety only | Strong Test | Isolated stress/repair mode |
| DSP Only Safe | P0 fallback | Preserve | Model-disabled fallback |
| Side Noise Cleanup | P1 stereo safety | Balanced | Side-biased noise |
| Artifact Focus Low Denoise | P1 surgical low-denoise | Surgical AI | Artifact focus, low broad denoise |

## Default Rules

- Fresh default is Preserve.
- Strong is never default.
- Residual Monitor is Off by default.
- Amount default is 30%.
- Dry/Wet default is 70%.
- MaxSuppressionDb default is 8 dB.
- MaskStrength default is 0.35.
- Vocal/Clarity/Air/Transient Preserve defaults are high.

## Migration Rules

- Existing JSFX slider order must remain stable.
- Missing new parameters get safe defaults.
- Invalid values are clamped to absolute safety ranges.
- Unknown preset versions load through safe fallback policy.
- Strong mode is not auto-selected during migration.
- User values inside absolute safe range remain loadable.

## Tuning Rules

- No preset tuning without Prompt 7 evaluation.
- No Strong tuning as default demo quality.
- No high-shelf, exciter, or fake clarity compensation.
- No broad high-frequency suppression that removes air.
- Preset cannot pass if residual contains obvious source.

## Pass Gates

Preserve minimum automated targets:

- source preservation >= 85 average
- clarity >= 85 average
- air >= 80 average
- transient >= 85 average
- residual cleanliness >= 80 average
- safety = 100

Balanced and Surgical may clean more, but cannot bypass safety or residual checks. Strong is quality-report-only and must still pass safety.
