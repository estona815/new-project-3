# MIDI Reconstruction Audit

- RPP: `/Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v10_reaper_pipeline/mesi_1_v10_REAPER_PIPELINE.rpp`
- Classification recommendation: `drum_reinforcement`
- True rebeat allowed: `False`
- Fullmix dependency: `high`
- Bus renders complete: `False`

## Counts

- Kick notes: `1`
- Snare notes: `1`
- Hat/percussion notes: `1`
- Bass notes: `0`
- Music notes: `0`

## Tracks

| # | Name | Roles | MIDI | Notes | Audio | Muted |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 01_REF_ORIGINAL | - | False | 0 | True | True |
| 2 | 02_WORKING_FULLMIX_MP3_DECODED | - | False | 0 | True | False |
| 3 | 03_GRID_MARKERS | - | False | 0 | False | True |
| 4 | 04_KICK_REBUILD_MIDI | drums | True | 0 | False | True |
| 5 | 05_SNARE_CLAP_REBUILD_MIDI | drums | True | 0 | False | True |
| 6 | 06_HAT_PERC_REBUILD_MIDI | drums | True | 0 | False | True |
| 7 | 07_DRUMS_AUDIO_SUPPORT | drums | False | 0 | True | True |
| 8 | 08_BASS_REBUILD_UNAVAILABLE | bass | False | 0 | False | True |
| 9 | 09_MUSIC_REBUILD_UNAVAILABLE | music | False | 0 | False | True |
| 10 | 10_VOCAL_STEM_MISSING | vocal | False | 0 | False | True |
| 11 | 11_FULLMIX_DERIVED_VOCAL_FOCUS | vocal | False | 0 | False | True |
| 12 | 12_DEAI_NOISE_REDUCTION_BUS | - | False | 0 | False | True |
| 13 | 13_PARALLEL_DRUM_COMP | drums | False | 0 | False | True |
| 14 | 14_MID_SIDE_REPAIR_BUS | - | False | 0 | False | True |
| 15 | 15_MIX_BUS | - | False | 0 | True | True |
| 16 | 16_MASTER_BUS | - | False | 0 | False | True |
| 17 | 17_MASTER_PRINT | - | False | 0 | True | True |

## Findings

| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WARN | REBEAT_BUS_RENDERS_MISSING | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline | Role bus render evidence exists. | {"bass": [], "drums": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_drums_bus.wav"], "master": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_master_bus.wav", "/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_24-48.wav"], "mix": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_mix_bus.wav"], "music": []} | Render drums, bass, music/support, mix, and master buses, then rerun audit. | - | no |
| WARN | FULLMIX_ACTIVE_WITH_REBUILD_ITEMS | /Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v10_reaper_pipeline/mesi_1_v10_REAPER_PIPELINE.rpp | Rebuild items are the primary sound source. | original_fullmix_active=true | Classify as drum reinforcement or partial rebeat unless the independent arrangement can play without fullmix reliance. | - | yes |
