# Hangang Shadow v23 New Female Gated Pan Notes

## Summary

- Source stance: full-stem `12 Vocals.wav` is the male main vocal.
- New female `0 Lead Vocals.wav` is not a lead: it is globally aligned, hard-gated by timing/pitch overlap, then added as a quiet panned double only where it passes.
- Female gate kept 22.523 s (0.1593) after 210.0 ms global correction.
- Old female candidates (`11 Backing_Vocals.wav` and v19 `0 Lead Vocals.wav`) remain muted as reference material.
- Revision from v22: same male-main/stem/bass/kick/master balance, plus the new low female panned layer.
- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.
- Status: genre_based_draft; this is a mix/master polish pass, not a reference-matched master.

## Deliverables

- REAPER project: `reaper/hangang_shadow_v23_new_female_gated_pan/hangang_shadow_mashup_v23_new_female_gated_pan.rpp`
- Premaster WAV: `renders/hangang_shadow_v23_new_female_gated_pan/hangang_shadow_mashup_v23_new_female_gated_pan_PREMASTER_24-48.wav`
- REAPER print WAV: `renders/hangang_shadow_v23_new_female_gated_pan/hangang_shadow_mashup_v23_new_female_gated_pan_REAPERPRINT_24-48.wav`
- Loud master WAV: `renders/hangang_shadow_v23_new_female_gated_pan/hangang_shadow_mashup_v23_new_female_gated_pan_MASTER_loud_24-48.wav`
- Loud master MP3: `renders/hangang_shadow_v23_new_female_gated_pan/hangang_shadow_mashup_v23_new_female_gated_pan_MASTER_loud_320k.mp3`

## Result

- Source full mix LUFS: -14.9 / true peak -2.6
- Final master LUFS: -8.9 / true peak -1.0
- Audible intent: male voice stays in front; female appears as low side support only on aligned phrases; bass/kick and embedded melody stay from v22.

## Metrics

| label | LUFS | LRA | true peak | peak | RMS | corr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| source_full_mix_reference | -14.9 | 3.2 | -2.6 | -2.62 | -16.99 | 0.9278 |
| new_female_raw_candidate | -17.0 | 5.1 | -2.2 | -2.22 | -21.21 | 0.9552 |
| new_female_gated_pan_layer | -28.1 | 11.8 | -11.1 | -11.1 | -38.01 | 0.99 |
| v23_reaper_premaster | -24.9 | 2.9 | -10.3 | -10.32 | -27.29 | 0.9319 |
| v23_reaper_print | -23.3 | 2.9 | -8.7 | -8.72 | -25.69 | 0.9319 |
| v23_final_master_loud | -8.9 | 1.9 | -1.0 | -1.0 | -11.37 | 0.9295 |
| v23_final_master_loud_mp3 | -8.9 | 1.9 | -0.7 | -0.69 | -11.37 | 0.9293 |

## Main Moves

- Male lead: high-pass cleanup, low-mid dip, 3 kHz presence lift, gentle air, 1.7:1 leveling, light saturation.
- Female layer: new `0 Lead Vocals.wav` was shifted by the measured global lag, then only overlap frames passing chroma and local timing thresholds were kept.
- Stems: active music stems raised from v21 while reference/female-lead/artifact tracks remain muted.
- Bass/kick: bass and drum stems get added saturation, low-end body, and dynamic low-mid control.
- Melody M/S: synth, keyboard, and woodwinds get side presence with a slight mid tuck so melody stays audible but embedded.
- Mix/master: conservative low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.
