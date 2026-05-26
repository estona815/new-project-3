# Final Render QC

| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| premaster | True | -10.84 | -25.07 | 2.17 | 0 | 0.873 |
| master | True | -1.0 | -10.08 | 2.16 | 0 | 0.873 |

## Interpretation
- No sample clipping detected in the rendered master.
- Dynamic warning: LRA is very low; the premaster was already low-movement, so manual level automation or source regeneration is needed for a more natural 5-8 LU target.
- Stereo correlation is not showing an immediate anti-phase warning.
- Vocal masking and tonal balance still require human ear review in REAPER.
