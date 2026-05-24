# Suno REAPER Harness v0.5 Handoff

Date: 2026-05-24
Branch: `codex/suno-reaper-harness-v05-handoff`
Project root: `/Users/hantaeheuk/Documents/New project 3`

## Current State

This project is moving from Python-only Suno stem processing into a REAPER-centered production harness.

The latest completed audio snapshot before the new REAPER workflow is v23:

- MP3: `/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/v11_precision_mix/renders/hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_320k.mp3`
- WAV: `/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/v11_precision_mix/renders/hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_24-48.wav`
- Processed stems ZIP: `/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/v11_precision_mix/renders/hangang_shadow_mashup_v23_vocal_clarity_rebalance_processed_stems.zip`
- Current classified package: `/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/_classified_current_v23_for_new_work`

Important rule: MP3/master/fullmix files are reference/problem-reference only. Production rebuild must use Suno Studio WAV stems and guide MIDI.

## v0.5 Harness Patch

The harness was patched to v0.5 with these goals:

- Use REAPER as the main DAW workflow.
- Treat Suno WAV stems as production source.
- Treat Suno MIDI as guide MIDI only, never final truth.
- Classify MP3/master/fullmix files as `problem_reference` or `reference_only`.
- Detect and quarantine AI artifacts.
- Build a professional REAPER routing layout.
- Add plugin discovery/config with safe fallbacks.
- Add source classification, reference comparison, audio QC, MIDI cleanup, REAPER scripts, prompt payloads, and planning reports.

## Key Added Or Updated Code

- `scrh`
- `AI_BEAT_LOGIC_WORKFLOW/src/suno_source_classifier.py`
- `AI_BEAT_LOGIC_WORKFLOW/src/audio_qc.py`
- `AI_BEAT_LOGIC_WORKFLOW/src/suno_reaper_generator.py`
- `AI_BEAT_LOGIC_WORKFLOW/src/reaper_plugin_inventory.py`
- `AI_BEAT_LOGIC_WORKFLOW/src/reference_comparison.py`
- `AI_BEAT_LOGIC_WORKFLOW/src/reaper_harness_v05.py`
- `AI_BEAT_LOGIC_WORKFLOW/tests/test_suno_reaper_harness.py`

## Key Generated Files

- `config/plugin_map.yaml`
- `reports/codex_patch_report.md`
- `reports/plugin_inventory.md`
- `reports/plugin_inventory.json`
- `reports/source_classification.md`
- `reports/source_classification.json`
- `reports/reference_comparison.md`
- `reports/current_problem_profile.json`
- `reports/reference_profile.json`
- `reports/audio_qc.md`
- `reports/audio_qc.json`
- `reports/vocal_tuning_plan.md`
- `reports/reverb_delay_plan.md`
- `reports/vocal_fx_settings.md`
- `reports/stereo_ms_eq_plan.md`
- `reports/mix_master_plan.md`
- `reports/master_settings.md`
- `reports/manual_plugin_notes.md`
- `reports/render_report.md`
- `reports/studio_export_plan.md`
- `reports/suno_style_prompt.txt`
- `reports/suno_exclude_prompt.txt`
- `reports/suno_generation_settings.md`
- `reports/suno_prompt_payload.json`
- `reports/reaper_import_manifest.json`
- `midi/cleaned/*.mid`
- `reaper/build_project.lua`
- `reaper/apply_mix_chains.lua`
- `reaper/render_project.lua`
- `reaper/launch_reaper.sh`
- `reaper/launch_reaper.ps1`
- `renders/REFERENCE_MATCH_NOTES.md`

## Plugin Detection

Safe plugin inventory detected these preferred tools as availability hints:

- Pitch correction: `Auto-Tune Pro`
- Surgical EQ / dynamic EQ / de-esser / M/S EQ: `TDR Nova`
- Character compression: `uaudio_teletronix_la-2a_tc`, with `uaudio_ua_1176` also detected
- Saturation: `Decapitator`, `Fresh Air`
- Stereo imaging: `Ozone Imager 2`

Fallback roles currently include:

- `compressor_clean` -> `ReaComp`
- `multiband_compressor` -> `ReaXcomp`
- `reverb_plate` -> `ReaVerbate`
- `reverb_room` -> `ReaVerbate`
- `delay` -> `ReaDelay`
- `limiter` -> `ReaLimit`
- `loudness_meter` -> `ffmpeg ebur128 / JS: Loudness Meter Peak/RMS/LUFS`
- `noise_reduction` -> `ReaFIR`

Do not claim premium plugin processing was applied until REAPER insertion and render are verified.

## Source Classification Summary

Last generated source classification:

- Production rebuild allowed: true
- Production audio files: 14
- Reference-only files: 5
- Guide MIDI files: 13
- Quarantine sources from QC: 2

Important classifications:

- `00_REF_Full_Mix.wav` -> `reference_only`
- v21/v23 masters -> `problem_reference`
- `12_Vocals.wav` -> `male_lead_vocal`
- `11_Backing_Vocals.wav` -> `female_bgv`
- `external_female_v20_stems/0 Lead Vocals.wav` -> `female_bgv`
- `external_female_v20_stems/1 Instrumental.wav` -> `reference_only`
- `03_FX.wav` -> QC override to `ARTIFACT_QUARANTINE_BUS`, muted
- `08_Guitar.wav` -> QC override to `ARTIFACT_QUARANTINE_BUS`, muted

## Reference Comparison

Current/problem reference:

- Requested: `/mnt/data/hangang_shadow_mashup_v21_clear_male_blended_female_MASTER_320k.mp3.zip`
- Project fallback found and analyzed:
  `/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/v11_precision_mix/renders/hangang_shadow_mashup_v21_clear_male_blended_female_MASTER_320k.mp3.zip`
- Classification: `problem_reference`

Technical commercial reference:

- Requested: `/mnt/data/Estona,Nib-Lovee_MASTER_24-48.wav.zip`
- Status: missing in this environment
- Classification target: `technical_mix_reference`

Use the technical reference only for vocal clarity, placement, reverb depth, delay control, stereo image, tonal balance, low-end control, dynamic movement, and polish. Do not copy melody, lyrics, arrangement, chords, topline, artist identity, or musical content.

## Audio QC Summary

Last generated audio QC:

- Files analyzed: 16
- Issues detected: 208
- REAPER marker candidates: 83
- Quarantine sources:
  - `/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/03_FX.wav`
  - `/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/08_Guitar.wav`

QC detects:

- local dropouts
- abrupt cuts
- hard splice candidates
- unstable section transitions
- phase/stereo width anomalies
- high-frequency harshness risk
- low-end mud/masking risk
- suspicious AI vocal texture issues

## REAPER Session Layout

`reaper/build_project.lua` creates:

- `REF_BUS`
- `DRUM_BUS`
- `BASS_808_BUS`
- `MUSIC_BUS`
- `MALE_LEAD_VOX_BUS`
- `FEMALE_BGV_BUS`
- `VOCAL_FX_BUS`
- `FX_BUS`
- `ARTIFACT_QUARANTINE_BUS`
- `MIX_BUS`
- `MASTER_PREMIX_BUS`
- `PRINT_MASTER_BUS`
- `VOCAL_PLATE_SEND`
- `VOCAL_DELAY_SEND`
- `SHORT_ROOM_SEND`
- `OPTIONAL_WIDE_THROW_SEND`

Routing intent:

- References muted by default.
- Quarantine tracks muted by default.
- Male lead centered and upfront.
- Female BGV lower and wide support only.
- Vocal reverb/delay send-based, filtered, and controlled.
- Musical buses route to `MIX_BUS -> MASTER_PREMIX_BUS -> PRINT_MASTER_BUS`.

Run:

```sh
cd "/Users/hantaeheuk/Documents/New project 3"
./reaper/launch_reaper.sh
```

Then inspect plugin insertions manually inside REAPER before render.

## Tests

Targeted v0.5 tests passed:

```sh
PYTHONPATH=AI_BEAT_LOGIC_WORKFLOW/src python3 -m unittest AI_BEAT_LOGIC_WORKFLOW.tests.test_suno_reaper_harness -v
```

Result: 13/13 passed.

Full `unittest discover` was attempted:

- 495 tests run
- 493 passed
- 2 failed due to existing repo fixture/worktree state, not the v0.5 path:
  - missing `AI_BEAT_LOGIC_WORKFLOW/05_FINAL_WAV/plugg_reference_matched_v4_24bit_48k.wav`
  - existing untracked `AI_BEAT_LOGIC_WORKFLOW/08_REFERENCE_MATCH/web_reference_sources.json` broke a temp-root isolation assertion

`pytest` is not installed in this environment, so pytest could not be used.

## Known Limitations

- REAPER was not run in this patch.
- No REAPER render was verified yet.
- Technical reference WAV zip was missing.
- Premium plugins are only detected as availability hints. Do not claim they were applied until REAPER confirms insertion and a render is verified.
- If the main vocal stem still has severe AI artifacts, mark the section as requiring regeneration or manual re-recording.

## Recommended Next Step

1. Open REAPER using `reaper/launch_reaper.sh`.
2. Confirm references and quarantine tracks are muted.
3. Confirm `03_FX.wav` and `08_Guitar.wav` are in `ARTIFACT_QUARANTINE_BUS`.
4. Confirm `12_Vocals.wav` is the main male lead.
5. Confirm `external_female_v20_stems/0 Lead Vocals.wav` is female BGV support only.
6. Insert or verify Auto-Tune Pro / TDR Nova / Decapitator / Ozone Imager where REAPER can actually load them.
7. Tune lead vocal naturally but locked.
8. Use dynamic EQ to carve music around 1-5 kHz for vocal intelligibility.
9. Use send-based plate/delay, filtered and ducked.
10. Render premaster first, then conservative master.
11. Update `reports/render_report.md` after actual REAPER render verification.

