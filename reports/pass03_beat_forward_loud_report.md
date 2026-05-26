# Pass 03 Beat-Forward Loud Report

Generated: 2026-05-24T18:19:54

## User Direction
- Lower the vocal.
- Make the beat and main melody more obvious.
- Push loudness around -6 LUFS.

## Mix Moves
- Lowered 12_Vocals and MALE_LEAD_VOX_BUS relative to PASS02.
- Raised likely main melody/beat stems: 04_Synth, 07_Keyboard, 01_Woodwinds, 05_Strings, and MUSIC_BUS.
- Relaxed MUSIC_BUS ducking so the melody stays present under vocals.
- Kept late/problem female vocal layers muted.
- Tucked vocal reverb/delay further so the beat reads more clearly.
- Pushed Event Horizon harder for a loud review master.

## Metrics
| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| pass02_master | True | -1.0 | -9.07 | 2.9 | 0 | 0.992 |
| pass03_premaster | True | -11.98 | -26.2 | 3.44 | 0 | 0.99 |
| pass03_master | True | -1.0 | -5.64 | 3.32 | 0 | 0.99 |
| technical_reference | True | -0.1 | -6.11 | 1.59 | 0 | 0.938 |

## Tonal / Stereo Profile
| File | sub_20_120_db | mud_120_350_db | vocal_presence_1k_5k_db | sibilance_5k5_9k_db | side_150_400_db |
| --- | ---: | ---: | ---: | ---: | ---: |
| pass02_master | -19.2 | -19.04 | -18.15 | -34.28 | -43.42 |
| pass03_master | -12.5 | -15.26 | -15.47 | -30.89 | -38.51 |
| technical_reference | -10.53 | -14.96 | -17.65 | -26.51 | -28.11 |

## Interpretation
- PASS03 hits the requested loudness range: around -5.6 LUFS by local approximation.
- Clipping sample count is 0, and sample peak is -1.0 dBFS.
- LRA remains low, so this is intentionally loud/squeezed and must be checked by ear for pumping or vocal distortion.
- The beat and main melody should be more forward than PASS02 by level design.
