# Pass 02 Master Pressure Reset

PASS02 does not try to fix the mix by simply pushing the limiter.

- Premaster render bypasses PRINT_MASTER_BUS FX.
- Final master render enables the safety/master chain only after balance changes.
- Event Horizon is bypassed for the premaster/balance render.
- Final review master uses Event Horizon around -16.6 dB threshold with a -1 dB ceiling after the balance pass.
- The goal is to expose and correct the real mix balance before loudness.

| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| previous_master | True | -1.0 | -10.08 | 2.16 | 0 | 0.873 |
| pass02_premaster | True | -9.75 | -24.66 | 2.89 | 0 | 0.992 |
| pass02_master | True | -1.0 | -9.07 | 2.9 | 0 | 0.992 |
| technical_reference | True | -0.1 | -6.11 | 1.59 | 0 | 0.938 |
