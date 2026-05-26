# Loudness Check

ffmpeg ebur128 is unavailable in this shell. This report uses a local Python BS.1770-style approximation for integrated loudness and LRA, plus sample peak checks.

| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| premaster | True | -10.84 | -25.07 | 2.17 | 0 | 0.873 |
| master | True | -1.0 | -10.08 | 2.16 | 0 | 0.873 |

True peak oversampling is not available here; keep REAPER limiter ceiling conservative around -1.0 dBTP and confirm with a true-peak meter manually.
