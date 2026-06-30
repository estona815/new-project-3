# First Patch Plan

This plan is based on the actual repository. It does not assume a C++ `AudioProcessor`, APVTS, STFT engine, or model runtime exists.

Do not implement multiband, M/S, TDR Nova-style bands, new denoising, exciters, or clarity restoration in this sequence. The next patches must prevent destructive processing before making denoise stronger.

## Patch 1 - Lock Audit And Build/Test Baseline

- files to modify:
  - `VOCAL_CLARITY_REPAIR_SYSTEM/docs/*.md`
  - `tests/test_prompt11_signal_path_audit.py`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/eval/rc_qa.py`
- reason:
  - This is the current task: lock the real JSFX signal path and missing C++/model/STFT paths so future agents do not tune blindly.
- risk:
  - Documentation/test-only; no sound change.
- tests needed:
  - Direct Python test runner.
  - RC QA runner.

## Patch 2 - JSFX Fallback Tightening - completed in first safety patch

- files to modify:
  - `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`
  - `tests/test_vocal_ai_artifact_split_tamer_jsfx.py`
- reason:
  - Bad-input fallback now uses `last_safe_l/r` (`vocal_ai_artifact_split_tamer.jsfx:228-235`).
  - Suspicious drop/full-band collapse now dry-fallbacks (`:741-757`).
  - This is the first sound-path safety patch because it targets crash/invalid/destructive-output behavior, not tone improvement.
- risk:
  - Changed behavior only during bypass, DryWet=0, disabled, invalid, or suspicious fallback conditions.
- tests needed:
  - NaN/Inf cannot reach output.
  - Invalid single-sample spike does not blast or click beyond defined policy.
  - Bypass and processing-disabled remain dry.
  - Suspicious full-band collapse chooses dry fallback.

## Patch 3 - Parameter Drift Guard

- files to modify:
  - `VOCAL_CLARITY_REPAIR_SYSTEM/presets/factory_presets_safe_defaults.json`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/docs/parameter_freeze_table.md`
  - `tests/test_prompt8_preset_release_policy.py`
  - `tests/test_prompt11_signal_path_audit.py`
- reason:
  - JSFX slider defaults (`vocal_ai_artifact_split_tamer.jsfx:5-32`) and factory JSON (`factory_presets_safe_defaults.json:23-52`, `:107-112`) are the source of truth. They must remain synchronized.
- risk:
  - Documentation/test-only unless defaults are changed later.
- tests needed:
  - JSFX defaults equal Preserve preset.
  - Legacy preset sanitizer still preserves old in-range values (`preset_policy.py:60-70`).

## Patch 4 - Actual REAPER Render Harness

- files to modify:
  - `VOCAL_CLARITY_REPAIR_SYSTEM/eval/evaluation_harness.py`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/scripts/`
  - `tests/test_ab_quality_harness.py`
- reason:
  - The current harness can only use passthrough or externally supplied processed files (`evaluation_harness.py:77-93`). To verify source preservation, the system needs actual REAPER JSFX processed renders.
- risk:
  - Test infrastructure only, but depends on REAPER availability.
- tests needed:
  - Bypass render equals dry.
  - Processing disabled render equals dry.
  - Preserve preset does not heavily attenuate clean sine/vocal proxy.
  - Residual monitor can be captured for listening checks.

## Patch 5 - C++ processBlock Snapshot Only If C++ Plugin Appears

- files to modify:
  - NOT APPLICABLE in current repo.
- reason:
  - `processBlock`, `AudioProcessor`, and APVTS are NOT FOUND. A processBlock parameter snapshot cannot be implemented without inventing a new plugin architecture.
- risk:
  - Adding C++ scaffolding now would be a large architecture change and outside this safety audit.
- tests needed if future C++ exists:
  - Parameter snapshot read once per block.
  - No APVTS reads in inner loops.
  - No allocation/logging/file IO in processBlock.
  - Bypass and dry/wet bit-identical/near-identical tests.

## Patch 6 - STFT/Mask Numerical Safety - Prompt 13 partially completed

- files to modify:
  - `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/docs/stft_mask_model_safety.md`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/docs/manual_test_plan_prompt13.md`
  - `tests/test_prompt13_stft_mask_model_safety.py`
- reason:
  - STFT/FFT, FFT size, hop size, window, and overlap-add normalization are NOT FOUND in active JSFX and must not be invented in a safety patch.
  - Prompt 13 made the active mask-equivalent gain floor/collapse constants explicit without changing intended denoise strength.
- risk:
  - Adding STFT now would be a new algorithm and explicitly outside the task.
  - JSFX behavior should only change in extreme invalid/collapse conditions already guarded by dry fallback.
- tests needed if future STFT exists:
  - FFT size/hop/window explicit.
  - Overlap-add normalization.
  - Min gain based on MaxSuppressionDb.
  - No log(0), divide-by-zero, NaN, or Inf output.

## Patch 7 - Model Output Validation Contract - Prompt 13 completed for non-runtime contract

- files to modify:
  - `VOCAL_CLARITY_REPAIR_SYSTEM/ml/model_output_contract.py`
  - `tests/test_model_output_contract.py`
  - `tests/test_prompt13_stft_mask_model_safety.py`
- reason:
  - There is no model loading or inference runtime. The existing model contract validates future outputs but is not connected to audio.
  - Prompt 13 strengthened missing/ragged/shape/finite/extreme output validation, mask floors, residual RMS fallback, negative magnitude rejection, complex-pair validation, and suspicious waveform fallback.
- risk:
  - Adding inference now would be a new model feature and outside this safety audit.
  - Contract tests do not prove runtime model behavior until a real backend is wired through the contract.
- tests needed if future model exists:
  - Unknown output type rejected.
  - Shape mismatch dry fallback.
  - NaN/Inf output dry fallback.
  - Waveform output never directly replaces dry without blend/limits.

## Patch 8 - Conservative Soft Mask - Prompt 14 completed

- files modified:
  - `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/ml/model_output_contract.py`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/docs/conservative_soft_mask.md`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/docs/manual_test_plan_prompt14.md`
  - `tests/test_prompt14_conservative_soft_mask.py`
- reason:
  - The active JSFX already used soft probability/gain rather than hard masks. Prompt 14 made the broad presence/air caps explicit, locked nonlinear Amount and MaskStrength depth behavior in tests, and made full-band near-floor recovery more conservative.
  - The model contract now has reusable conservative soft-probability, bounded denoise-gain, spectral-subtraction, and full-band guard helpers for future integration tests.
- risk:
  - The JSFX behavior can become slightly less suppressive when two high bands sit at their floors; this is intentional preservation-first behavior.
  - No final vocal-quality claim is made without real REAPER renders.
- tests:
  - Soft probability and knee tests.
  - Amount/MaskStrength/MaxSuppression cap tests.
  - Frequency-cap tests.
  - Model-mask and spectral-subtraction safety tests.
  - Full-band guard tests.

## Patch 9 - Source Preserve Guards - Prompt 15 completed

- files modified:
  - `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/ml/model_output_contract.py`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/docs/source_preserve_guards.md`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/docs/harmonic_preserve_deferred.md`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/docs/manual_test_plan_prompt15.md`
  - `tests/test_prompt15_source_preserve_guards.py`
- reason:
  - Preserve controls already existed in the JSFX. Prompt 15 added `@sample` snapshots for source-preserve values, made transient/harmonic suppression-limit edits local per sample, and added future-integration helpers so model masks and spectral subtraction cannot bypass preserve floors.
  - Active JSFX tilt and air-loss guards remain attenuation-reduction guards, not EQ or exciters.
- risk:
  - The plugin can leave more noise/artifact residue in protected regions. This is intentional because the patch prioritizes source preservation over stronger cleanup.
  - Full F0 harmonic tracking remains deferred.
- tests:
  - Preserve default/snapshot tests.
  - Frequency preserve weight tests.
  - Suppression-limit, transient, harmonic, tilt, air, model-mask, and spectral-subtraction guard tests.

## Patch 10 - Residual Monitor And A/B Evaluation Foundation - Prompt 16 completed

- files modified:
  - `VOCAL_CLARITY_REPAIR_SYSTEM/eval/audio_metrics.py`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/eval/evaluation_harness.py`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/scripts/plugin_eval.py`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/docs/evaluation_harness.md`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/docs/residual_monitor.md`
  - `VOCAL_CLARITY_REPAIR_SYSTEM/docs/manual_test_plan_prompt16.md`
  - `tests/test_prompt16_residual_eval_foundation.py`
- reason:
  - This patch creates the measurement foundation for original/processed/residual comparison, level-matched A/B files, source-preservation metrics, transient metrics, residual leakage scoring, and JSON/Markdown reports.
  - It does not change the active denoise algorithm or preset behavior.
- risk:
  - Metrics are approximate and should be treated as warnings/fail gates, not as final audio truth.
  - Direct JSFX execution is still not available outside REAPER; real plugin renders must use the external-render path.
- tests:
  - Residual calculation tests.
  - RMS matching tests.
  - Band-energy placement tests.
  - Spectral tilt and transient metric tests.
  - Synthetic generator tests.
  - Offline evaluation output and metrics tests.
  - NaN/Inf metric detection tests.

## Recommended Next Command

Next prompt should move to real render validation or numerical mask/model-shape safety, without adding stronger denoise:

```text
Using the audit and first safety patch docs in VOCAL_CLARITY_REPAIR_SYSTEM/docs, implement the next safety-only validation patch. Do not change denoise strength, presets, EQ, model code, M/S logic, or multiband behavior. Focus on real REAPER render validation, residual checks, and numerical safety tests.
```
