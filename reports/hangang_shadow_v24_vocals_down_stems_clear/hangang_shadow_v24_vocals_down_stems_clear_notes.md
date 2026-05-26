# Hangang Shadow v24 Vocals Down Stem Glue Notes

## Summary

- Source stance: full-stem `12 Vocals.wav` is the male main vocal.
- Vocal bus is reduced 1.5 dB from v23 so the lead is less over-emphasized.
- New instrumental is active as a low beat glue bed; split stems are kept as clearer detail/texture reinforcement instead of acting like separate unglued pieces.
- New female `0 Lead Vocals.wav` remains a quiet gated/panned double only where timing and pitch overlap passed.
- Female gate kept 22.523 s (0.1593) after 210.0 ms global correction.
- Old female candidates (`11 Backing_Vocals.wav` and v19 `0 Lead Vocals.wav`) remain muted as reference material.
- Revision from v23: vocal down, beat cohesion up, stem detail rebalanced to avoid the separated-stem feeling.
- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.
- Status: genre_based_draft; this is a mix/master polish pass, not a reference-matched master.

## Deliverables

- REAPER project: `reaper/hangang_shadow_v24_vocals_down_stems_clear/hangang_shadow_mashup_v24_vocals_down_stems_clear.rpp`
- Premaster WAV: `renders/hangang_shadow_v24_vocals_down_stems_clear/hangang_shadow_mashup_v24_vocals_down_stems_clear_PREMASTER_24-48.wav`
- REAPER print WAV: `renders/hangang_shadow_v24_vocals_down_stems_clear/hangang_shadow_mashup_v24_vocals_down_stems_clear_REAPERPRINT_24-48.wav`
- Loud master WAV: `renders/hangang_shadow_v24_vocals_down_stems_clear/hangang_shadow_mashup_v24_vocals_down_stems_clear_MASTER_loud_24-48.wav`
- Loud master MP3: `renders/hangang_shadow_v24_vocals_down_stems_clear/hangang_shadow_mashup_v24_vocals_down_stems_clear_MASTER_loud_320k.mp3`

## Result

- Source full mix LUFS: -14.9 / true peak -2.6
- Final master LUFS: -9.4 / true peak -1.0
- Audible intent: male stays main but less oversized; beat reads as one glued bed with clearer stem detail around it.

## Metrics

| label | LUFS | LRA | true peak | peak | RMS | corr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| source_full_mix_reference | -14.9 | 3.2 | -2.6 | -2.62 | -16.99 | 0.9278 |
| new_female_raw_candidate | -17.0 | 5.1 | -2.2 | -2.22 | -21.21 | 0.9552 |
| beat_glue_instrumental_source | -15.8 | 5.1 | -2.4 | -2.4 | -17.07 | 0.8981 |
| new_female_gated_pan_layer | -28.1 | 11.8 | -11.1 | -11.1 | -38.01 | 0.99 |
| v24_reaper_premaster | -24.0 | 3.3 | -10.8 | -10.82 | -25.57 | 0.9143 |
| v24_reaper_print | -22.4 | 3.3 | -9.2 | -9.22 | -23.97 | 0.9143 |
| v24_final_master_loud | -9.4 | 2.1 | -1.0 | -1.0 | -11.02 | 0.9084 |
| v24_final_master_loud_mp3 | -9.4 | 2.1 | -0.7 | -0.75 | -11.02 | 0.9083 |

## Main Moves

- Vocal bus: -1.5 dB from v23, with less presence/air makeup on the vocal bus.
- Beat glue: new instrumental is active under the split stems with mild compression, low-mid tightening, and light saturation.
- Female layer: new `0 Lead Vocals.wav` was shifted by the measured global lag, then only overlap frames passing chroma and local timing thresholds were kept.
- Stems: bass/drums/synth/FX are pulled into detail roles while quiet melodic stems are level-normalized upward where safe.
- Bass/kick: saturation reduced from the separate-stem version so the instrumental bed and detail stems glue together instead of doubling too hard.
- Melody M/S: synth, keyboard, and woodwinds get side presence with a slight mid tuck so melody stays audible but embedded.
- Mix/master: conservative low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.
