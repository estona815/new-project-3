# mesi_1 v12 Codex Tune/EQ Substitute Session

- Classification: `vocal_repair_chain_prepared + Codex_tune_EQ_substitute_session`
- RPP: `/Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v12_codex_tune_eq_substitute/mesi_1_v12_CODEX_TUNE_EQ_SUBSTITUTE.rpp`
- Source vocal: `/Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v09_tuned_ducked_space_dynamic_master/source_stems/mesi_1_main_vocal_trigger.wav`
- Max severity: `PASS`
- Claim status: `not_vocal_tuned_until_pitch_QC_and_human_AB`

## What Was Applied

- `Codex Vocal Pitch Monitor`
- `ReaTune` as the stock REAPER pitch-correction engine
- `Codex Pro Dynamic MS EQ`
- `Codex Dynamic EQ Band`
- `Codex Noise Floor Tamer`

## Honesty Notes

- This is not Antares Auto-Tune.
- This is not FabFilter Pro-Q.
- `vocal tuned` is still forbidden until key/scale, correction settings, rendered before/after, and human A/B exist.

## Rows

| Severity | Stage | Status | Target | Detail |
| --- | --- | --- | --- | --- |
| PASS | media | inserted | `01_REF_V11_CURRENT_FAVORITE_MUTED` | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_MASTER_24-48.wav |
| PASS | media | inserted | `02_FULL_MIX_ORIGINAL_REF_MUTED` | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v09_tuned_ducked_space_dynamic_master/source_stems/mesi_1_full_mix_original.wav |
| PASS | media | inserted | `03_LEAD_VOCAL_RAW_MUTED` | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v09_tuned_ducked_space_dynamic_master/source_stems/mesi_1_main_vocal_trigger.wav |
| PASS | media | inserted | `04_LEAD_VOCAL_CODEX_TUNE_EQ_SUBSTITUTE` | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v09_tuned_ducked_space_dynamic_master/source_stems/mesi_1_main_vocal_trigger.wav |
| PASS | media | inserted | `06_MUSIC_SUPPORT_LOW_MUTED` | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v09_tuned_ducked_space_dynamic_master/source_stems/mesi_1_keyboard_b_raw.wav |
| PASS | media | inserted | `07_DRUMS_SUPPORT_MUTED` | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v09_tuned_ducked_space_dynamic_master/source_stems/mesi_1_drums_raw.wav |
| PASS | media | inserted | `08_BASS_SUPPORT_MUTED` | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v09_tuned_ducked_space_dynamic_master/source_stems/mesi_1_bass_raw.wav |
| PASS | pitch monitor | loaded | `JS: codex_fresh_mix/codex_vocal_pitch_monitor.jsfx` | fx_index=0 |
| PASS | ReaTune pitch engine | loaded | `ReaTune` | fx_index=1 |
| PASS | dynamic M/S EQ | loaded | `JS: codex_fresh_mix/codex_pro_dynamic_ms_eq.jsfx` | fx_index=2 |
| PASS | extra resonance dynamic EQ | loaded | `JS: codex_fresh_mix/codex_dynamic_eq_band.jsfx` | fx_index=3 |
| PASS | noise/fizz floor tamer | loaded | `JS: codex_fresh_mix/codex_noise_floor_tamer.jsfx` | fx_index=4 |
| PASS | vocal bus polish | loaded | `JS: codex_fresh_mix/codex_v20_channel_polish.jsfx` | fx_index=0 |
| PASS | project | saved | `/Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v12_codex_tune_eq_substitute/mesi_1_v12_CODEX_TUNE_EQ_SUBSTITUTE.rpp` | RPP contains ReaTune and Codex substitute JSFX chain. |
