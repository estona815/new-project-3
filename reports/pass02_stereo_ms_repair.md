# Pass 02 Stereo M/S Repair

- Kick, bass, snare focus, and male lead remain centered.
- MUSIC_BUS and BGV width are restrained by lowering competing layers instead of fake widening.
- 260-300 Hz low-mid cleanup was added as a mono-compatibility proxy where full M/S EQ automation is unavailable.
- Render QC checks stereo correlation and side low-mid energy.

## Render Band Profile
| File | sub_20_120_db | mud_120_350_db | vocal_presence_1k_5k_db | sibilance_5k5_9k_db | side_150_400_db |
| --- | ---: | ---: | ---: | ---: | ---: |
| previous_master | -19.97 | -19.56 | -19.92 | -34.46 | -29.52 |
| pass02_master | -19.2 | -19.04 | -18.15 | -34.28 | -43.42 |
| technical_reference | -10.53 | -14.96 | -17.65 | -26.51 | -28.11 |
