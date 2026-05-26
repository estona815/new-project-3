# Premaster Master Execution

The project was saved as FRESH_MIX_MASTER_PASS_01.rpp. Render prep creates separate premaster and master temp projects.

- Premaster render bypasses PRINT_MASTER_BUS FX.
- Master render enables PRINT_MASTER_BUS ReaLimit safety chain.
- Master goal is conservative review loudness, not a crushed final release.
- True peak is not measured by ffmpeg because ffmpeg is unavailable in shell; post-render Python reports sample peak and approximate LUFS/LRA.

| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| premaster | True | -10.84 | -25.07 | 2.17 | 0 | 0.873 |
| master | True | -1.0 | -10.08 | 2.16 | 0 | 0.873 |
