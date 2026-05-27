# Codex Next Dev Tasks

## P0

- Done 2026-05-27: added tests for `audio_utils.py` optional backend metadata:
  - Confirm `spectral_backend` is either `librosa` or `numpy_fft`.
  - Confirm `loudness_backend` is either `pyloudnorm_bs1770` or `rms_proxy`.
- Done 2026-05-27: added QC test that removes `06_OUTPUTS/mp3_check` and confirms MP3 after-encode check either creates an MP3 or logs a clear ffmpeg error.
- Done 2026-05-27: added a JSON report for uncertain REAPER track matches so `apply_policy_to_reaper.lua` warnings are visible outside REAPER markers.

## P1

- Done 2026-05-27: improve `reference_feature_extractor.py` profile:
  - Add per-section summaries: loudest 15s, quiet 15s, high-vocal-presence 15s.
  - Add `profile_version` and `feature_backend` fields.
  - Store acceptable ranges using p25/p75/IQR, already available from `audio_utils.summarize_feature_set`.
- Done 2026-05-27: improve `current_song_analyzer.py`:
  - Add confidence score per stem classification.
  - Emit `unknown_stems_requiring_user_confirmation`.
  - Better conflict scoring for kick vs 808 using low-band envelope correlation.
- Done 2026-05-27: improve `generate_mix_policy.py`:
  - Read new `saturation_shortage_score`.
  - Adjust clip/saturation policies from shortage/risk pair.
  - Add policy version hash and source analysis file timestamps.

## P2

- Build optional `stem_separation_experiment.py`:
  - Demucs/open-unmix optional only.
  - Report artifact warning prominently.
  - Never feed separated stems to final release without user confirmation.
- Build optional `pedalboard_plugin_probe.py`:
  - Inventory-only by default.
  - No automatic plugin loading.
  - GPL/license warning visible in output.
- Build optional JSFX offline smoke harness:
  - Investigate `jpcima/ysfx` only if license/build review is acceptable.

## P3

- ReaPack packaging:
  - Add headers/metadata for ESTONA JSFX and Lua scripts.
  - Keep distribution private until license and generated-artifact boundaries are clean.
- Future native plugin route:
  - Compare DPF/iPlug2/JUCE/CLAP after JSFX proves useful.
  - Choose only one framework and write a separate license memo.
