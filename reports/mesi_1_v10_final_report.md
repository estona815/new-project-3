# mesi_1_v10 Final Report

## Actual Classification

`fullmix_rescue + Suno_DeAI_repair + master processing`.

`drum_reinforcement` was rendered as candidate E and audited in the RPP, but it was not selected for the final WAV.

This is not `true_rebeat`, not `stem rebuild`, not `vocal tuned`, and not `lossless restoration`.

## Created Files

- Final WAV: `renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_24-48.wav`
- MP3 preview: `renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_320k.mp3`
- A/B preview: `renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_AB_PREVIEW_320k.mp3`
- REAPER project: `reaper/mesi_1_v10_reaper_pipeline/mesi_1_v10_REAPER_PIPELINE.rpp`
- ZIP: `renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_FINAL_DELIVERABLE.zip`

## What Was Actually Done

- Decoded MP3 to 48 kHz working WAV.
- Created REAPER pipeline project with explicit reference/fullmix/MIDI/support/bus/master tracks.
- Analyzed BPM/grid and onset events.
- Created drum reinforcement MIDI evidence and subtle audio support as candidate E; selected final C does not use that support.
- Applied conservative fullmix DeAI-style high-side/fizz control, dynamic resonance control, M/S side wash control, and limiter/output guard; selected C minimized compression to preserve transients.
- Rendered A/B/C/D/E candidates and selected by QC score.

## What Was Not Done

- No true rebeat: no bass/music MIDI or independent arrangement bus evidence.
- No selected-final drum reinforcement: candidate E exists, but grid confidence failed and C_punch_preserve won QC.
- No stem rebuild: discovered stems were not used as active v10 source stems.
- No vocal tuning: no isolated vocal/pitch edit evidence.
- No lossless restoration: source is MP3.

## QC Summary

- Duration: `105.850688` -> `105.850688` sec
- Peak: `-1.604253800670255` -> `-1.4253022379948799` dBFS
- Loudness: `None` -> `None` LUFS
- Harshness delta: `-0.06044314022947894` dB
- Sibilance delta: `-0.09354406796214221` dB
- Air/fizz delta: `-0.07017598686045545` dB
- Punch delta: `0.024730455381559935` dB
- Transient ratio: `0.997120902664239`
- Side/mid delta: `-0.3142947476003979` dB

## WARN/FAIL/BLOCKER

| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WARN | INTEGRATED_LOUDNESS_UNAVAILABLE | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v10_reaper_pipeline/intermediate/mesi_1_v10_WORKING_FROM_MP3_48k.wav | Integrated LUFS is available for QC. | pyloudnorm import failed or numpy is unavailable. | Install pyloudnorm in the harness environment, then rerun before/after QC. | python3 -m harness.audio_qc --before BEFORE.wav --after AFTER.wav --json | no |
| WARN | LOSSY_MP3_SOURCE | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v03_mp3_piano_vocal_noise_tuck/mesi_1_v03_MASTER_320k.mp3 | MP3-derived WAV is a lossless original. | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v03_mp3_piano_vocal_noise_tuck/mesi_1_v03_MASTER_320k.mp3 | Keep lossy-source language in all reports and avoid lossless restoration claims. | - | no |
| WARN | JSFX_SMOKE_WARN | /Users/hantaeheuk/Documents/New project 3/ESTONA_AUTO_MIX_ENGINE/00_EXTERNAL_REFS/reaper_lua/ReaTeam_ReaScripts_Templates/JSFX/GFX/spk77_Basic GFX text.jsfx | Custom JSFX can be safely inserted. | {"file": "/Users/hantaeheuk/Documents/New project 3/ESTONA_AUTO_MIX_ENGINE/00_EXTERNAL_REFS/reaper_lua/ReaTeam_ReaScripts_Templates/JSFX/GFX/spk77_Basic GFX text.jsfx", "has_desc": false, "has_null_bytes": false, "has_slider_or_code": true, "line_count": 25} | Open the JSFX in REAPER or fix desc/code structure, then rerun plugin audit. | python3 -m harness.plugin_audit --project-root /Users/hantaeheuk/Documents/New project 3 --json | no |
| WARN | INTEGRATED_LOUDNESS_UNAVAILABLE | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v10_reaper_pipeline/intermediate/mesi_1_v10_WORKING_FROM_MP3_48k.wav | Integrated LUFS is available for QC. | pyloudnorm import failed or numpy is unavailable. | Install pyloudnorm in the harness environment, then rerun before/after QC. | python3 -m harness.audio_qc --before BEFORE.wav --after AFTER.wav --json | no |
| WARN | INTEGRATED_LOUDNESS_UNAVAILABLE | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_24-48.wav | Integrated LUFS is available for QC. | pyloudnorm import failed or numpy is unavailable. | Install pyloudnorm in the harness environment, then rerun before/after QC. | python3 -m harness.audio_qc --before BEFORE.wav --after AFTER.wav --json | no |
| WARN | FULLMIX_DEESSER_RISK | - | Fullmix de-essing is low risk. | move_index=1, target=fullmix master, max_reduction_db=1.20 | Prefer isolated vocal de-essing when possible; keep fullmix de-essing narrow and light, then run brightness/vocal A/B. | - | yes |
| WARN | REBEAT_BUS_RENDERS_MISSING | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline | Role bus render evidence exists. | {"bass": [], "drums": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_drums_bus.wav"], "master": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_master_bus.wav", "/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_24-48.wav"], "mix": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_mix_bus.wav"], "music": []} | Render drums, bass, music/support, mix, and master buses, then rerun audit. | - | no |
| WARN | FULLMIX_ACTIVE_WITH_REBUILD_ITEMS | /Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v10_reaper_pipeline/mesi_1_v10_REAPER_PIPELINE.rpp | Rebuild items are the primary sound source. | original_fullmix_active=true | Classify as drum reinforcement or partial rebeat unless the independent arrangement can play without fullmix reliance. | - | yes |
| WARN | LOSSY_SOURCE_REBEAT_LIMITATION | {"format": "mp3", "lossy": true, "path": "/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v03_mp3_piano_vocal_noise_tuck/mesi_1_v03_MASTER_320k.mp3"} | Lossy source can support lossless restoration language. | source_is_lossy=true | Use lossy-source processed print language and avoid lossless restoration claims. | - | no |
| FAIL | GRID_CONFIDENCE_FAIL | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v10_reaper_pipeline/intermediate/mesi_1_v10_WORKING_FROM_MP3_48k.wav | Detected grid is safe for reconstruction. | grid_confidence=FAIL, grid_score=0.241 | Use manual tempo map or light reinforcement only; do not hard-quantize or claim true rebeat unless justified. | - | yes |
| WARN | INTEGRATED_LOUDNESS_UNAVAILABLE | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_24-48.wav | Integrated LUFS is available for QC. | pyloudnorm import failed or numpy is unavailable. | Install pyloudnorm in the harness environment, then rerun before/after QC. | python3 -m harness.audio_qc --before BEFORE.wav --after AFTER.wav --json | no |
| WARN | REBEAT_BUS_RENDERS_MISSING | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline | Role bus render evidence exists. | {"bass": [], "drums": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_drums_bus.wav"], "master": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_master_bus.wav", "/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_24-48.wav"], "mix": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_mix_bus.wav"], "music": []} | Render drums, bass, music/support, mix, and master buses, then rerun audit. | - | no |
| WARN | FULLMIX_ACTIVE_WITH_REBUILD_ITEMS | /Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v10_reaper_pipeline/mesi_1_v10_REAPER_PIPELINE.rpp | Rebuild items are the primary sound source. | original_fullmix_active=true | Classify as drum reinforcement or partial rebeat unless the independent arrangement can play without fullmix reliance. | - | yes |
| WARN | EXTERNAL_VALIDATOR_WARN | python3 -m pytest tests/test_harness_smoke.py | All requested validators are available and pass. | /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest | Install missing validator/test dependency or create the missing test, then rerun. | - | no |
| WARN | EXTERNAL_VALIDATOR_WARN | python3 -m pytest tests/test_engineering_rules.py | All requested validators are available and pass. | /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest | Install missing validator/test dependency or create the missing test, then rerun. | - | no |
| WARN | EXTERNAL_VALIDATOR_WARN | python3 -m pytest tests/test_rebeat_classification.py | All requested validators are available and pass. | /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest | Install missing validator/test dependency or create the missing test, then rerun. | - | no |
| WARN | EXTERNAL_VALIDATOR_WARN | python3 -m pytest tests/test_pipeline_integration.py | All requested validators are available and pass. | /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest | Install missing validator/test dependency or create the missing test, then rerun. | - | no |
| WARN | REAPER_RENDER_FALLBACK | /Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v10_reaper_pipeline/mesi_1_v10_REAPER_PIPELINE.rpp | REAPER executable availability means the final WAV was rendered by REAPER. | reaper_executable=/Applications/REAPER.app/Contents/MacOS/REAPER, selected_candidate=C_punch_preserve | Run a REAPER batch/render pass from the generated RPP or render_candidates.lua, then rerun final validation if REAPER-render evidence is required. | /Applications/REAPER.app/Contents/MacOS/REAPER -newinst -nosplash /Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v10_reaper_pipeline/mesi_1_v10_REAPER_PIPELINE.rpp | yes |

## Allowed Claims

- fullmix rescue
- drum reinforcement candidate/audit only, not selected-final drum replacement
- Suno DeAI repair
- lossy-source processed print

## Forbidden Claims

- true rebeat
- 비트 다 새로 찍음
- lossless restoration
- vocal tuned
- professional final master without human listening approval

## Rerun Commands

- `python3 tools/mesi_1_v10_reaper_pipeline.py`
- `python3 harness/audio_qc.py --before /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v10_reaper_pipeline/intermediate/mesi_1_v10_WORKING_FROM_MP3_48k.wav --after /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_24-48.wav --json`
- `python3 harness/engineering_rule_checker.py --before /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v10_reaper_pipeline/intermediate/mesi_1_v10_WORKING_FROM_MP3_48k.wav --after /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_24-48.wav --profile presets/engineering_rules/mp3_source_rescue_rules.json --processing-report /Users/hantaeheuk/Documents/New project 3/reports/mesi_1_v10_processing_report.json --out-json /Users/hantaeheuk/Documents/New project 3/reports/mesi_1_v10_engineering_rule_check.json --out-md /Users/hantaeheuk/Documents/New project 3/reports/mesi_1_v10_engineering_rule_check.md`
- `python3 harness/final_validator.py --project-root . --final-wav /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_24-48.wav --rpp /Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v10_reaper_pipeline/mesi_1_v10_REAPER_PIPELINE.rpp --reports-dir reports --out-json /Users/hantaeheuk/Documents/New project 3/reports/mesi_1_v10_final_validation.json --out-md /Users/hantaeheuk/Documents/New project 3/reports/mesi_1_v10_final_validation.md`
