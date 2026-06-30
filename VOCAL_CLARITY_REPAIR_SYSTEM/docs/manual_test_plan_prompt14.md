# Manual Test Plan - Prompt 14

Use this plan because the repository still does not contain an in-process REAPER JSFX renderer, active STFT runtime, or active model runtime.

## Setup

1. Load `Codex Vocal AI Artifact Split Tamer` in REAPER.
2. Confirm the installed JSFX matches the repo copy.
3. Start from the default Preserve state.
4. Keep Residual Monitor off unless explicitly checking residual output.

## Checks

### Clean Vocal Default

- Input: clean dry vocal.
- Expected: no sudden dull collapse, no sudden silence, no invalid output.
- This does not approve final vocal quality.

### Vocal With Hiss

- Input: vocal with steady hiss.
- Expected: hiss may reduce moderately, but voice should not become dramatically darker or smeared.

### Sine Safety

- Inputs: 1 kHz, 3 kHz, 6 kHz sine.
- Expected: no heavy attenuation under default Preserve, no modulation, no clicks.

### Silence

- Input: silence.
- Expected: output remains silence, no meter spikes.

### Amount Sweep

- Amount `0`: expected no denoise attenuation.
- Amount `50`: expected moderate behavior, not destructive.
- Amount `100`: expected stronger but still bounded by Max Reduction and frequency caps.

### MaskStrength Sweep

- MaskStrength `0`: expected no denoise attenuation.
- MaskStrength `0.35`: default conservative depth.
- MaskStrength `1`: strongest allowed attenuation, still bounded.

### Max Reduction

- Max Reduction `0`: expected no attenuation.
- Max Reduction `8`: default conservative cap.
- Max Reduction higher values: still no full-band silence or invalid output.

### Residual Monitor

- Enable Residual Monitor = Residual briefly.
- Expected: residual mode can be used for listening, and fallback paths do not force residual output.

### Invalid Model Output

- Not applicable in active JSFX because no runtime model exists.
- Future model build must test NaN, Inf, wrong shape, all-zero destructive masks, and unknown output type.

## Fail Conditions

Fail the patch if:

- bypass or DryWet `0` is not dry
- silence becomes non-silence
- clean sine collapses
- output blasts, becomes NaN/Inf-like, or goes unexpectedly silent
- default Preserve sounds obviously darker because of this patch
- installed JSFX differs from repo copy
