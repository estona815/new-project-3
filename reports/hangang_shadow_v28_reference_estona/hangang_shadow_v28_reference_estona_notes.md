# Hangang Shadow v28 Reference Estona Notes

## Summary

- Source stance: full-stem `12 Vocals.wav` is the male main vocal.
- This version restarts from v23 because v24 changed the beat feel too much.
- No new instrumental bed is active; only the original v23 full-stem timing is used for the beat.
- Estona/Nib reference set was analyzed as a folder of 24/48 masters, then translated conservatively.
- Vocal remains slightly tucked from the earlier vocal-forward passes; presence/air are softened to avoid the synthetic top edge.
- Added female-double intro chops before 9.20s are removed; the male main vocal is not cut.
- Kick and bass get a reference-informed low texture pass: more 60-80 Hz density, more saturation, and extra low-mid control.
- Main melody is lifted by side/embedded M/S presence after 1.18 kHz and 3.15 kHz resonance control.
- Vocal tune feel is increased slightly with a quiet parallel lead density layer; ReaTune remains present, but this is not note-by-note manual pitch editing.
- New female `0 Lead Vocals.wav` is not a lead: it is globally aligned, hard-gated by timing/pitch overlap, then added as a quiet panned double only where it passes.
- Female gate kept 22.523 s (0.1593) after 210.0 ms global correction.
- Old female candidates (`11 Backing_Vocals.wav` and v19 `0 Lead Vocals.wav`) remain muted as reference material.
- Revision from v27: slightly wider music bed, controlled low-end density, less 1.5-5 kHz/air glare, and a slightly hotter but true-peak-safe loud master.
- Reference median: -6.0 LUFS / side-mid -12.23 dB / sub share 52.5375%.
- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.
- Status: genre_based_draft; this is a measured reference-informed polish pass, not a claim of identical reference matching.

## Deliverables

- REAPER project: `reaper/hangang_shadow_v28_reference_estona/hangang_shadow_mashup_v28_reference_estona.rpp`
- Premaster WAV: `renders/hangang_shadow_v28_reference_estona/hangang_shadow_mashup_v28_reference_estona_PREMASTER_24-48.wav`
- REAPER print WAV: `renders/hangang_shadow_v28_reference_estona/hangang_shadow_mashup_v28_reference_estona_REAPERPRINT_24-48.wav`
- Loud master WAV: `renders/hangang_shadow_v28_reference_estona/hangang_shadow_mashup_v28_reference_estona_MASTER_loud_24-48.wav`
- Loud master MP3: `renders/hangang_shadow_v28_reference_estona/hangang_shadow_mashup_v28_reference_estona_MASTER_loud_320k.mp3`

## Result

- Source full mix LUFS: -14.9 / true peak -2.6
- Final master LUFS: -8.5 / true peak -1.0
- Audible intent: keep the v23/v25/v27 song feel while pushing the master closer to the measured Estona/Nib reference traits.

## Metrics

| label | LUFS | LRA | true peak | peak | RMS | corr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| source_full_mix_reference | -14.9 | 3.2 | -2.6 | -2.62 | -16.99 | 0.9278 |
| synth_source_reference | -23.7 | 12.2 | -3.0 | -3.05 | -27.83 | 0.4489 |
| new_female_raw_candidate | -17.0 | 5.1 | -2.2 | -2.22 | -21.21 | 0.9552 |
| new_female_gated_no_intro_chops_layer | -28.0 | 12.1 | -11.1 | -11.1 | -38.16 | 0.99 |
| v28_reaper_premaster | -24.8 | 3.1 | -9.9 | -9.87 | -26.97 | 0.9432 |
| v28_reaper_print | -23.5 | 3.1 | -8.6 | -8.57 | -25.67 | 0.9432 |
| v28_final_master_loud | -8.5 | 1.6 | -1.0 | -1.0 | -10.92 | 0.9398 |
| v28_final_master_loud_mp3 | -8.5 | 1.6 | -0.7 | -0.73 | -10.92 | 0.9396 |

## Main Moves

- V23 base preserved: active music uses the same original full-stem sources and item positions.
- Vocal bus: stays tucked from the earlier vocal-forward passes, with less presence/air emphasis and slightly stronger de-ess/harshness control.
- Intro chops: removed only the added female-double layer before 9.20s; original male lead and beat are untouched.
- Vocal tune: quiet parallel lead density layer is a little more present, but still below the male main. This is a tune-feel support layer, not manual note correction.
- Kick/bass: saturation drive/mix and 60-80 Hz body are raised, with output trims and 200 Hz control to avoid boom.
- Melody: synth level/M/S readability is lifted only after dynamic 1.18 kHz and 3.15 kHz resonance control plus high-tail taming.
- Female layer: new `0 Lead Vocals.wav` was shifted by the measured global lag, then only overlap frames passing chroma and local timing thresholds were kept.
- Stems: no v24 instrumental bed and no broad stem rebalance; the beat structure remains v23.
- Reference translation: v27 measured narrower and less sub-dense than the reference median, so v28 adds music width and controlled low-end density without chasing the reference's clipped true peaks.
- Mix/master: low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.
