# Hangang Shadow v26 Synth Natural Intro Chop Notes

## Summary

- Source stance: full-stem `12 Vocals.wav` is the male main vocal.
- This version restarts from v23 because v24 changed the beat feel too much.
- No new instrumental bed is active; only the original v23 full-stem timing is used for the beat.
- Vocal bus is reduced 1.5 dB from v23 with a smaller presence/air push.
- Added female-double intro chops before 9.20s are removed; the male main vocal is not cut.
- Synth is pulled back and darkened with dynamic presence/top-end control to reduce the AI-like edge.
- New female `0 Lead Vocals.wav` is not a lead: it is globally aligned, hard-gated by timing/pitch overlap, then added as a quiet panned double only where it passes.
- Female gate kept 22.523 s (0.1593) after 210.0 ms global correction.
- Old female candidates (`11 Backing_Vocals.wav` and v19 `0 Lead Vocals.wav`) remain muted as reference material.
- Revision from v25: remove added intro chops, soften synth, and make only a small instrumental texture/melody polish.
- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.
- Status: genre_based_draft; this is a mix/master polish pass, not a reference-matched master.

## Deliverables

- REAPER project: `reaper/hangang_shadow_v26_v23_base_synth_natural/hangang_shadow_mashup_v26_v23_base_synth_natural.rpp`
- Premaster WAV: `renders/hangang_shadow_v26_v23_base_synth_natural/hangang_shadow_mashup_v26_v23_base_synth_natural_PREMASTER_24-48.wav`
- REAPER print WAV: `renders/hangang_shadow_v26_v23_base_synth_natural/hangang_shadow_mashup_v26_v23_base_synth_natural_REAPERPRINT_24-48.wav`
- Loud master WAV: `renders/hangang_shadow_v26_v23_base_synth_natural/hangang_shadow_mashup_v26_v23_base_synth_natural_MASTER_loud_24-48.wav`
- Loud master MP3: `renders/hangang_shadow_v26_v23_base_synth_natural/hangang_shadow_mashup_v26_v23_base_synth_natural_MASTER_loud_320k.mp3`

## Result

- Source full mix LUFS: -14.9 / true peak -2.6
- Final master LUFS: -9.1 / true peak -1.0
- Audible intent: keep the v23/v25 song feel, remove the added intro chop distraction, and make the melody less synthetic while still present.

## Metrics

| label | LUFS | LRA | true peak | peak | RMS | corr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| source_full_mix_reference | -14.9 | 3.2 | -2.6 | -2.62 | -16.99 | 0.9278 |
| synth_source_reference | -23.7 | 12.2 | -3.0 | -3.05 | -27.83 | 0.4489 |
| new_female_raw_candidate | -17.0 | 5.1 | -2.2 | -2.22 | -21.21 | 0.9552 |
| new_female_gated_no_intro_chops_layer | -28.0 | 12.1 | -11.1 | -11.1 | -38.16 | 0.99 |
| v26_reaper_premaster | -25.8 | 3.6 | -10.7 | -10.67 | -27.91 | 0.9541 |
| v26_reaper_print | -24.2 | 3.6 | -9.1 | -9.07 | -26.31 | 0.9541 |
| v26_final_master_loud | -9.1 | 2.1 | -1.0 | -1.0 | -11.29 | 0.951 |
| v26_final_master_loud_mp3 | -9.1 | 2.1 | -0.7 | -0.7 | -11.29 | 0.9508 |

## Main Moves

- V23 base preserved: active music uses the same original full-stem sources and item positions.
- Vocal bus: -1.5 dB from v23, with a smaller presence/air push to reduce the over-forward vocal feel.
- Intro chops: removed only the added female-double layer before 9.20s; original male lead and beat are untouched.
- Synth: lowered 1.8 dB, less side-bright M/S, dynamic 3.15 kHz control, and high-tail taming for a less AI-like texture.
- Female layer: new `0 Lead Vocals.wav` was shifted by the measured global lag, then only overlap frames passing chroma and local timing thresholds were kept.
- Stems: no v24 instrumental bed and no broad stem rebalance; the beat structure remains v23.
- Bass/kick: bass and drum stems get added saturation, low-end body, and dynamic low-mid control.
- Melody M/S: synth, keyboard, and woodwinds get side presence with a slight mid tuck so melody stays audible but embedded.
- Mix/master: conservative low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.
