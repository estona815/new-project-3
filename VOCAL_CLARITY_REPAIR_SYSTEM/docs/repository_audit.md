# Repository Audit

Scope: Prompt 11 signal-path audit only. No DSP, preset, model, UI, or sound-changing code was modified.

Headline finding: No C++ `AudioProcessor` class, No APVTS, and No model loading or inference runtime exist in the active repository path.

Searches performed: `rg "processBlock|prepareToPlay|releaseResources|AudioProcessor"`, `rg "AudioProcessorValueTreeState|APVTS|createParameterLayout"`, `rg "mask|threshold|suppression|noise|denoise|STFT|FFT"`, `rg "model|inference|tensor|onnx|torch|tflite"`, `rg "dry|wet|mix|bypass"`, and direct inspection with `nl -ba`.

## Project Structure

| Path | Purpose | Evidence | Risk |
| --- | --- | --- | --- |
| `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/` | REAPER JSFX audio processors. The actual plugin entry point is `vocal_ai_artifact_split_tamer.jsfx`. | `vocal_ai_artifact_split_tamer.jsfx:1-37`, `release/rc_metadata.json:8-11` | Host-interpreted JSFX; no standalone plugin binary in this package. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/presets/` | Factory preset and release policy JSON. | `factory_presets_safe_defaults.json:1-22`, `:23-52`, `:107-112` | JSON and JSFX slider defaults can drift. Existing tests cover this. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/ml/` | Future model output contract and Python validation helpers. | `model_output_contract.py:9-36`, `:240-407` | Contract only; not active real-time inference. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/eval/` | Python QA, preset validation, A/B metrics, release gate, RC runner. | `evaluation_harness.py:77-93`, `rc_qa.py:39-55`, `preset_policy.py:60-70` | A/B harness uses passthrough/external WAVs, not direct JSFX rendering. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/scripts/` | REAPER/Lua and QA helper scripts. | `scripts/run_rc_qa.sh:1-9` | Requires REAPER or local Python for full validation. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/docs/` | Product, QA, release, and handoff documentation. | Existing docs directory contains `signal_path.md`, `known_risks.md`, `developer_handoff_master.md`. | Needs current audit docs to keep future patches evidence-based. |
| `.github/workflows/` | CI workflows for a separate/expected `plugin/` CMake/JUCE project. | `.github/workflows/build-macos.yml:45-65`, `build-windows.yml:45-67`, `build-linux.yml:89-112` | Referenced `plugin/` directory is NOT FOUND in this checkout. |
| Root `CMakeLists.txt` | C++ analyzer build definition, not the JSFX plugin. | `CMakeLists.txt:1-34` | References `analyzer/*` and `tests/test_mastering_qa_analyzer.cpp`, both NOT FOUND in this checkout. |

## Build System

- Build tool found: root `CMakeLists.txt` (`CMakeLists.txt:1-34`) and GitHub Actions CMake workflows (`.github/workflows/build-macos.yml:45-65`, `.github/workflows/build-windows.yml:45-67`, `.github/workflows/build-linux.yml:89-112`).
- Actual active plugin format in this repository: REAPER JSFX (`release/rc_metadata.json:8-11`).
- Unvalidated formats: VST3, AU, AAX, Standalone are explicitly not validated here (`release/rc_metadata.json:8-10`, `:49-54`).
- CI workflows expect `plugin/`, `cmake/`, and `scripts/package_plugin.py`; these are NOT FOUND in the current checkout.
- Local build attempt: `cmake -S . -B /tmp/codex_new_project3_audit_build` failed with `cmake: command not found`.
- Pytest attempt: `python3 -m pytest tests/test_vocal_ai_artifact_split_tamer_jsfx.py` failed with `No module named pytest`.
- Working test command in this repo: `python3 -m VOCAL_CLARITY_REPAIR_SYSTEM.eval.rc_qa --output-dir <dir>` via `scripts/run_rc_qa.sh:1-9`.
- Required model/resource files: no model file is required in current metadata (`release/rc_metadata.json:19-26`).

## Main Plugin Classes

NOT FOUND: No C++ `AudioProcessor` class.

Searched for `AudioProcessor`, `processBlock`, `prepareToPlay`, `releaseResources`, `AudioProcessorValueTreeState`, `APVTS`, and `createParameterLayout`. Matches were documentation/test references, not implementation files.

| File | Function / Section | Responsibility | Risk | Patch Needed |
| --- | --- | --- | --- | --- |
| `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx` | JSFX `slider1`-`slider28`, lines `5-32` | Host-visible parameter definitions and fresh JSFX defaults. | Slider order is preset/session ABI. | Only append new sliders; never reorder. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx` | `@init`, lines `39-61` | DSP constants and persistent filter/envelope/gain state. | State resets depend on host lifecycle, not `prepareToPlay`. | Future docs/tests should define host reload behavior. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx` | `@slider`, lines `63-204` | Parameter clamp, derived coefficients, thresholds, mode caps. | No immutable block snapshot because JSFX has sample-level globals. | Equivalent snapshot is only needed for future C++ processor. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx` | `@sample`, lines `207-794` | Actual real-time audio path. | Destructive source removal can occur in detector/gain logic before dry fallback triggers. | Continue validating with real REAPER renders. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/ml/model_output_contract.py` | `postprocess_model_output`, lines `240-407` | Future model-output validation contract. | Not connected to audio path; could be mistaken for active inference. | Keep documented as non-runtime contract. |

## Current Tests

| Test File | Coverage | Evidence | Gap |
| --- | --- | --- | --- |
| `tests/test_vocal_ai_artifact_split_tamer_jsfx.py` | Static JSFX safety/slider behavior. | References slider order and guards, e.g. `test_legacy_slider_order_is_preserved_for_existing_presets`. | Does not execute REAPER audio engine. |
| `tests/test_model_output_contract.py` | Python model contract validation. | Exercises `model_output_contract.py`. | Contract is not active plugin path. |
| `tests/test_ab_quality_harness.py` | A/B evaluation helpers. | `evaluation_harness.py:77-93`, `:171-255` | Renderer is `passthrough` or `external`; no direct JSFX render. |
| `tests/test_prompt8_preset_release_policy.py` | Factory defaults and preset policy. | Tests JSFX defaults against JSON. | Does not validate DAW preset migration in REAPER. |
| `tests/test_prompt9_rc_qa_lock.py` | RC QA/static release lock. | `rc_qa.py:39-55`, `:154-183` | Static and synthetic checks only. |
| `tests/test_prompt10_developer_handoff.py` | Handoff docs remain present and internally consistent. | `tests/test_prompt10_developer_handoff.py:34-53` | Prompt 11 audit detail was not previously locked. |

Test command situation:

- `python3 -m pytest ...`: unavailable because `pytest` is not installed.
- `python3 -m VOCAL_CLARITY_REPAIR_SYSTEM.eval.rc_qa --output-dir <dir>`: available direct runner.

Coverage gaps:

- No direct compiled `processBlock` unit test because there is no C++ plugin source.
- No REAPER-hosted automated render in CI.
- No pluginval coverage for this JSFX package.
- No clean-input audio regression using the actual JSFX engine in this workspace.

## Current Documentation

Existing useful docs include `developer_handoff_master.md`, `signal_path.md`, `known_risks.md`, `testing_plan.md`, `preset_policy.md`, and release docs. Missing before this task: dedicated `parameter_audit.md`, `model_path_audit.md`, `realtime_safety_audit.md`, `risk_register.md`, and `first_patch_plan.md`.

## Immediate Risks

P0 - crash / invalid output / destructive audio:

- Bad input NaN/Inf path now outputs the previous stable safe sample (`vocal_ai_artifact_split_tamer.jsfx:228-235`). The first invalid sample can still resolve to zero-initialized last-safe state.
- Full-band collapse now dry-fallbacks instead of lowering wet to 25% (`vocal_ai_artifact_split_tamer.jsfx:741-757`).
- CI CMake workflows reference missing `plugin/` sources; package build is not reproducible from this checkout.

P1 - source preservation / quality:

- Denoise decisions are broad time-domain detector/gain decisions, not a trained AI model or STFT mask (`vocal_ai_artifact_split_tamer.jsfx:300-325`, `:467-545`).
- Air/presence/transient guards exist, but they need real rendered A/B verification (`vocal_ai_artifact_split_tamer.jsfx:290-298`, `:382-407`, `:637-649`).
- Strong mode exists and is intentionally not default (`factory_presets_safe_defaults.json:82-90`, `:178-194`).

P2 - testing / evaluation:

- Pytest is missing locally.
- REAPER render validation is not automated here.
- A/B harness needs external processed WAVs for real plugin output (`evaluation_harness.py:77-93`).

P3 - UX / presets / release:

- Parameter naming is JSFX slider-based, not a custom UI/APVTS layout.
- Existing presets rely on exact slider order (`factory_presets_safe_defaults.json:16-22`).
- Current package is REAPER JSFX only; VST3/AU/AAX claims are explicitly unvalidated (`release/rc_metadata.json:8-10`).

## Issue Links

- Issue 0.1 - Repository architecture and signal-path audit: completed by this document set.
- Issue 0.2 - Build and test baseline: partially blocked by missing `cmake` and missing `pytest`; RC QA runner remains available.
- Issue 1.1 - Parameter default unification: mostly implemented for JSFX/JSON, but must remain first safety patch for any future C++ port.
- Issue 1.2 - Add processBlock parameter snapshot: NOT APPLICABLE until a C++ `processBlock` exists.
- Issue 1.4 - Safe fallback behavior: still relevant in JSFX for bad-input and suspicious-collapse behavior.
