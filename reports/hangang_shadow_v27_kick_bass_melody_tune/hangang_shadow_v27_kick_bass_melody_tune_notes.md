# Hangang Shadow v27 Kick Bass Melody Tune Notes

## Summary

- Source stance: full-stem `12 Vocals.wav` is the male main vocal.
- This version restarts from v23 because v24 changed the beat feel too much.
- No new instrumental bed is active; only the original v23 full-stem timing is used for the beat.
- Vocal bus is reduced 1.5 dB from v23 with a smaller presence/air push.
- Added female-double intro chops before 9.20s are removed; the male main vocal is not cut.
- Kick and bass get a small extra texture pass with more saturation/body while trims keep the low end from jumping out.
- Main melody is lifted after resonance control: synth gets extra 1.18 kHz/3.15 kHz dynamic taming, then a small level/M/S lift.
- Vocal tune feel is increased with a very low parallel lead density layer; ReaTune remains present, but this is not note-by-note manual pitch editing.
- New female `0 Lead Vocals.wav` is not a lead: it is globally aligned, hard-gated by timing/pitch overlap, then added as a quiet panned double only where it passes.
- Female gate kept 22.523 s (0.1593) after 210.0 ms global correction.
- Old female candidates (`11 Backing_Vocals.wav` and v19 `0 Lead Vocals.wav`) remain muted as reference material.
- Revision from v26: kick/bass texture up, melody slightly more forward after resonance control, and vocal tune-edge layer added quietly.
- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.
- Status: genre_based_draft; this is a mix/master polish pass, not a reference-matched master.

## Deliverables

- REAPER project: `reaper/hangang_shadow_v27_kick_bass_melody_tune/hangang_shadow_mashup_v27_kick_bass_melody_tune.rpp`
- Premaster WAV: `renders/hangang_shadow_v27_kick_bass_melody_tune/hangang_shadow_mashup_v27_kick_bass_melody_tune_PREMASTER_24-48.wav`
- REAPER print WAV: `renders/hangang_shadow_v27_kick_bass_melody_tune/hangang_shadow_mashup_v27_kick_bass_melody_tune_REAPERPRINT_24-48.wav`
- Loud master WAV: `renders/hangang_shadow_v27_kick_bass_melody_tune/hangang_shadow_mashup_v27_kick_bass_melody_tune_MASTER_loud_24-48.wav`
- Loud master MP3: `renders/hangang_shadow_v27_kick_bass_melody_tune/hangang_shadow_mashup_v27_kick_bass_melody_tune_MASTER_loud_320k.mp3`

## Result

- Source full mix LUFS: -14.9 / true peak -2.6
- Final master LUFS: -8.9 / true peak -1.0
- Audible intent: keep the v23/v25 song feel while adding low-end texture, a clearer main melody, and a slightly tighter vocal tune impression.

## Metrics

| label | LUFS | LRA | true peak | peak | RMS | corr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| source_full_mix_reference | -14.9 | 3.2 | -2.6 | -2.62 | -16.99 | 0.9278 |
| synth_source_reference | -23.7 | 12.2 | -3.0 | -3.05 | -27.83 | 0.4489 |
| new_female_raw_candidate | -17.0 | 5.1 | -2.2 | -2.22 | -21.21 | 0.9552 |
| new_female_gated_no_intro_chops_layer | -28.0 | 12.1 | -11.1 | -11.1 | -38.16 | 0.99 |
| v27_reaper_premaster | -24.9 | 2.8 | -10.1 | -10.13 | -27.26 | 0.9519 |
| v27_reaper_print | -23.3 | 2.8 | -8.5 | -8.53 | -25.66 | 0.9519 |
| v27_final_master_loud | -8.9 | 1.8 | -1.0 | -1.0 | -11.29 | 0.9501 |
| v27_final_master_loud_mp3 | -8.9 | 1.8 | -0.7 | -0.82 | -11.29 | 0.95 |

## Main Moves

- V23 base preserved: active music uses the same original full-stem sources and item positions.
- Vocal bus: -1.5 dB from v23, with a smaller presence/air push to reduce the over-forward vocal feel.
- Intro chops: removed only the added female-double layer before 9.20s; original male lead and beat are untouched.
- Vocal tune: very low parallel lead density layer with fast compression, controlled saturation, and harshness control. This is a tune-feel support layer, not manual note correction.
- Kick/bass: saturation drive/mix and low body are raised slightly, with output trims to avoid breaking balance.
- Melody: synth is lifted from v26 but only after dynamic 1.18 kHz and 3.15 kHz resonance control plus high-tail taming.
- Female layer: new `0 Lead Vocals.wav` was shifted by the measured global lag, then only overlap frames passing chroma and local timing thresholds were kept.
- Stems: no v24 instrumental bed and no broad stem rebalance; the beat structure remains v23.
- Bass/kick: bass and drum stems get added saturation, low-end body, and dynamic low-mid control.
- Melody M/S: synth, keyboard, and woodwinds get side presence with a slight mid tuck so melody stays audible but embedded.
- Mix/master: conservative low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.
