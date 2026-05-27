# Open Source Integration Plan

## 즉시 통합할 것

- `librosa` optional backend:
  - Files: `02_ANALYSIS/audio_utils.py`, `02_ANALYSIS/vocal_pitch_analyzer.py`
  - Improvement: spectral centroid/rolloff/flatness/bandwidth, zero-crossing, onset/transient proxy, pyin f0 when installed.
- `pyloudnorm` optional backend:
  - Files: `02_ANALYSIS/audio_utils.py`, `02_ANALYSIS/loudness_codec_qc.py`
  - Improvement: integrated LUFS via BS.1770-style meter when installed, explicit RMS fallback otherwise.
- ReaScript transaction patterns:
  - Files: `04_REAPER_AUTOMATION/apply_policy_to_reaper.lua`, `render_versions.lua`, `export_ab_previews.lua`
  - Improvement: `PreventUIRefresh`, Undo blocks, project backup, ExtState policy timestamp, log file output.
- JSFX style cleanup:
  - Files: `05_JSFX/estona_DigiClip.jsfx`, `05_JSFX/estona_MonoSub_Guard.jsfx`
  - Improvement: simple `@gfx` meters/warnings and clearer REAPER-native sectioning.
- Airwindows/ChowDSP-style conceptual DSP:
  - Files: `02_ANALYSIS/saturation_analyzer.py`
  - Improvement: original `saturation_shortage_score` from crest factor, spectral flatness, high-band energy, transient density, and harmonic density.

## 참고만 할 것

- `sergree/matchering`: reference/target architecture, frequency/level matching stages, preview concept. GPL-3.0, so no direct code copy.
- `X-Raym/REAPER-ReaScripts`: marker/region/script lifecycle patterns. GPL-3.0, so no direct code copy.
- `ReaTeam/JSFX` and `ReaTeam/ReaScripts`: style and API pattern references only because repo-level licensing is unclear/mixed.
- `airwindows/airwindows`: MIT, but DSP should still be reauthored into simpler JSFX ideas rather than copied.

## 나중에 볼 것

- `twardoch/pedalboard-pluginary`: richer plugin inventory if optional pedalboard work continues.
- `jpcima/ysfx`: offline JSFX test host possibility.
- `DISTRHO/DPF`, `iPlug2`, `CLAP`, `oXygen`: future C++/plugin framework route after JSFX policy engine is useful.
- `demucs` and `open-unmix`: optional stem estimation when no stems exist.

## 제외할 것

- `blueff/Matchering`: GPL-3.0 plus MATLAB dependency, low relevance.
- `Sonic-Anomaly/Sonic-Anomaly-JSFX`: license unavailable through GitHub API, exclude until verified.
- Any crack/paid plugin bypass/material: forbidden.

## ESTONA File Impact

- `02_ANALYSIS/reference_feature_extractor.py`
  - Already benefits through `audio_utils.py` feature upgrades.
  - Next: add section-aware profile summaries once hook/loudest/vocal-exposed detection exists.
- `02_ANALYSIS/audio_utils.py`
  - Added optional librosa spectral/onset backend, backend metadata, robust median/range calculation.
- `02_ANALYSIS/loudness_codec_qc.py`
  - Added MP3 after-encode generation/check using PATH ffmpeg or `imageio_ffmpeg`.
  - Report now states true peak is a proxy.
- `02_ANALYSIS/saturation_analyzer.py`
  - Added `saturation_shortage_score` and `overbright_saturation_risk`.
- `02_ANALYSIS/plugin_inventory_scanner.py`
  - New optional inventory-only VST3/AU scanner. No plugin loading.
- `02_ANALYSIS/matchering_reference_experiment.py`
  - New study-only placeholder. Not in default pipeline.
- `04_REAPER_AUTOMATION/apply_policy_to_reaper.lua`
  - Added backup copy, log writing, ExtState policy metadata, missing-JSFX warnings.
- `04_REAPER_AUTOMATION/render_versions.lua`
  - Added render prep log.
- `04_REAPER_AUTOMATION/export_ab_previews.lua`
  - Added UI refresh guard and ExtState timestamp.
- `05_JSFX/estona_DigiClip.jsfx`
  - Added simple clipping meter.
- `05_JSFX/estona_MonoSub_Guard.jsfx`
  - Added side-low warning meter.

## Pipeline Position

Default pipeline remains:

1. Analyze references/current stems.
2. Generate reference/current delta.
3. Generate conservative/normal/aggressive policies.
4. Apply policy in REAPER using stock/JSFX-first processing.
5. Render and QC WAV/MP3.
6. Human listening approval.

Optional experiments (`pedalboard`, `matchering`, stem separation) must never become default without explicit user request and license review.
