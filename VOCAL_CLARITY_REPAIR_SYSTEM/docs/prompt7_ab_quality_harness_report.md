# Prompt 7 A/B Quality Harness Report

## Repository Audit

| File | Function/script | Current role | Missing capability | Patch needed |
| --- | --- | --- | --- | --- |
| `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx` | JSFX `@sample` | Actual REAPER plugin path with preservation-first DSP and residual monitor. | Cannot be instantiated directly from Python without REAPER. | Evaluate rendered WAVs or passthrough synthetic CI output; do not add DSP in Prompt 7. |
| `tools/*vocal_clarity*.py` | offline render scripts | Project-specific REAPER/audio render utilities. | Not a reusable plugin evaluation harness. | Add separate manifest-driven A/B evaluator. |
| `tests/test_*` | direct Python tests | Static and math regression checks for JSFX, prompt assets, model contract. | No audio A/B metrics or residual scoring. | Add synthetic audio evaluation tests. |
| `CMakeLists.txt` | analyzer target | References missing analyzer sources. | No buildable plugin test binary here. | Do not rely on CMake for Prompt 7. |
| `.github/` | CI area | Present but no confirmed audio eval workflow in this patch. | No lightweight synthetic eval command documented. | Provide CI-safe command and tests. |

## Implemented Harness

New modules:

- `VOCAL_CLARITY_REPAIR_SYSTEM/eval/audio_metrics.py`
- `VOCAL_CLARITY_REPAIR_SYSTEM/eval/synthetic_assets.py`
- `VOCAL_CLARITY_REPAIR_SYSTEM/eval/evaluation_harness.py`

The harness can:

- load a manifest
- generate CI-safe synthetic WAV assets
- read original and externally rendered processed WAVs
- run passthrough synthetic smoke evaluation when no plugin renderer is available
- write `processed.wav`, `processed_matched.wav`, `residual.wav`
- compute level, band, darkening, transient, residual leakage, and stereo metrics
- generate per-item `metrics.json` and `report.md`
- generate run-level `run_metrics.json` and `index.md`
- fail with `--fail-on-damage` when severe source damage is detected

## Renderer Strategy

Current renderer modes:

- `passthrough`: CI-safe do-no-harm and report smoke mode. No new DSP is added.
- `external`: evaluates already rendered plugin output from a processed directory or per-manifest `processed_path`.

This project has no direct C++ processor instantiation and no command-line JSFX runner. REAPER can still be used to render plugin outputs, then this harness evaluates those WAVs.

## Metrics

Implemented:

- input/processed RMS
- RMS delta dB
- peak and clipping count
- DC offset
- active frame detection
- gap/noise reduction estimate
- band energies for sub, low_mid, body, nasal, presence, clarity, air, full
- active-frame band deltas
- presence loss
- clarity loss
- air loss
- spectral tilt loss
- transient count / flux / peak loss
- residual source leakage score
- residual/input correlation
- mid/side stereo width and L/R correlation
- preservation-weighted scoring
- failure tags such as `vocal_presence_loss`, `consonant_loss`, `air_loss`, `transient_smear`, `residual_ghost_vocal`, `stereo_collapse`, `clipping`, `nan_inf`, `clean_input_damage`

## Manifest

`VOCAL_CLARITY_REPAIR_SYSTEM/audio_tests/manifest.json` documents the local private-asset structure. Large audio assets are not committed.

Synthetic CI assets can be generated with:

```sh
python3 -m VOCAL_CLARITY_REPAIR_SYSTEM.eval.evaluation_harness \
  --generate-synthetic VOCAL_CLARITY_REPAIR_SYSTEM/audio_tests/generated \
  --preset Preserve \
  --output-dir eval_outputs/synthetic_preserve
```

## Manual Evaluation Protocol

For each file:

1. Listen to original.
2. Listen to processed loudness-matched.
3. A/B quickly.
4. Listen to residual.
5. Fail if residual contains ghost vocal, consonants, harmonic body, attacks, musical air, or source room tail.
6. Prefer moderate remaining noise over a cleaner but lower-fidelity source.

## Limitations

- No direct plugin processor test binary exists.
- JSFX offline rendering still requires REAPER or pre-rendered outputs.
- No real vocal/AI-artifact assets were committed.
- Plots are deferred; reports are JSON and Markdown.
- CPU timing of the actual plugin is deferred until a direct renderer exists.

