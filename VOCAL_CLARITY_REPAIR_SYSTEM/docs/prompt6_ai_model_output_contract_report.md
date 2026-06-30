# Prompt 6 AI Model Output Contract Report

## ML / Inference Audit

| File | Class/function | Current role | Model input | Model output | Risk | Patch needed |
| --- | --- | --- | --- | --- | --- | --- |
| `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx` | JSFX `@sample` | Actual REAPER plugin path. Uses conservative DSP, soft probabilities, M/S suppressor, residual monitor, dry/wet and fallback. | Audio samples only | No model output | No ML path exists here; adding fake inference would be unsafe. | Keep model output from bypassing DSP; document no model backend. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/ml/model_output_contract.py` | `ModelOutputType`, `postprocess_model_output` | New preservation-first model output contract and validator. | Tensor-like Python values plus input/domain metadata | Bounded probability/gain or safe blended samples | Contract module is not an audio-thread backend. | Use as future inference adapter reference/test harness. |
| `tools/*vocal_clarity*.py` | `spectral_denoise` helpers | Offline render scripts with STFT denoise utilities. | Offline NumPy audio arrays | Offline rendered audio | Not plugin inference; can over-denoise if reused blindly. | Do not treat as real-time model path. |
| `CMakeLists.txt` | analyzer target | References missing analyzer sources. | n/a | n/a | Not a plugin build path; no ML. | No Prompt 6 code integrated here. |

Current model output type in the plugin: **none / unknown**. Unknown model output is now explicitly rejected by the contract.

## Chosen Architecture

No AI model backend exists in this repository. Prompt 6 was implemented as a source-preserving model output contract and postprocessing harness rather than adding an unverified model.

Required future inference flow:

```text
input
-> preprocessing
-> model inference
-> output validation
-> convert model output to bounded noise/artifact probability
-> combine with DSP detector using model confidence
-> Prompt 2 soft mask
-> Prompt 3 preserve guards
-> Prompt 5 M/S multiband budget
-> dry/wet and output safety
```

The model advises the DSP. The model does not own the final audio.

## Output Contract

Implemented output types:

- `Unknown`
- `GainMask`
- `NoiseProbabilityMask`
- `ResidualEstimate`
- `MagnitudeEstimate`
- `ComplexMask`
- `Waveform`

Rules implemented in `model_output_contract.py`:

- Unknown output type is invalid.
- Shape mismatch is invalid.
- NaN/Inf is invalid.
- Gain masks are converted to noise probability instead of directly multiplying audio.
- Noise probability is advisory and bounded by preserve guards.
- Residual estimates are RMS-limited before subtraction.
- Magnitude and complex outputs are high-risk and confidence-reduced.
- Waveform output is high-risk and only blended toward input after damage checks.
- All final gain decisions pass through `MaxSuppressionDb`, frequency-dependent caps, amount mapping, mask strength, and preserve weights.

## Confidence And Domain Handling

Implemented:

- `ModelDomainStatus.Ok`
- `Silence`
- `TooQuiet`
- `Clipped`
- `UnsupportedSampleRate`
- `UnsupportedChannels`
- `OutOfDistributionSuspected`

Domain mismatch lowers model confidence. Invalid output sets model confidence to `0.0` and falls back to DSP probability.

## Training Redesign Recommendations

Current repository has no training scripts, losses, datasets, or model architecture to patch. Required future training direction:

- Prefer mask, probability, or residual learning over direct enhanced waveform.
- Add clean / near-clean identity loss.
- Add multi-resolution STFT loss using 256, 512, 1024, and 2048 FFT sizes.
- Add 2-8 kHz presence and consonant preservation loss.
- Add 8-16 kHz air preservation loss with tolerance, not high-frequency hallucination.
- Add harmonic or spectral-peak preservation loss.
- Add transient / onset / spectral-flux preservation loss.
- Add timbre consistency loss using spectral envelope or cepstral features.
- Add residual source leakage loss on `removed = input - enhanced`.

Training target rule: do not train `noisy room vocal -> dry studio vocal`. Train toward same source character with only artifact/noise reduced.

## Dataset Requirements

Future datasets must include:

- clean and near-clean vocals
- breath, consonants, sibilance, room tails and ambience
- AI voice / source separation / watery / metallic / codec artifacts
- drums, guitar picking, piano, synths, backing vocals, full mixes
- room tone, hiss, hum, fan and environmental noise
- stereo examples if stereo processing is expected

The model must learn “do nothing” on clean material.

## Evaluation Protocol

For each test file render:

- original
- DSP-only
- AI-assist output
- residual / removed signal

Score:

- noise/artifact reduction
- vocal preservation
- clarity
- air preservation
- transient preservation
- harmonic preservation
- residual source leakage
- stereo/space
- overall quality

A model with high noise reduction but poor source preservation fails.

## Unresolved Risks

- No actual model file, backend, tensor allocator, or real-time inference thread exists.
- No model latency can be measured yet.
- No manual A/B was performed.
- The new module is a contract/test harness; future C++ or JSFX inference integration must still be implemented against this contract.

