# REAPER Mix/Master Automation Spec

This repository contains a reproducible REAPER mix/master harness for vocal-centered digicore, hip-hop, hyperpop, and Suno/AI-generated source cleanup. The male vocal is the lead anchor when available. Female vocals are side, shadow, emotional width, and support layers unless explicitly directed otherwise.

## Required Flow

1. Discover source stems from `input/stems/` and full mix references from `input/reference/`.
2. Write `work/assets/asset_manifest.json` and `reports/ASSET_REPORT.md`.
3. Create or validate `work/reaper_project/codex_mix_master_project.rpp`.
4. Build the fixed track layout and bus routing.
5. Insert plugin chains conservatively.
6. Write `work/traces/plugin_trace.json`.
7. Validate routing and plugin gates.
8. Render 24 bit 48 kHz WAV and 16 bit 44.1 kHz WAV when REAPER and source audio are available.
9. Render MP3 preview if an encoder is available, otherwise M4A if available.
10. Run QC, safe auto-correction, and delivery packaging only from verified files.

## Fixed Track Layout

- `SOURCE full mix reference muted - not in master`
- `REF BUS`
- `01 FX`
- `02 SYNTH`
- `03 KEYBOARD`
- `04 GUITAR`
- `05 BASS`
- `06 DRUMS`
- `08 MALE_NONHOOK_CENTER`
- `09 MALE_HOOK_RESIDUAL_CENTER`
- `10 MALE_HOOK_LOWMID_SUPPORT`
- `11 FEMALE_L_SIDE`
- `12 FEMALE_R_SIDE`
- `13 VOCAL_THROW_TUCKED`
- `VOX BUS`
- `DRUM BUS`
- `808/BASS BUS`
- `MUSIC BUS`
- `MIX BUS`
- `PREMASTER`
- `PRINT MASTER`

## Required Routing

The full mix/reference track may route only to the muted `REF BUS`; both the track and `REF BUS` must have master send disabled by default. Vocal tracks and tucked vocal FX route to `VOX BUS`. Drums route to `DRUM BUS`. 808 and bass route to `808/BASS BUS`. FX, synth, keyboard, and guitar route to `MUSIC BUS`. `VOX BUS`, `DRUM BUS`, `808/BASS BUS`, and `MUSIC BUS` route to `MIX BUS`. `MIX BUS` routes to `PREMASTER`. `PREMASTER` routes to `PRINT MASTER`. Only `PRINT MASTER` may feed the REAPER master/hardware output in the active print path.

Optional sidechain sends may route `06 DRUMS` to `808/BASS BUS` channels 3/4 and `08 MALE_NONHOOK_CENTER` to `MUSIC BUS` channels 3/4, but a sidechain send alone is not verified ducking.

## Master Profiles

- Loud reference master: -9.5 to -8.0 LUFS-I, true peak at or below -1.0 dBTP, review/short preview use only.
- Safer streaming master: -14.5 to -12.5 LUFS-I, true peak at or below -1.0 dBTP, default shareable review target.
- Sustained master-bus gain reduction above 2 dB means the pass should return to vocal, drum, 808/bass, or music-bus balance before further limiting.

## Completion Contract

The system is not complete unless render files, trace JSON, QC JSON/Markdown, validation gates, and `delivery/codex_mix_master_delivery.zip` exist. Missing runtime prerequisites must be reported as `BLOCKED` or `UNVERIFIED`.
