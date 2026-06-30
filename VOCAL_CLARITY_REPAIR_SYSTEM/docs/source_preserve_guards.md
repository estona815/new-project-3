# Source Preserve Guards

Prompt 15 result: source-preservation patch. This patch does not add stronger denoise, EQ boost, exciter, artificial air, new model inference, new STFT, new M/S logic, new multiband logic, surgical notch processing, or preset tuning.

## Implementation Note

- parameter definition file: `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx` sliders.
- parameter snapshot file: JSFX `@sample`, `snap_*` variables.
- conservative gain calculation file: active JSFX gain path plus `VOCAL_CLARITY_REPAIR_SYSTEM/ml/model_output_contract.py`.
- STFT/mask file: active STFT NOT FOUND; JSFX uses a time-domain filterbank mask-equivalent path.
- temporal smoothing file: JSFX `@sample` gain smoothing.
- model mask integration file: `VOCAL_CLARITY_REPAIR_SYSTEM/ml/model_output_contract.py`.
- dry/wet file: JSFX `@sample`.
- tests available: `tests/test_prompt15_source_preserve_guards.py`, existing JSFX tests, model contract tests, and RC QA.

## Parameters

The active JSFX already had these preservation-first controls. Prompt 15 now snapshots them at the top of `@sample` before denoise decisions:

| Parameter | Default | Behavior |
| --- | ---: | --- |
| VocalPreserve | `0.85` | Reduces allowed attenuation in vocal presence and center-source protection paths. |
| ClarityPreserve | `0.85` | Reduces allowed attenuation in consonant, edge, and presence paths. |
| AirPreserve | `0.80` | Reduces allowed attenuation in fizz/air paths and the air-loss guard. |
| TransientPreserve | `0.80` | Reduces attenuation during detected attack/consonant frames. |
| HarmonicPreserve | `0.75` internal | Existing broad harmonic/source proxy in JSFX; full F0 tracking remains deferred. |

These parameters only reduce attenuation. They do not boost, synthesize high frequencies, change dry/wet, or override bypass.

## Frequency Preserve Weights

The frequency preserve weights are lightweight helper curves for protected source regions.

The model-output contract now exposes future-integration helper weights:

- `get_vocal_presence_weight(freqHz)`: protects roughly `1.8 kHz..5.5 kHz`, centered around `3.5 kHz`.
- `get_clarity_weight(freqHz)`: protects roughly `3.5 kHz..8.5 kHz`, centered around `6 kHz`.
- `get_air_weight(freqHz)`: protects roughly `8 kHz..18 kHz`, centered around `12 kHz`.

These helpers return `0.0..1.0`, are finite-safe, and never create gain above `1.0`.

## Suppression Limit Order

The protected gain path now follows this safety order:

```text
base noise probability
-> base frequency suppression limit
-> vocal / clarity / air preserve limit reduction
-> transient preserve limit reduction
-> harmonic preserve if valid F0 is available
-> attenuationDb
-> gain floor from protected limit
-> frequency smoothing
-> temporal smoothing
-> full-band collapse guard
-> spectral tilt guard
-> air loss guard
-> clamp gain to valid range
-> reconstruction
-> dry/wet
-> final finite check
```

In the active JSFX path, Prompt 15 also makes transient/harmonic limit edits per-sample local variables, so the sample loop does not keep mutating the global band limit.

## Transient Detection

The active JSFX uses a lightweight transient score based on:

- high-band positive flux
- full-band energy rise
- light smoothing through `transient_score_sm`

When the score is high, source-preserve logic reduces allowed attenuation. It does not add transient enhancement or lookahead.

## Spectral Tilt Guard

The active JSFX estimates whether processing is making the signal darker by comparing presence energy to low-mid energy before and after predicted gain. If `2 kHz..8 kHz` is over-reduced, the guard blends attack/sandy gains toward dry.

This is not EQ compensation. It only reduces attenuation already being applied.

## Air Loss Guard

The active JSFX estimates high-band loss from fizz/air energy. If high-band attenuation is too broad, the guard gently blends fizz/air gains toward dry based on `AirPreserve`.

This is not an air generator and does not widen stereo.

## Model And Spectral Subtraction Interaction

There is still no active runtime model. The Python contract now makes future model masks advisory under the same preserve limits:

- model gain masks use `min_model_gain()` based on the protected suppression limit.
- noise-probability masks are converted into bounded attenuation through `bounded_gain_from_probability()`.
- spectral-subtraction helper can use `SafetyConfig` so the effective gain floor cannot bypass preserve guards.

Invalid model output still falls back as before.

## Residual Source Leakage

The active JSFX residual monitor remains a listening/debug mode: `dry input - processed-before-drywet`. Prompt 15 does not add heavy residual correlation or source-leakage classification in the audio path. Residual source-leakage warning is deferred to offline or render-harness validation.

## Limitations

- Full F0 harmonic tracking is deferred because no pitch estimate exists in the active JSFX path.
- No direct JSFX execution harness exists; tests are static/direct Python contract checks plus RC QA.
- Real REAPER renders and manual listening remain required before claiming audio quality improvement.
- This patch deliberately leaves more noise when removal would risk vocal presence, consonants, air, transients, ambience, or harmonic texture.

## Tests Added

- Preserve parameter defaults and snapshot coverage.
- Vocal/clarity/air frequency weight tests.
- Suppression-limit protection tests.
- Transient and harmonic helper tests.
- Model-mask and spectral-subtraction preserve-floor tests.
- Spectral tilt and air-loss guard helper tests.
- Documentation scope tests.
