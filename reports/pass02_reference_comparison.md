# Pass 02 Reference Comparison

The technical reference was reanalyzed for broad engineering direction only: clarity, depth, low-end discipline, dynamic movement, and stereo safety. No musical content was copied.

## Loudness And Dynamics
| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| previous_master | True | -1.0 | -10.08 | 2.16 | 0 | 0.873 |
| pass02_master | True | -1.0 | -9.07 | 2.9 | 0 | 0.992 |
| technical_reference | True | -0.1 | -6.11 | 1.59 | 0 | 0.938 |

## Tonal / Stereo Profile
| File | sub_20_120_db | mud_120_350_db | vocal_presence_1k_5k_db | sibilance_5k5_9k_db | side_150_400_db |
| --- | ---: | ---: | ---: | ---: | ---: |
| previous_master | -19.97 | -19.56 | -19.92 | -34.46 | -29.52 |
| pass02_master | -19.2 | -19.04 | -18.15 | -34.28 | -43.42 |
| technical_reference | -10.53 | -14.96 | -17.65 | -26.51 | -28.11 |

## Main Diagnosed PASS01 Problems
- BGV/secondary female material was not sufficiently controlled; one candidate behaves like a delayed second lead.
- Master loudness hid unfinished mix balance; LRA was too low for a lively commercial-feeling mix.
- Music/synth low-mid and 1-5 kHz content needed more space around the male lead.
- Delay/reverb needed to be phrase-event based rather than constant ambience.

## PASS02 Corrections
- Muted the late/problem female layers.
- Raised and centered the male lead while trimming music, bass, and ambience around it.
- Added actual fallback dynamic-EQ-style JSFX bands for vocal, music, bass, drums, and mix-bus control.
- Wrote music/FX ducking and phrase-end delay throw automation.
- Reduced master pressure before final safety limiting.

## Remaining Gap
- PASS02 is safer and more vocal-forward, but the measured LRA is still below the 5-8 LU target. Do not call it commercial-final until a human ear pass confirms vocal intelligibility and additional musical dynamics are ridden by hand.
