# Prompt 8 Preset And Release Policy

## Repository Audit

| File | Class/function | Current role | Current default | Risk | Patch needed |
| --- | --- | --- | --- | --- | --- |
| `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx` | JSFX `@slider`, `@sample` | Actual installed audio path. There is no C++ `AudioProcessor`, APVTS, or plugin UI in this repository. | Preserve-style JSFX defaults: Amount 30%, Dry/Wet 70%, Max Reduction 8 dB, Mode Preserve, Residual Off. | JSFX sliders are the real fresh-instance defaults; scattered preset JSON could drift from them. | Added factory preset JSON and tests that compare fresh Preserve values against JSFX slider defaults. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/eval/evaluation_harness.py` | `run_evaluation` | Prompt 7 A/B renderer and report generator. | Preset was free to be Preserve/Balanced/old names. | Prompt 8 preset names and release gating were not represented. | Added Prompt 8 preset choices and release gate module. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/eval/audio_metrics.py` | `evaluate_pair` | Scores preservation, clarity, air, transient, residual, stereo, safety. | Thresholds existed for earlier preset names. | New factory presets could use fallback thresholds silently. | Added Prompt 8 preset aliases and thresholds. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/eval/synthetic_assets.py` | `generate_synthetic_suite` | CI-safe synthetic evaluation assets. | Covered basic sine/noise/transient assets. | Prompt 8 categories were incomplete. | Added clean consonant vocal, acoustic guitar, drum transient, hiss, room tone, metallic, watery, stereo ambience, and full-mix proxies. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/presets/factory_presets_safe_defaults.json` | data | Source of truth for factory preset values, UI grouping, labels, and migration behavior. | Fresh preset is `Preserve`. | None yet; REAPER preset import remains manual. | Use this file to create REAPER presets or any future UI preset manager. |
| `VOCAL_CLARITY_REPAIR_SYSTEM/presets/release_candidate_policy.json` | data | Source of truth for release gates, blockers, warnings, required test categories, and listening policy. | Strong is quality-report-only. | Full real-audio evaluation still requires REAPER renders. | Use with `python3 -m VOCAL_CLARITY_REPAIR_SYSTEM.eval.release_gate`. |

No APVTS layout, C++ preset manager, direct model mode UI, or GUI panel exists in this repository. The JSFX slider panel is therefore the current release UI.

## Product Philosophy

This plugin is a source-preserving AI artifact/noise suppressor. It is not a maximum noise-removal tool, not a restoration miracle tool, and not an enhancer.

The default result should keep the original vocal tone, consonants, presence, air, transients, harmonic texture, ambience, and stereo width. Moderate remaining noise is acceptable when the alternative is a dull, cloudy, lower-fidelity source.

## Factory Presets

| Preset | Mode | Intended use | Risk |
| --- | --- | --- | --- |
| Preserve | Preserve | Safest default for vocals, AI vocals, stems, and mixed material. | Leaves some noise. |
| Balanced | Balanced | More cleanup while still protecting source tone. | Can darken some sources. |
| AI Metallic Surgical | Surgical AI | Narrow metallic chirps, birdies, and source-separation artifacts. | Only helps when artifacts match the detector. |
| Hiss / Room Tone Gentle | Preserve | Broadband hiss and room tone without de-airing. | Not enough for severe chirps. |
| Voiceover Clean | Balanced | Spoken word, podcast, narration. | Less ambience-friendly than Preserve. |
| Strong Test / Repair | Strong Test | Stress/rescue mode for damaged audio. | Not a default, can affect tone. |
| DSP Only Safe | Preserve | Model-disabled or low-confidence fallback. | Lower cleanup. |
| Side Noise Cleanup | Balanced | Stereo-side noise while protecting center vocal. | Not useful on mono. |
| Artifact Focus Low Denoise | Surgical AI | Low broadband denoise with surgical artifact focus. | Not a general hiss preset. |

All values are explicit in `presets/factory_presets_safe_defaults.json`; no preset relies on scattered fallback values.

## Fresh Defaults

Fresh instance default is `Preserve`.

| Parameter | Value |
| --- | ---: |
| Amount | 30% |
| Dry/Wet | 70% |
| Max Reduction | 8 dB |
| Mask Strength | 0.35 |
| Detector Attack | 50 ms |
| Detector Release | 12 ms |
| Soft Knee | 9 dB |
| Vocal Preserve | 0.85 |
| Clarity Preserve | 0.85 |
| Air Preserve | 0.80 |
| Transient Preserve | 0.80 |
| Harmonic Preserve | 0.75 internal |
| Multiband | On, Preserve mode |
| M/S | On for stereo |
| Mid Amount | 0.25 |
| Side Amount | 0.40 |
| Residual Monitor | Off |
| Strong Mode | Off |

Amount remains nonlinear: `internalAmount = pow(userAmount, 1.6)`. Turning Amount to 50% does not mean destructive 50% suppression.

## UI Simplification

Main controls:

- Amount
- Preserve / Balanced / Surgical mode
- Dry/Wet
- Vocal Preserve
- Clarity Preserve
- Air Preserve
- Artifact Focus
- Residual Monitor

Advanced controls:

- Max Suppression
- Side Reduction
- Mid Preserve
- Transient Preserve
- Multiband and M/S toggles
- Detector Attack/Release
- Soft Knee
- Mask Strength

Developer controls:

- raw attack/sandy/fizz/tail tame sliders
- Processing Enabled
- Output Trim

Avoid labels that promise impossible restoration: "Remove all noise", "Restore lost clarity", "AI enhancer", "Make it studio quality", "Perfect clean", or "High-frequency reconstruction".

## Residual Policy

Residual means `original - processed`: what the plugin is removing.

Good residual: noise, hiss, hum, AI chirp, metallic artifact, unwanted fuzz.

Bad residual: vocal phrases, S/T/CH consonants, musical breath, harmonic overtones, guitar picking, snare attack, or source room tail.

If residual contains source, reduce processing, raise Vocal/Clarity/Air/Transient Preserve, reduce high-band attenuation, or reject the preset.

## Automation And Mode Switching

Continuous parameters that affect gain must remain smoothed: Amount, Dry/Wet, Max Suppression, Vocal Preserve, Clarity Preserve, Air Preserve, Transient Preserve, Side Reduction, and Surgical Intensity.

Mode-style parameters are treated as bounded release controls: Preserve/Balanced/Surgical/Strong, Multiband On/Off, M/S On/Off, and Residual Monitor. They must not allocate in the audio path, bypass dry fallback, bypass NaN/Inf checks, or disable total attenuation budgets.

FFT size, hop size, raw model tensor options, individual band debug controls, and low-level detector internals are developer controls, not normal release UI.

## Release Gates

Before a release candidate, render Prompt 7 reports for:

- Preserve
- Balanced
- AI Metallic Surgical
- Hiss / Room Tone Gentle
- Voiceover Clean
- DSP Only Safe
- Strong Test / Repair separately

Required categories:

- clean vocal
- clean consonant vocal
- clean acoustic guitar
- clean drum transient
- vocal with hiss
- room tone vocal
- AI metallic vocal
- watery source-separated vocal
- stereo ambience
- full mix with centered vocal

Run the gate:

```sh
python3 -m VOCAL_CLARITY_REPAIR_SYSTEM.eval.release_gate \
  --reports eval_outputs/Preserve/run_metrics.json eval_outputs/Balanced/run_metrics.json \
  --output-json VOCAL_CLARITY_REPAIR_SYSTEM/reports/release_gate_result.json \
  --output-md VOCAL_CLARITY_REPAIR_SYSTEM/reports/release_gate_result.md
```

Preserve minimums:

- source preservation >= 85 average
- clarity >= 85 average
- air >= 80 average
- transient >= 85 average
- residual cleanliness >= 80 average
- safety = 100

Balanced minimums:

- source preservation >= 75 average
- clarity >= 75 average
- air >= 70 average
- transient >= 75 average
- residual cleanliness >= 75 average
- safety = 100

Strong Test / Repair is safety-gated and quality-report-only. It must never count as the default release quality.

## Release Blockers

Block release if any of these occur:

- crash
- NaN/Inf reaches output
- invalid model output reaches audio
- bypass is not dry
- Dry/Wet 0 is not dry
- clean vocal is damaged in Preserve
- Preserve sounds dull or cloudy
- default residual contains strong ghost vocal
- transients smear in default preset
- 2 kHz to 8 kHz loss exceeds the default threshold
- 8 kHz+ air collapses
- stereo image collapses
- Strong is default or auto-selected
- audio thread has obvious unsafe work
- mode switching clicks severely
- model-not-ready path outputs silence or broken audio
- preset loading breaks old sessions

## Known Limitations

- No direct C++ plugin build target exists in this repo.
- JSFX offline rendering still requires REAPER or pre-rendered WAVs.
- Current model mode is documented as DSP Only because no real model backend is present.
- Factory preset JSON is the preset contract; REAPER preset installation/import remains manual.
- Some noise may remain by design when removing it would damage the source.
