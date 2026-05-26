# Hangang Shadow v22 Lifted Stems Bass/Kick Notes

## Summary

- Source stance: full-stem `12 Vocals.wav` is the male main vocal.
- Female material is not the lead: automated alignment check did not prove timing safety, so `11 Backing_Vocals.wav` and v19 `0 Lead Vocals.wav` are muted as reference material.
- Revision from v21: male lead down 1 dB, music stems lifted, bass/drum saturation added, and melody stems shaped with M/S tuck.
- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.
- Status: genre_based_draft; this is a mix/master polish pass, not a reference-matched master.

## Deliverables

- REAPER project: `reaper/hangang_shadow_v22_lifted_stems_bass_kick/hangang_shadow_mashup_v22_lifted_stems_bass_kick.rpp`
- Premaster WAV: `renders/hangang_shadow_v22_lifted_stems_bass_kick/hangang_shadow_mashup_v22_lifted_stems_bass_kick_PREMASTER_24-48.wav`
- REAPER print WAV: `renders/hangang_shadow_v22_lifted_stems_bass_kick/hangang_shadow_mashup_v22_lifted_stems_bass_kick_REAPERPRINT_24-48.wav`
- Loud master WAV: `renders/hangang_shadow_v22_lifted_stems_bass_kick/hangang_shadow_mashup_v22_lifted_stems_bass_kick_MASTER_loud_24-48.wav`
- Loud master MP3: `renders/hangang_shadow_v22_lifted_stems_bass_kick/hangang_shadow_mashup_v22_lifted_stems_bass_kick_MASTER_loud_320k.mp3`

## Result

- Source full mix LUFS: -14.9 / true peak -2.6
- Final master LUFS: -9.0 / true peak -1.0
- Audible intent: male voice stays in front but 1 dB less dominant; bass/kick feel denser; main melody is audible from the sides without sitting on top.

## Metrics

| label | LUFS | LRA | true peak | peak | RMS | corr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| source_full_mix_reference | -14.9 | 3.2 | -2.6 | -2.62 | -16.99 | 0.9278 |
| v22_reaper_premaster | -25.1 | 3.0 | -10.1 | -10.13 | -27.37 | 0.9325 |
| v22_reaper_print | -23.5 | 3.0 | -8.5 | -8.53 | -25.77 | 0.9325 |
| v22_final_master_loud | -9.0 | 1.8 | -1.0 | -1.0 | -11.36 | 0.93 |
| v22_final_master_loud_mp3 | -9.0 | 1.8 | -0.6 | -0.6 | -11.36 | 0.9298 |

## Main Moves

- Male lead: high-pass cleanup, low-mid dip, 3 kHz presence lift, gentle air, 1.7:1 leveling, light saturation.
- Female layer: muted after alignment check; it is kept in the REAPER project only for manual adlib editing if needed.
- Stems: active music stems raised from v21 while reference/female-lead/artifact tracks remain muted.
- Bass/kick: bass and drum stems get added saturation, low-end body, and dynamic low-mid control.
- Melody M/S: synth, keyboard, and woodwinds get side presence with a slight mid tuck so melody stays audible but embedded.
- Mix/master: conservative low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.
