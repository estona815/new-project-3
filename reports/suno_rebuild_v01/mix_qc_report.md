# Mix QC Report

## Detection Summary

- BPM/key: `162.0` BPM, `B minor`.
- Reference length: `141.394 s`; rebuilt render length: `141.394 s`.

## What Was Recreated

- Arrangement function, sad melodic density, half-time drum role, 808 support, and hook/verse/bridge energy curve.
- New MIDI/audio tracks for drums, 808, melody, and FX were generated and placed into a REAPER project.

## What Was Intentionally Changed

- Exact guide melodies, exact drum sequences, and Suno audio artifacts were not copied into the active render.
- The 808 is cleaner and less muddy, with ducking under kick hits.
- The high end is softer than the Suno reference to leave vocal space.

## Artifact Reduction

- Suno stems and full mix are muted in REAPER and excluded from the active production bus.
- No vocal stem, random voice texture, or AI top-noise layer was used in the final mix.
- Transitions were rebuilt from filtered noise/impact synthesis instead of separated reference audio.

## Metrics

| file | LUFS approx | peak | true peak approx | RMS | corr |
| --- | ---: | ---: | ---: | ---: | ---: |
| Suno reference | -19.831 | -4.61 | -4.604 | -17.853 | 0.9407 |
| full_mix | -10.861 | -1.0 | -0.994 | -7.322 | 0.997 |
| drums | -21.101 | -2.0 | -1.964 | -16.154 | 1.0 |
| bass | -15.485 | -2.08 | -2.074 | -12.21 | 1.0 |
| melody | -22.863 | -6.786 | -6.772 | -22.362 | 0.959 |
| fx | -42.593 | -24.508 | -24.48 | -51.014 | 0.9942 |
| reaper_sum_sanity | -19.32 | -2.299 | -2.293 | -16.05 | 0.9951 |

## QC Judgement

- MP3 320 encode: `passed`.
- REAPER project build: `reaper_cli_return_0`.
- REAPER active-stem render sanity: `reaper_render_return_0`.
- Clipping / true peak: final WAV peak is held under 0 dBFS; true peak is approximate, not a certified meter.
- Human-made feel: stronger than the Suno sketch because the active parts are newly programmed with humanized velocity, fills, and arrangement decisions.

## Remaining Weaknesses

- The render is a deterministic synthesized production, not a hand-played musician session.
- Key and structure are inferred from guide MIDI plus technical analysis; final user listening feedback should decide the next revision.
- REAPER MIDI tracks are guide/edit tracks; the reliable playback source is the printed rebuilt audio stems.

## Next Revision Suggestions

- Audition with the intended vocal and carve 1-4 kHz around the actual vocal tone.
- If the hook needs more lift, add a second bell octave only in bars 65-88 rather than raising drum level.
- If the 808 masks the vocal, reduce 90-140 Hz by 1-2 dB on the bass stem before mastering.
