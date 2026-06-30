# Manual Test Plan - Prompt 13

Use this plan because the repository does not contain an active STFT runtime, model runtime, or in-process REAPER JSFX renderer.

## Host Setup

1. Load `Codex Vocal AI Artifact Split Tamer` in REAPER.
2. Confirm the installed JSFX matches `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`.
3. Use the default Preserve state.
4. Keep Residual Monitor off unless the test explicitly asks for it.

## Tests

### Silence

- Input: generated silence.
- Expected: output remains silence, no meter spikes, no generated noise, no NaN/Inf symptoms.

### Bypass And Disabled Processing

- Input: clean vocal or sine.
- Set Bypass on.
- Set Processing Enabled off in a separate pass.
- Expected: dry passthrough, no clicks, no sudden silence.

### DryWet Zero

- Input: clean vocal or harmonic stack.
- Set Dry/Wet to `0`.
- Expected: dry passthrough, no filterbank coloration.

### Clean Sine Safety

- Input: 1 kHz, 3 kHz, and 6 kHz sine files.
- Expected: no level collapse, no obvious modulation, no clicks, no invalid output.

### Clean Vocal Safety

- Input: dry clean vocal.
- Expected: no sudden silence, no garbage output, no obvious full-band dull collapse from safety changes.
- This is not an approval that audio quality improved.

### Block Size Matrix

- Host block sizes: 64, 512, 2048 if available.
- Expected: stable processing, no crash, no invalid output.

### Sample Rate Matrix

- Project rates: 44.1 kHz, 48 kHz, 88.2 kHz, 96 kHz if available.
- Expected: stable processing and no crash after rate changes.

### Residual Monitor Spot Check

- Enable Residual Monitor = Residual.
- Input: clean vocal and artifact-heavy vocal.
- Expected: residual mode is usable for listening checks but is not enabled by fallback paths. Disable after test.

### Corrupt Model Output

- not applicable in the active plugin because no model runtime exists.
- If a future model runtime is added, force wrong shape, NaN/Inf, extreme values, all-zero destructive mask, and unknown output type.
- Expected: dry fallback or contract fallback, no crash, no invalid output.

## Pass / Fail

Fail the patch if any of these occur:

- silence becomes non-silence
- bypass or disabled processing is not dry
- DryWet `0` is not dry
- clean tones collapse
- output contains NaN/Inf symptoms, full-scale blasts, or sudden silence unrelated to dry input
- REAPER crashes or the JSFX differs from the repo copy
