# Audio Quality Guardrails

The product is a source-preserving AI noise and artifact suppressor. It is not a maximum noise remover.

## Non-Negotiables

- Default mode must preserve source quality.
- Moderate remaining noise is acceptable.
- Source damage is not acceptable.
- Residual must not contain obvious ghost vocal.
- Consonants must remain intact.
- 2 kHz to 8 kHz presence/clarity must be protected.
- 8 kHz+ air and ambience must be protected.
- Transients must be protected.
- Harmonic texture must be protected.
- M/S processing must not collapse stereo width.
- Strong mode must be isolated and never default.
- Invalid model output must never reach audio.
- Bypass and DryWet 0 must be dry.
- NaN/Inf must never reach output.

## Prohibited Fixes

- No exciter to hide damaged denoise.
- No high-shelf boost to fake clarity.
- No artificial clarity reconstruction without a dedicated approved issue.
- No hard mask in the normal path.
- No full-band gain collapse.
- No broad high-frequency suppression to fake cleanliness.
- No hidden destructive processing.
- No strong mode as default.
- No model output bypassing MaxSuppressionDb or preserve guards.

## Residual Listening Rule

Residual = original minus processed.

Good residual:

- noise
- hiss
- hum
- AI chirp
- metallic artifact
- unwanted fuzz

Bad residual:

- vocal phrases
- S/T/CH consonants
- musical breaths
- harmonic overtones
- guitar picking
- snare attack
- room tail that belongs to the source

If residual contains source, reduce processing or fail the preset.

## Default Preset Rule

Preserve is the only acceptable fresh default. A cleaner but duller Preserve output is a failed release candidate.

Fresh Preserve must keep:

- Amount around 0.30
- DryWet around 0.70 to 0.75
- MaxSuppressionDb around 8 dB
- MaskStrength around 0.35
- Vocal/Clarity/Air/Transient Preserve high
- Residual Monitor Off
- Strong Off

## Release Decision Rule

Metrics can catch regressions, but they cannot approve release alone. If metrics pass and listening fails, release fails. If listening passes but clean-input do-no-harm tests fail, release fails.
