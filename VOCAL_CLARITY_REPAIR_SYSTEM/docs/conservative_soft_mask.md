# Conservative Soft Mask

Prompt 14 result: first denoise-behavior patch, kept conservative. No EQ boost, high shelf, exciter, artificial clarity restoration, new AI inference, new STFT, new M/S logic, new multiband logic, or preset tuning was added.

## Implementation Note

- mask/gain calculation file: `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`
- model output postprocessing file: `VOCAL_CLARITY_REPAIR_SYSTEM/ml/model_output_contract.py`
- spectral subtraction path: NOT FOUND in the active plugin.
- STFT reconstruction file: NOT FOUND in the active plugin.
- parameter snapshot file: JSFX `@sample` in `vocal_ai_artifact_split_tamer.jsfx`.
- MaxSuppressionDb source: JSFX `slider10` `Max Reduction (dB)`, default `8`, clamped `0..24`.
- tests available: `tests/test_vocal_ai_artifact_split_tamer_jsfx.py`, `tests/test_model_output_contract.py`, `tests/test_prompt13_stft_mask_model_safety.py`, `tests/test_prompt14_conservative_soft_mask.py`, and `VOCAL_CLARITY_REPAIR_SYSTEM/eval/rc_qa.py`.

Do not guess architecture: the active processor is still REAPER JSFX time-domain filterbank DSP. There is no C++ `processBlock`, no APVTS, no active STFT/iSTFT, and no runtime AI model inference.

## Current Destructive-Behavior Audit

| File | Function | Current formula | Risk | Patch |
| --- | --- | --- | --- | --- |
| `vocal_ai_artifact_split_tamer.jsfx` | `@slider` | `mapped_amount = pow(amount, 1.6)` | Already conservative; future edits could accidentally revert to linear amount. | Locked by Prompt 14 tests. |
| `vocal_ai_artifact_split_tamer.jsfx` | `@sample` high bands | Soft logistic detector probability multiplied by band cap, mapped Amount, MaskStrength, and band amount. | Broad high-band attenuation can still dull vocals if detector is wrong. | Made frequency caps explicit and kept gains bounded. |
| `vocal_ai_artifact_split_tamer.jsfx` | `@sample` high-band target gains | Adjacent-band smoothing: `0.25 / 0.50 / 0.25` style. | Too much smoothing would smear formants; no heavy smoothing was added. | Kept light existing smoothing only. |
| `vocal_ai_artifact_split_tamer.jsfx` | `@sample` full-band guard | Detects too many high bands near floor and blends gains toward dry; suspicious collapse dry-fallbacks. | Previous near-floor threshold waited for 3 high bands at floor. | Prompt 14 now triggers the near-floor blend when 2 high bands are near floor. |
| `model_output_contract.py` | `postprocess_model_output` | Model output is advisory and feeds bounded probability/gain. | Future runtime model mask could be trusted too directly if it bypasses contract. | Added Prompt 14 conservative gain and spectral-subtraction helpers for tests/future integration. |

No hard 0/1 STFT mask, spectral-bin zeroing, direct model-mask multiplication, raw spectral subtraction, or waveform replacement was found in the active JSFX path.

## New Soft Attenuation Behavior

The active JSFX already used a soft-knee detector. Prompt 14 keeps that behavior and makes its safety role explicit:

```text
probability = logistic((detectorDb - thresholdDb) / kneeDb)
attenuationDb = bandLimitDb * probability * mappedAmount * maskStrength
gain = clamp(dbToGain(-attenuationDb), minGain, 1.0)
```

The Python model contract now also exposes `compute_soft_noise_probability()` and `compute_conservative_denoise_gain()` for future model/STFT integration tests. Those helpers use SNR-style probability:

```text
0.0 = likely source, preserve
1.0 = likely noise/artifact, eligible for bounded attenuation
```

No normal denoise path may produce a `0.0` gain.

## Amount Mapping

Amount remains nonlinear and conservative:

```text
mappedAmount = amount^1.6
```

Expected behavior:

- `0.00 -> 0.00`
- `0.25 -> about 0.11`
- `0.50 -> about 0.33`
- `0.75 -> about 0.63`
- `1.00 -> 1.00`

Amount never boosts. Amount `0` produces no denoise attenuation. Amount `1` still obeys MaxSuppressionDb and frequency caps.

## MaskStrength Behavior

MaskStrength remains attenuation depth:

```text
attenuationDb = bandLimitDb * noiseProbability * mappedAmount * maskStrength
```

- Range: `0..1`
- Default: `0.35`
- `0` means no attenuation.
- `1` means full allowed attenuation, still bounded by MaxSuppressionDb and band caps.
- It cannot bypass minGain or full-band guards.

## MaxSuppressionDb Cap

Max Reduction is the global safety cap:

- Default: `8 dB`
- Range: `0..24 dB`
- Normal gain floor: `dbToGain(-bandLimitDb)`
- No normal path can zero a band/bin.

## Frequency-Dependent Caps

Active JSFX high-band caps are now named constants:

| Band / Region | Active cap |
| --- | ---: |
| attack / presence | `min(MaxReduction, 4 dB)` before existing preserve guards |
| sandy / sibilance | `min(MaxReduction, 4 dB)` before existing preserve guards |
| fizz | `min(MaxReduction, 3 dB)` before existing preserve guards |
| air | `min(MaxReduction, 3 dB)` before existing preserve guards |

The Python contract's broad future-integration helper uses:

| Frequency | Limit |
| --- | ---: |
| `<120 Hz` | `min(global, 10 dB)` |
| `120 Hz..1 kHz` | `min(global, 8 dB)` |
| `1 kHz..2 kHz` | `min(global, 6 dB)` |
| `2 kHz..8 kHz` | `min(global, 4 dB)` |
| `8 kHz+` | `min(global, 3 dB)` |

These functions only reduce allowed attenuation. They never boost.

## Prompt 15 Source Preserve Update

Prompt 15 now applies source-preserve guards to the suppression limit before gain is calculated. In practice:

- vocal presence, clarity, and air preserve values reduce the allowed attenuation limit in protected frequency regions.
- transient preserve reduces attenuation during detected attack/consonant frames.
- harmonic preserve remains an internal JSFX source-proxy, with full F0 tracking deferred.
- model mask floors and optional spectral-subtraction helper paths now use protected suppression limits through the model contract.

This keeps Prompt 14's soft-mask shape but makes protected source regions harder to over-attenuate.

## Model Mask Integration

There is no active runtime model. In the contract:

- GainMask is clamped/floored and converted to noise probability.
- NoiseProbabilityMask is clamped to `0..1`.
- The final gain is computed through one bounded attenuation path.
- Model output cannot force gain to zero.
- Invalid model output keeps the Prompt 13 fallback behavior.

## Spectral Subtraction Safety

No active spectral subtraction path exists. For future integration, `conservative_spectral_subtraction_gain()` implements the required safety shape:

```text
rawProcessed = inputMagnitude - noiseMagnitude * mappedAmount * maskStrength
floorMagnitude = inputMagnitude * dbToGain(-bandLimitDb)
processed = max(rawProcessed, floorMagnitude, 0)
effectiveGain = clamp(processed / max(inputMagnitude, eps), minGain, 1)
```

This prevents negative magnitudes and destructive zero collapse.

## Smoothing And Collapse Guard

- Temporal smoothing: existing asymmetric smoothing remains. Entering stronger attenuation is slower; recovery toward dry is faster.
- Frequency smoothing: existing adjacent high-band smoothing remains light.
- Full-band guard: Prompt 14 improves the near-floor guard by blending gains toward dry when at least two high bands sit within 1 dB of their floors. Suspicious broad RMS collapse still dry-fallbacks.

## Tests Added

- Prompt 14 docs and architecture-scope checks.
- Soft noise probability and knee behavior.
- Amount mapping, MaskStrength, MaxSuppressionDb, and frequency cap tests.
- Model mask bounded-integration tests.
- Spectral subtraction safety helper tests.
- Full-band collapse guard tests.

## Remaining Limitations

- Prompt 14 does not add VocalPreserve, ClarityPreserve, AirPreserve, TransientPreserve, HarmonicPreserve, M/S processing, or multiband processing. Some of those controls already exist from earlier local work, but Prompt 15 now snapshots the preserve controls and ties future model/spectral-subtraction helpers to protected suppression limits.
- The evaluation harness still does not execute the JSFX in-process.
- Real REAPER renders, clean-vocal A/B, residual listening, and DAW block-size/sample-rate tests remain required.
- No claim is made that vocals are fixed, clarity is restored, or AI artifacts are solved.
