# Hangang Shadow v20 Commercial Polish Notes

## Summary

- Source stance: latest v19 lead vocal + instrumental two-stem kept as the active arrangement.
- Full-stem original mix was imported into the REAPER project as muted reference context only.
- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.
- Status: genre_based_draft; this is a mix/master polish pass, not a reference-matched master.

## Deliverables

- REAPER project: `reaper/hangang_shadow_v20_commercial_polish/hangang_shadow_mashup_v20_commercial_polish.rpp`
- Premaster WAV: `renders/hangang_shadow_v20_commercial_polish/hangang_shadow_mashup_v20_commercial_polish_PREMASTER_24-48.wav`
- REAPER print WAV: `renders/hangang_shadow_v20_commercial_polish/hangang_shadow_mashup_v20_commercial_polish_REAPERPRINT_24-48.wav`
- Loud master WAV: `renders/hangang_shadow_v20_commercial_polish/hangang_shadow_mashup_v20_commercial_polish_MASTER_loud_24-48.wav`
- Loud master MP3: `renders/hangang_shadow_v20_commercial_polish/hangang_shadow_mashup_v20_commercial_polish_MASTER_loud_320k.mp3`

## Result

- Source rough sum LUFS: -17.1 / true peak -1.5
- Final master LUFS: -9.2 / true peak -1.0
- Audible intent: similar arrangement, cleaner vocal edge, slightly tighter low-mid, smoother commercial density.

## Metrics

| label | LUFS | LRA | true peak | peak | RMS | corr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| v19_2stem_sum_minus3db | -17.1 | 4.0 | -1.5 | -1.54 | -19.68 | 0.7647 |
| v20_reaper_premaster | -18.4 | 4.2 | -2.8 | -2.78 | -21.21 | 0.8231 |
| v20_reaper_print | -16.8 | 4.2 | -1.2 | -1.18 | -19.61 | 0.8231 |
| v20_final_master_loud | -9.2 | 2.9 | -1.0 | -1.0 | -12.08 | 0.822 |
| v20_final_master_loud_mp3 | -9.2 | 2.9 | -0.8 | -0.78 | -12.08 | 0.8219 |

## Main Moves

- Lead vocal: high-pass cleanup, low-mid dip, 3 kHz presence lift, gentle air, 1.7:1 leveling, light saturation.
- Instrumental: sub cleanup, small low-mid tuck, mild glue compression, tiny width/open-air lift.
- Mix/master: conservative low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.
