# Risk Register

| ID | Priority | Area | Description | Evidence | Proposed Issue | Blocking? |
|---|---|---|---|---|---|---|
| R-001 | P1 | Invalid output | Reduced in first safety patch: bad input NaN/Inf/huge values no longer hard-zero after a stable sample; the plugin outputs `last_safe_l/r`. First invalid sample can still resolve to zero-initialized last-safe state. | `vocal_ai_artifact_split_tamer.jsfx:228-235` | Host-test invalid spikes and decide whether held-safe state needs fade smoothing. | Blocks final release validation. |
| R-002 | P0 | Build/release | Root CMake build cannot be attempted locally because `cmake` is unavailable; root CMake also references missing analyzer files. | `CMakeLists.txt:5-14`, local command `cmake: command not found`, `analyzer/` NOT FOUND | Separate JSFX release QA from missing analyzer/C++ build, or restore build tree. | Blocks binary plugin claims. |
| R-003 | P0 | CI/release | GitHub workflows reference a missing `plugin/` project and `scripts/package_plugin.py`. | `.github/workflows/build-macos.yml:45-65`, `build-windows.yml:45-67`, `build-linux.yml:89-112`; `plugin/` NOT FOUND | Align workflows with current JSFX package or add plugin project. | Blocks CI artifact claims. |
| R-004 | P0 | processBlock safety | C++ `processBlock` is NOT FOUND, so C++ audio-thread safety cannot be certified. | Repository search for `processBlock` and `AudioProcessor` found docs/tests only. | If C++ source appears, first patch must add parameter snapshot and no-allocation audit. | Blocking for VST3/AU/AAX. |
| R-005 | P0 | Model output | Active plugin still has no model validation path because there is no active model path. Prompt 13 reduced future-integration risk by strengthening the contract for missing/ragged/shape/finite/extreme outputs, destructive gain masks, residual RMS, negative magnitudes, odd complex masks, and suspicious waveform RMS. | Runtime model NOT FOUND; contract at `model_output_contract.py:262-497`. | Do not add model inference without contract-enforced validation and dry fallback. | Blocking for AI inference claims. |
| R-006 | P1 | Destructive full-band suppression | Reduced in first safety patch: suspicious RMS drop/full-band collapse now returns dry instead of 25% wet processing. Prompt 13 made the floor/collapse constants explicit. Prompt 14 tightened the near-floor high-band guard from three bands to two bands before blending toward dry. Real render validation is still missing. | `vocal_ai_artifact_split_tamer.jsfx:44-56`, `:425-435`, `:754-755` | Run actual REAPER A/B renders and residual listening. | Blocks audio-quality approval. |
| R-007 | P1 | Vocal presence loss | Further reduced in Prompt 15: VocalPreserve/ClarityPreserve are now included in the `@sample` snapshot, future model/spectral helpers apply source-preserve weights before gain floors, and the active JSFX tilt guard blends over-reduced presence toward dry. Broad detector decisions can still reduce presence/consonants if source is misdetected. | `vocal_ai_artifact_split_tamer.jsfx:237-242`, `:354-389`, `:447-455`; `model_output_contract.py` preserve helpers | Clean vocal and residual-listening tests. | Blocks quality approval. |
| R-008 | P1 | Air loss | Further reduced in Prompt 15: AirPreserve is snapshotted, the active JSFX air-loss guard uses the snapshot, and future model/spectral helpers apply air preserve before gain floors. Tail warble logic can still remove ambience/air if detector is wrong. | `vocal_ai_artifact_split_tamer.jsfx:237-242`, `:459-467`; `model_output_contract.py` air weight/helper | Dedicated air/ambience preservation test. | Blocks quality approval. |
| R-009 | P1 | Transient smear | Further reduced in Prompt 15: TransientPreserve is snapshotted and transient/harmonic suppression-limit reductions now use local per-sample limits instead of mutating global band limits. Real transients still need host validation. | `vocal_ai_artifact_split_tamer.jsfx:331-367`, `:398-419` | Transient test set with residual check. | Blocks quality approval. |
| R-010 | P1 | Stereo collapse | M/S side attenuation can narrow side ambience if detector is wrong. | `vocal_ai_artifact_split_tamer.jsfx:416-545`, `:637-649` | Stereo-width A/B and mono compatibility tests. | Blocks quality approval. |
| R-011 | P1 | Residual ghost vocal | Partially addressed in Prompt 16: residual monitor behavior is documented, the harness writes `residual.wav`, and metrics now report residual presence/clarity/air ratios plus source-leakage score. Real JSFX render residual listening is still required. | Residual monitor `vocal_ai_artifact_split_tamer.jsfx:733-740`; harness residual files `evaluation_harness.py`; `docs/residual_monitor.md` | Use real REAPER render outputs in A/B harness. | Blocks quality approval. |
| R-012 | P2 | Missing local pytest | `python3 -m pytest` fails because pytest is unavailable. | Local command result: `No module named pytest`. | Use direct RC runner or install test dependencies. | Not blocking docs; blocks pytest workflow. |
| R-013 | P2 | No direct JSFX execution harness | Partially addressed in Prompt 16: Python A/B harness now has documented single-file, synthetic, and external-render entry points, but it still cannot execute JSFX directly outside REAPER. | `evaluation_harness.py`; `scripts/plugin_eval.py`; `docs/evaluation_harness.md` | Add REAPER batch render integration or fixture outputs. | Blocks automated audio claims. |
| R-014 | P2 | Sample-rate behavior | Coefficients are computed with `srate`, but no host sample-rate reset test through REAPER is automated. | `vocal_ai_artifact_split_tamer.jsfx:188-204` | REAPER matrix at 44.1/48/88.2/96 kHz. | Blocks DAW matrix. |
| R-015 | P2 | Block-size behavior | Active JSFX is per-sample, but host block-size tests are simulated/static, not actual REAPER engine render. | `@sample` `vocal_ai_artifact_split_tamer.jsfx:207-794`; RC block list `rc_qa.py:56-57` | REAPER render matrix over block sizes. | Blocks DAW matrix. |
| R-016 | P3 | Preset ABI | Existing JSFX slider order is the preset/session ABI. | JSFX sliders `vocal_ai_artifact_split_tamer.jsfx:5-32`; legacy policy `factory_presets_safe_defaults.json:16-22` | Append-only parameter policy. | Blocks unsafe parameter edits. |
| R-017 | P3 | Product naming | Current runtime is DSP-only while product language may imply AI model inference. | `release/rc_metadata.json:19-26`; model runtime NOT FOUND | Release copy must say DSP-only unless model is added. | Blocks marketing/release wording. |
| R-018 | P3 | Unvalidated formats | Metadata lists VST3/AU/AAX/Standalone as unvalidated. | `release/rc_metadata.json:8-10`, `:49-54` | Do not ship those formats from this repo without actual build. | Blocks non-JSFX release. |

## Prompt 13 Reduced Risks

- NaN/Inf mask/model output: reduced in the Python model contract by rejecting non-finite model outputs before advisory gain calculation.
- Invalid tensor shape crash: reduced in the contract by rejecting missing, ragged, wrong-shape, and odd complex-mask outputs.
- Full-bin zeroing: reduced for future GainMask/ComplexMask handling by flooring masks to `min_model_gain`; active JSFX has no STFT bins.
- Negative magnitude: reduced in the contract by rejecting negative MagnitudeEstimate values.
- Uninitialized STFT: documented as not applicable to the active JSFX path because no STFT state exists; any future STFT path must add dry fallback before use.
- Model output shape crash: reduced in contract tests, still not runtime-tested because no model runtime exists.

## Prompt 14 Reduced Risks

- Hard mask / bin zeroing: active JSFX path is documented and tested as soft probability plus bounded gain; no STFT bin-zero path was found.
- Excessive default suppression: high-band caps are now named constants, with presence capped at 4 dB and fizz/air at 3 dB before existing guards.
- Linear aggressive Amount: nonlinear `amount^1.6` remains locked by tests.
- Model mask direct destructive application: contract tests verify model masks are advisory and cannot directly mute source.
- Spectral subtraction negative magnitude: no active path found; future helper/test floors magnitude and clamps effective gain.
- Full-band near-floor collapse: guard now blends toward dry when two high bands are near floor, and dry-fallback remains for suspicious broad collapse.

## Prompt 15 Reduced Risks

- Vocal presence loss: reduced by snapshotted VocalPreserve/ClarityPreserve controls, frequency preserve weights, and protected suppression limits.
- Consonant loss: reduced by clarity weighting around the 4 kHz to 8 kHz region and transient-aware suppression-limit reduction.
- Air loss: reduced by AirPreserve snapshot use, air weighting around 8 kHz+, and the air-loss guard.
- Transient smearing: reduced by transient-score protection and target-gain safeguards that avoid sudden extra attenuation during attack frames.
- Harmonic removal: partially reduced by the existing internal harmonic proxy and future contract helper; full F0 harmonic tracking is explicitly deferred.
- Spectral darkening: reduced by the existing spectral tilt guard, now documented and tested as source-preservation behavior.
- Residual source leakage: residual monitor remains available for listening/debug; automated source-leakage warning remains a future render-harness task.

## Prompt 16 Reduced Risks

- No residual monitoring: reduced by documenting the plugin monitor convention and harness residual file convention.
- No clean-input do-no-harm testing: reduced by synthetic sine, harmonic stack, impulse, and source-proxy generated assets.
- No source-preservation metrics: reduced by presence, clarity, air, spectral tilt, transient, residual leakage, and safety metrics in `metrics.json`.
- No A/B level matching: reduced by `processed_matched.wav` and `match_gain_db` reporting.
- Clean but low-quality result passing unnoticed: reduced by residual listening reports, source-leakage score, and warning/failure tags.
- Direct JSFX execution is still unresolved; external REAPER renders remain required for true plugin-output validation.
