# Pass 04 Final QC

Generated: 2026-05-24T18:42:42

## Metrics
| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| pass02_master | True | -1.0 | -9.07 | 2.9 | 0 | 0.992 |
| pass03_master | True | -1.0 | -5.64 | 3.32 | 0 | 0.99 |
| pass04_premaster | True | -13.19 | -26.91 | 4.55 | 0 | 0.99 |
| pass04_master | True | -1.0 | -6.49 | 4.37 | 0 | 0.99 |
| technical_reference | True | -0.1 | -6.11 | 1.59 | 0 | 0.938 |

## Tonal / Stereo Profile
| File | sub_20_120_db | mud_120_350_db | vocal_presence_1k_5k_db | sibilance_5k5_9k_db | side_150_400_db |
| --- | ---: | ---: | ---: | ---: | ---: |
| pass03_master | -12.5 | -15.26 | -15.47 | -30.89 | -38.51 |
| pass04_master | -12.19 | -15.9 | -16.81 | -32.11 | -38.81 |
| technical_reference | -10.53 | -14.96 | -17.65 | -26.51 | -28.11 |

## Answers
- Is the beat/main melody more forward than before? PASS04 level design raises MUSIC_BUS and main melody stems relative to the lowered vocal.
- Are the new Suno `000000` stems used safely? Yes, they are downloaded, imported, documented, and muted because they are not a full aligned replacement.
- Is the master only louder? No. PASS04 changes the mix balance before the limiter: vocal down, music up, FX tucked.
- Remaining human check: listen for limiter pumping at the loud target and confirm whether the original lead vocal artifacts are still acceptable.
- If the original lead still has pitch/formant tearing by ear, the answer remains: lead vocal requires regeneration or manual re-recording using voice `000000` with correct lyric input.
