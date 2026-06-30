# Prompt 5 M/S Dynamic Multiband DSP Report

## Repository Signal Path Audit

| File | Class/Module | Function/Section | Current role | Risk | Patch needed |
| --- | --- | --- | --- | --- | --- |
| `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx` | JSFX processor | `@sample` | Actual installed REAPER audio path. Performs dry copy, soft artifact probabilities, band attenuation, dry/wet, fallback, NaN checks. | No C++ `processBlock`, APVTS, STFT, or model inference path exists in this workspace. | Implement Prompt 5 in JSFX, preserving existing fallback and dry/wet behavior. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx` | Parameter block | `slider1`-`slider19`, `@slider` | Existing preservation-first defaults and guards. | Existing presets depend on slider order. | Append new parameters after slider19 only. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx` | Existing denoise path | soft-knee probability and band gains | Conservative time-domain equivalent of a soft mask. | Further suppression can stack into dullness. | Add total attenuation budget and reuse guards. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/docs/reaper_ai_artifact_multiband_prototype.md` | DAW prototype | band decision table | Prompt 4 design source for M/S and residual validation. | Prototype was design-only. | Port only conservative parts. |
| `tests/test_vocal_ai_artifact_split_tamer_jsfx.py` | Static/math tests | JSFX safety tests | Guards against destructive defaults and preset breakage. | Needs Prompt 5 coverage. | Add M/S, band-count, budget, residual tests. |

## Chosen Architecture

Chosen path: time-domain dynamic EQ/filter-bank style JSFX implementation.

Reason: the current project has no C++ plugin source, no `processBlock`, no APVTS, no model inference code, and no stable STFT implementation to extend. The only actual REAPER plugin path is the installed JSFX. Prompt 5 was therefore implemented as a bounded JSFX M/S dynamic multiband suppressor that extends the existing Prompt 1-3 safety system.

## New Parameters

Added after existing sliders to avoid breaking old preset values:

- `Multiband Enabled`, default on
- `M/S Enabled`, default on
- `Multiband Mode`, default `Preserve`
- `Mid Amount`, default `0.25`
- `Side Amount`, default `0.40`
- `Side Artifact Reduction`, default `0.45`
- `Surgical Artifact Reduction`, default `0.25`
- `Residual Monitor`, default off
- `Mid Preserve`, default `0.85`

## Band Modes

The JSFX uses the existing lowpass-derived grouped bands and processes them independently in Mid and Side:

- Preserve: 14 grouped lanes, default
- Balanced: 28 complexity target
- Surgical AI: 48 complexity target with sparse surgical weighting
- Strong Test: 64 cap, not default

This is not a static notch forest. The active JSFX implementation remains bounded and grouped because the project currently has no safe 64-filter C++ DSP framework.

## M/S Convention

```text
mid  = 0.5 * (left + right)
side = 0.5 * (left - right)
left = mid + side
right = mid - side
```

Dry/wet still blends against the original L/R input. Bypass and processing-disabled paths still output dry.

## Preservation Guards

The M/S suppressor reuses:

- vocal preserve
- clarity preserve
- air preserve
- transient score
- harmonic proxy
- spectral tilt guard
- air loss guard
- full-band collapse guard

Mid uses stronger protection than Side. Side has a width-loss guard that blends side gains back toward dry if stereo energy collapses.

## Residual Monitor

Residual monitor is optional and off by default.

Convention:

```text
residual = dry input - processed before dry/wet
```

Processed monitor outputs the processed-before-dry/wet signal. Bypass and fallback ignore monitor mode and remain dry-safe.

## Total Attenuation Budget

The multiband path adds budget floors:

- Preserve presence budget: about 1.5 dB for 2-8 kHz
- Preserve air budget: about 2.0 dB for 8 kHz+
- wider budgets only in non-default modes

If the existing soft mask already used the budget, the multiband gain is blended back toward 1.0 instead of stacking more loss.

## CPU and Latency

CPU impact is bounded: no allocations, no loops over unbounded bands, no file IO, no logging, no locks, and no model loading in the audio path. Latency remains unchanged because the implementation is time-domain and uses existing one-pole band splits and envelope smoothing.

## Deferred Risks

- No true STFT-bin 64-band implementation exists yet.
- No manual A/B or residual listening was performed in this patch.
- JSFX static tests validate structure and math behavior, but they do not replace listening tests.
- If a future C++ plugin source appears, this JSFX logic should be ported into a real `DynamicMultibandSuppressor` class with prepared filter state and runtime DSP tests.
