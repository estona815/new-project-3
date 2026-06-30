# STFT / Mask / Model Safety

Prompt 13 result: safety-only patch. It does not add denoise strength, EQ boost, exciter, soft-mask redesign, new AI inference, preset tuning, new M/S logic, or new multiband DSP.

## Implementation Note

- STFT/FFT file: NOT FOUND in the active plugin path.
- Mask/gain calculation file: `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`.
- Model inference output file: runtime NOT FOUND; future validation contract is `VOCAL_CLARITY_REPAIR_SYSTEM/ml/model_output_contract.py`.
- Overlap-add/reconstruction file: active STFT overlap-add NOT FOUND; JSFX reconstructs by summing bounded time-domain filterbank bands.
- Fallback function from Prompt 12: JSFX `@sample` dry fallback branches for bypass, DryWet=0, disabled processing, bad processed output, suspicious drop/full-band collapse, and bad final output.
- Relevant tests available: `tests/test_vocal_ai_artifact_split_tamer_jsfx.py`, `tests/test_model_output_contract.py`, `tests/test_prompt12_first_safety_patch.py`, `tests/test_prompt13_stft_mask_model_safety.py`, and `VOCAL_CLARITY_REPAIR_SYSTEM/eval/rc_qa.py`.

## STFT/FFT Safety

Active plugin STFT configuration:

- FFT size: NOT FOUND.
- Hop size: NOT FOUND.
- Overlap ratio: NOT FOUND.
- Window type: NOT FOUND.
- Analysis window: NOT FOUND.
- Synthesis window: NOT FOUND.
- Overlap-add normalization: NOT FOUND.
- Frame/ring buffer size: NOT FOUND.
- Frequency-bin count: NOT FOUND.
- STFT latency: metadata reports `0` because no runtime STFT exists.

This is not a missing implementation in this patch. Adding STFT would be a new denoise algorithm path, which is explicitly out of scope. The active JSFX path is per-sample time-domain filterbank DSP and has no ring buffer, hop-size dependency, FFT buffer, or overlap-add state to initialize.

Initialization guard:

- JSFX state is initialized in `@init`.
- Sample-rate-derived coefficients are computed from `srate` with `sr_safe = max(srate, 1000)`.
- There is no STFT state that can be partially initialized.
- If a future STFT path is added, it must dry-fallback when state is not ready and must validate FFT size, hop size, window length, bin count, and OLA normalization before audio processing.

## Mask/Gain Safety

Active mask equivalent:

- The JSFX uses soft detector probabilities and bounded gains, not hard STFT bin masks.
- Clamp range: normal gains are clamped to per-band minimum gain through `Max Reduction (dB)` and to `1.0`.
- minGain source: `slider10` `Max Reduction (dB)` creates the global floor, with stricter per-band floors for attack, sandy, fizz, air, and M/S grouped bands.
- Prompt 13 constants made explicit:
  - `mask_floor_ratio = 1.122018`, within 1 dB of a per-band floor.
  - `suspicious_drop_power_ratio = 0.0158489`, -18 dB RMS-drop guard as a power ratio.
  - `collapse_gain_floor = 0.398107`, -8 dB active-spectrum average-gain guard.
  - `mb_collapse_gain_floor = 0.50`.
- Full-band collapse safety: if too many high-band gains sit near floor, if average gain is too low, or if M/S average gain is too low, the path returns dry instead of a reduced-wet processed signal.

Spectral subtraction handling:

- No active spectral subtraction path was found.
- No active code subtracts noise magnitude from STFT bins.
- Future spectral subtraction must floor processed magnitude by `inputMagnitude * minGain` and must reject negative/non-finite magnitudes before audio use.

## Magnitude/Phase Safety

Active plugin:

- No active STFT magnitude/phase calculation exists.
- Existing JSFX nonlinear math uses `eps = 1.0e-8` style protection for logs and denominators.
- Processed and final outputs are checked for NaN/Inf/huge values before reaching the host.

Future STFT requirement:

- Use epsilon before `log`, division, and gain derivation.
- Clamp every mask/gain to `[minGain, 1.0]`.
- Reject non-finite frames and dry-fallback instead of attempting partial reconstruction.

## Model Output Validation

Active runtime:

- Model loading: NOT FOUND.
- Model inference call: NOT FOUND.
- Runtime tensor output: NOT FOUND.
- Invalid runtime model fallback: NOT APPLICABLE because no model runtime exists.

Contract strengthened in `model_output_contract.py`:

- Missing output is rejected.
- Ragged tensor-like output is rejected.
- Expected output shape is checked before use.
- Non-numeric, empty, NaN, and Inf outputs are rejected.
- Absurd model values over `SafetyConfig.max_abs_model_value` are rejected.
- GainMask and ComplexMask are floored to `min_model_gain(freq, config)` instead of allowing destructive zero masks.
- NoiseProbabilityMask is clamped to `0..1` and remains advisory.
- ResidualEstimate must match input length and now falls back if residual RMS exceeds the safety budget.
- MagnitudeEstimate rejects negative magnitudes and clamps effective gain to `minGain..1`.
- ComplexMask requires real/imag pairs.
- Waveform must match input length and now falls back if output RMS ratio is outside the configured safety range.
- Unknown output type remains invalid.

Invalid output behavior:

- Contract returns model confidence `0.0`.
- Contract preserves the DSP probability path instead of trusting the model output.
- Contract returns bounded gain and finite values.

## Tests Added

- Prompt 13 doc coverage and architecture non-guessing checks.
- JSFX safety-constant and full-band fallback checks.
- Model contract tests for missing/ragged/wrong-shape/non-finite/extreme outputs.
- Mask floor tests for all-zero gain masks.
- Residual, magnitude, complex mask, and waveform suspicious-output fallback tests.

## Remaining Limitations

- No active STFT/iSTFT passthrough test can be added because no active STFT/iSTFT exists.
- No runtime model-output fallback can be host-tested because no model runtime exists.
- RC QA uses static/direct Python checks and synthetic passthrough release checks; it does not execute REAPER JSFX audio in-process.
- Real REAPER renders, residual listening, clean vocal preservation checks, and block-size/sample-rate DAW matrix remain required before any audio-quality claim.
