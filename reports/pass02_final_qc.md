# Pass 02 Final QC

| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| previous_master | True | -1.0 | -10.08 | 2.16 | 0 | 0.873 |
| pass02_premaster | True | -9.75 | -24.66 | 2.89 | 0 | 0.992 |
| pass02_master | True | -1.0 | -9.07 | 2.9 | 0 | 0.992 |
| technical_reference | True | -0.1 | -6.11 | 1.59 | 0 | 0.938 |

## Explicit Answers
- Is the vocal more commercial and forward than before? Yes in routing/level design: the lead was raised and competing female layers were muted; confirm by ear.
- Is the instrumental less masking? Yes by automation/design: MUSIC_BUS is lower and dynamically ducked around vocal phrases.
- Is the reverb/delay more controlled? Yes by routing/design: send levels are lower and delay is phrase-throw automation, not constant haze.
- Is the stereo image safer? Yes by metric screen; no immediate anti-phase warning.
- Is the master less flat than the previous version? Improved from about 2.16 LU to 2.9 LU, but still below the 5-8 LU target; this needs manual riding/source dynamics to become truly alive.
- Clipping status: No sample clipping detected.

## Remaining Human Corrections
- Listen on small speakers for lead intelligibility before calling this final.
- Manually tune marked lead phrases if pitch/formant instability is audible.
- If the lead stem has severe AI tearing, it requires regeneration or manual re-recording.
