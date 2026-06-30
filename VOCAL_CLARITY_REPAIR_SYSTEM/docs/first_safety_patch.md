# First Safety Patch

This patch is safety-only. It does not add denoise strength, EQ boost, exciter, model inference, STFT, new multiband behavior, or preset tuning.

## Files Changed

- `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`
- `tests/test_vocal_ai_artifact_split_tamer_jsfx.py`
- `tests/test_prompt12_first_safety_patch.py`
- `VOCAL_CLARITY_REPAIR_SYSTEM/docs/signal_path.md`
- `VOCAL_CLARITY_REPAIR_SYSTEM/docs/realtime_safety_audit.md`
- `VOCAL_CLARITY_REPAIR_SYSTEM/docs/risk_register.md`
- `VOCAL_CLARITY_REPAIR_SYSTEM/docs/first_safety_patch.md`

## Defaults Unified

No default value was changed. The preservation-first defaults remain:

- Amount: `30%`
- Dry/Wet: `70%`
- Max Reduction: `8 dB`
- Detector Attack: `50 ms`
- Detector Release: `12 ms`
- Processing Enabled: `On`
- Mask Strength: `0.35`
- Bypass: `Off`
- Multiband Mode: `Preserve`
- Residual Monitor: `Off`

The source of truth remains the JSFX slider definitions and the factory preset JSON, locked by tests. Existing preset compatibility is unchanged.

## Snapshot Added

There is no C++ `processBlock` in this repository. The JSFX equivalent was added at the start of `@sample`:

- `snap_wet`
- `snap_bypass`
- `snap_processing_enabled`
- `snap_mapped_amount`
- `snap_attack_amt`
- `snap_sandy_amt`
- `snap_fizz_amt`
- `snap_tail_amt`
- `snap_body_amt`
- `snap_mask_strength`
- `snap_min_gain`
- `snap_residual_monitor`
- `snap_out_gain`

These are stack-style JSFX sample variables and do not allocate, log, lock, call UI, or mutate a parameter tree.

## Fallback Conditions

- Bad input: output previous stable safe sample.
- Bypass: return dry before filterbank/denoise processing.
- DryWet = 0: return dry before filterbank/denoise processing.
- Processing disabled: return dry before filterbank/denoise processing.
- Bad processed output: dry fallback.
- Suspicious RMS drop: dry fallback.
- Full-band collapse: dry fallback.
- Bad final output: dry fallback.

## Bypass Behavior

Plugin bypass now returns dry before destructive processing and resets wet smoothing. Host bypass remains separate and still requires DAW validation.

## DryWet Behavior

DryWet = 0 now returns dry before filterbank/denoise processing. Successful processing still uses:

```text
output = dry + (processed - dry) * wet_state
```

## Model Not Ready Behavior

No active model runtime exists in this plugin. `Processing Enabled = Off` is the current safe runtime equivalent and returns dry.

## Known Limitations

- There is still no C++ `processBlock`, APVTS, STFT, or model runtime.
- Bad input before any previous stable sample can still output the zero-initialized last-safe state.
- Automated tests are static/math/direct Python tests; actual REAPER processed render validation remains required.
- This patch does not claim improved vocal clarity or better denoising.

## Tests Added

- Static tests for JSFX snapshot variables.
- Static tests that bypass, DryWet=0, and processing-disabled dry branches occur before filterbank processing.
- Static tests that bad input uses last stable safe output instead of hard zero.
- Static tests and docs checks for first safety patch reporting.

## Next Recommended Patch

Prompt 13 should focus on actual REAPER render validation and numerical safety around mask/gain behavior, without adding stronger denoise or clarity restoration.
