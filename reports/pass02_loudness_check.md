# Pass 02 Loudness Check

ffmpeg is unavailable in this shell, so this uses the same Python BS.1770-style approximation used in PASS01 plus sample peak and stereo correlation.

| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| previous_master | True | -1.0 | -10.08 | 2.16 | 0 | 0.873 |
| pass02_premaster | True | -9.75 | -24.66 | 2.89 | 0 | 0.992 |
| pass02_master | True | -1.0 | -9.07 | 2.9 | 0 | 0.992 |
| technical_reference | True | -0.1 | -6.11 | 1.59 | 0 | 0.938 |

True peak still needs confirmation with a real true-peak meter in REAPER or a third-party meter. Keep the limiter ceiling at or below -1.0 dBTP.
