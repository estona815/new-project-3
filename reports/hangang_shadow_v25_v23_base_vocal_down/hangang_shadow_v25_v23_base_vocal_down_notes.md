# Hangang Shadow v25 v23 Base Vocal Down Notes

## Summary

- Source stance: full-stem `12 Vocals.wav` is the male main vocal.
- This version restarts from v23 because v24 changed the beat feel too much.
- No new instrumental bed is active; only the original v23 full-stem timing is used for the beat.
- Vocal bus is reduced 1.5 dB from v23 with a smaller presence/air push.
- New female `0 Lead Vocals.wav` is not a lead: it is globally aligned, hard-gated by timing/pitch overlap, then added as a quiet panned double only where it passes.
- Female gate kept 22.523 s (0.1593) after 210.0 ms global correction.
- Old female candidates (`11 Backing_Vocals.wav` and v19 `0 Lead Vocals.wav`) remain muted as reference material.
- Revision from v23: minimal vocal-down correction only; stem timing/structure is kept intact.
- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.
- Status: genre_based_draft; this is a mix/master polish pass, not a reference-matched master.

## Deliverables

- REAPER project: `reaper/hangang_shadow_v25_v23_base_vocal_down/hangang_shadow_mashup_v25_v23_base_vocal_down.rpp`
- Premaster WAV: `renders/hangang_shadow_v25_v23_base_vocal_down/hangang_shadow_mashup_v25_v23_base_vocal_down_PREMASTER_24-48.wav`
- REAPER print WAV: `renders/hangang_shadow_v25_v23_base_vocal_down/hangang_shadow_mashup_v25_v23_base_vocal_down_REAPERPRINT_24-48.wav`
- Loud master WAV: `renders/hangang_shadow_v25_v23_base_vocal_down/hangang_shadow_mashup_v25_v23_base_vocal_down_MASTER_loud_24-48.wav`
- Loud master MP3: `renders/hangang_shadow_v25_v23_base_vocal_down/hangang_shadow_mashup_v25_v23_base_vocal_down_MASTER_loud_320k.mp3`

## Result

- Source full mix LUFS: -14.9 / true peak -2.6
- Final master LUFS: -9.1 / true peak -1.0
- Audible intent: return to v23 song feel, with the vocal less oversized and no added beat timing risk.

## Metrics

| label | LUFS | LRA | true peak | peak | RMS | corr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| source_full_mix_reference | -14.9 | 3.2 | -2.6 | -2.62 | -16.99 | 0.9278 |
| new_female_raw_candidate | -17.0 | 5.1 | -2.2 | -2.22 | -21.21 | 0.9552 |
| new_female_gated_pan_layer | -28.1 | 11.8 | -11.1 | -11.1 | -38.01 | 0.99 |
| v25_reaper_premaster | -25.6 | 3.5 | -10.8 | -10.76 | -27.77 | 0.9247 |
| v25_reaper_print | -24.0 | 3.5 | -9.2 | -9.16 | -26.17 | 0.9247 |
| v25_final_master_loud | -9.1 | 2.0 | -1.0 | -1.0 | -11.39 | 0.92 |
| v25_final_master_loud_mp3 | -9.1 | 2.0 | -0.7 | -0.68 | -11.39 | 0.9198 |

## Main Moves

- V23 base preserved: active music uses the same original full-stem sources and item positions.
- Vocal bus: -1.5 dB from v23, with a smaller presence/air push to reduce the over-forward vocal feel.
- Female layer: new `0 Lead Vocals.wav` was shifted by the measured global lag, then only overlap frames passing chroma and local timing thresholds were kept.
- Stems: no v24 instrumental bed and no broad stem rebalance; the beat structure remains v23.
- Bass/kick: bass and drum stems get added saturation, low-end body, and dynamic low-mid control.
- Melody M/S: synth, keyboard, and woodwinds get side presence with a slight mid tuck so melody stays audible but embedded.
- Mix/master: conservative low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.
