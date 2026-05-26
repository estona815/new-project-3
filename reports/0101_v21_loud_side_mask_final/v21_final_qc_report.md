# v21 Final QC Report

- Applied requested methods 2, 3, and 6.
- Method 2: raw vocal redesign with harmonic/body/formant layer under the original core.
- Method 3: consonant layer for perceived lyric articulation.
- Method 6: sibilance/AI fizz separated and controlled before presence is added.
- Required tune/noise chain remains included as controlled parallel, not replacing the main core.
- Female side layer is +1 dB louder than v18.
- Male vocal mix gain is +0.20 dB over v19.
- Broadband instrumental ducking is removed; only band-limited dynamic pockets react to the male vocal.
- Loud final target is -6.0 LUFS with true-peak-safe limiting.
- Vocal fizz triggers a reverse-sidechain side mask from panned piano/synth melody texture.
- Endpoint throw delay/reverb is kept; no global vocal reverb/delay.

| label | integrated_lufs | true_peak_dbfs | rms_dbfs | formant_pct | presence_pct | sibilance_pct | air_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| raw_vocal_reference | -19.9 | -5.8 | -24.46 | 37.954 | 14.911 | 3.935 | 1.772 |
| v18_reference | -10.0 | -1.2 | -12.8 | 26.443 | 14.424 | 0.377 | 0.255 |
| v21_male_redesigned_stem | -17.0 | -1.7 | -21.78 | 33.47 | 27.615 | 0.392 | 0.243 |
| v21_female_plus1_more_stem | -17.6 | -3.0 | -23.95 | 40.611 | 34.105 | 0.201 | 0.086 |
| v21_endpoint_throw_fx_stem | -46.5 | -31.0 | -62.93 | 22.338 | 44.071 | 0.236 | 0.207 |
| v21_instrumental_pocket_no_broadband_duck_stem | -19.8 | -1.8 | -22.12 | 26.381 | 3.476 | 0.643 | 0.38 |
| v21_side_noise_mask_piano_synth_stem | -34.9 | -7.9 | -44.12 | 0.0 | 0.0 | 0.0 | 0.0 |
| v20_reference | -10.3 | -1.2 | -12.68 | 26.857 | 9.3 | 0.465 | 0.291 |
| v21_final_wav | -6.2 | -1.2 | -8.65 | 26.923 | 9.865 | 0.548 | 0.326 |
| v21_final_mp3 | -6.2 | -1.0 | -8.65 | 26.923 | 9.865 | 0.548 | 0.327 |
