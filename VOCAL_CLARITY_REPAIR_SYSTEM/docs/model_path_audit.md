# Model Path Audit

## Active Runtime Model Path

No active AI model path was found in the REAPER JSFX plugin.

- Model loading path: NOT FOUND.
- Model inference call: NOT FOUND.
- Runtime tensor allocation: NOT FOUND.
- ONNX / Torch / TFLite backend: NOT FOUND.
- Runtime model output postprocessing: NOT FOUND.
- Model disabled behavior in active plugin: NOT APPLICABLE; there is no model. The closest runtime control is `ProcessingEnabled`, which dry-passes when off (`vocal_ai_artifact_split_tamer.jsfx:706-710`).
- Model missing behavior: metadata declares `model_version: none`, `model_file_required: false`, and `missing_model_behavior: DSP Only safe path` (`release/rc_metadata.json:19-26`).

Searches performed: `rg "model|inference|tensor|onnx|torch|tflite"`, plus direct inspection of JSFX, `ml/`, presets, release metadata, and tests.

## Runtime Output Type

Model output type in active plugin:

MODEL OUTPUT TYPE UNKNOWN - MUST NOT BE TRUSTED WITHOUT CONTRACT

Reason: the active audio path has no model inference and no model output. Any future inference integration must explicitly declare and validate output type before audio use.

## Existing Contract Module

The repository contains a Python contract for future model output validation. Contract only: this module is not active runtime inference and is not connected to the JSFX audio path.

| Area | Evidence | Behavior |
| --- | --- | --- |
| Output type enum | `model_output_contract.py:9-16` | Defines `UNKNOWN`, `GAIN_MASK`, `NOISE_PROBABILITY_MASK`, `RESIDUAL_ESTIMATE`, `MAGNITUDE_ESTIMATE`, `COMPLEX_MASK`, `WAVEFORM`. |
| Metadata | `model_output_contract.py:39-49` | Expected sample rate, channel count, input/output shape, latency, dataset metadata. |
| Safety config | `model_output_contract.py:52-67` | Preservation-first defaults: amount, mask strength, max suppression, preserve controls, waveform/residual limits, and max absurd output magnitude. |
| Soft mask helpers | `model_output_contract.py:101-110`, `:197-264` | Prompt 14 helpers for soft probability, conservative gain, spectral subtraction floors, and full-band collapse guard tests. |
| Shape check | `model_output_contract.py:367-398` | Rejects missing, ragged, and mismatched output shape. |
| Non-numeric/finite/range check | `model_output_contract.py:400-442` | Rejects non-numeric, empty, NaN, Inf, or absurd-magnitude output. |
| Mask handling | `model_output_contract.py:449-455`, `:502-526` | GainMask and ComplexMask are floored to `min_model_gain`; NoiseProbabilityMask is clamped to 0..1. |
| Residual handling | `model_output_contract.py:457-483` | Requires matching length and rejects residual RMS above safety budget. |
| Magnitude handling | `model_output_contract.py:485-500` | Rejects negative magnitudes and clamps effective gain to the safety floor. |
| Waveform handling | `model_output_contract.py:528-559` | Requires matching length and rejects suspicious RMS ratio; does not directly replace waveform. |
| Final bounded gain | `model_output_contract.py:561-575` | Blends model/DSP probability and returns bounded gain. |

## Required Model Questions

| Question | Active Runtime Answer | Evidence | Risk |
| --- | --- | --- | --- |
| model file format | NOT FOUND | No runtime model files or backend references found. | Future integration undefined. |
| model load location | NOT FOUND | JSFX contains no loader; metadata says no model file required (`release/rc_metadata.json:19-26`). | None for current JSFX. |
| model load timing | NOT FOUND | No loader. | Future real-time safety unknown. |
| inference backend | NOT FOUND | No ONNX/Torch/TFLite runtime. | Do not claim AI inference. |
| thread used | NOT FOUND | No inference. | Future thread model must be specified. |
| input preprocessing | NOT FOUND runtime | JSFX detector preprocessing is DSP, not model input (`vocal_ai_artifact_split_tamer.jsfx:231-288`). | Could be confused with AI features. |
| input tensor shape | NOT FOUND runtime | Contract metadata supports shapes (`model_output_contract.py:39-49`). | Must be defined before use. |
| sample-rate expectation | NOT FOUND runtime | Contract default expected sample rate 48000 (`model_output_contract.py:43`). | Contract-only value. |
| output tensor shape | NOT FOUND runtime | Contract shape check exists (`model_output_contract.py:266-276`). | Must be wired into future runtime. |
| output type | NOT FOUND runtime | Contract enum exists (`model_output_contract.py:9-16`). | Unknown model output must be rejected. |
| output validation | NOT FOUND runtime; FOUND contract | Contract checks shape/finite (`model_output_contract.py:266-310`). | Not active. |
| fallback behavior | NOT FOUND runtime; FOUND contract | Invalid contract fallback helper at `model_output_contract.py:203-223`. | Active plugin has no model fallback. |
| NaN/Inf handling | NOT FOUND runtime for model; FOUND contract | `model_output_contract.py:301-310`. | Not active. |
| model disabled behavior | NOT FOUND model; DSP disabled dry-passes | `vocal_ai_artifact_split_tamer.jsfx:706-710`. | Naming mismatch. |
| model not ready behavior | NOT FOUND | No model. | Future patch required if model added. |
| invalid output behavior | NOT FOUND runtime; contract invalid result | `model_output_contract.py:255-310`. | Future integration must not bypass this. |

## Conclusion

The current plugin is a source-preserving DSP-only JSFX. Prompt 13 strengthened the Python model contract, but the contract remains engineering scaffolding, not a runtime model path. No AI model changes should be made until a real inference backend, output type, shape contract, and dry fallback policy are implemented and tested through the audio path.
