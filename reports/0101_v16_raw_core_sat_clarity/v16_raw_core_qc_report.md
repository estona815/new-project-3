# v16 Raw Core QC Report

- Cause found: v15 processed male reduced the raw 700 Hz-1.5 kHz formant core too much and pushed 1.5-5 kHz presence too hard.
- v16 starts directly from `0101_vocal_raw.wav`, with only light cleanup, saturation, preserved body/formant, and a small clarity parallel.
- No global reverb/delay and no phrase throw FX in this pass.
- Female layer remains side support only, lower than the raw main vocal so it does not blur the center.

| label | integrated_lufs | true_peak_dbfs | rms_dbfs | formant_pct | presence_pct | sibilance_pct | air_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| raw_vocal_reference | -19.9 | -5.8 | -24.46 | 37.954 | 14.911 | 3.935 | 1.772 |
| v15_processed_male_reference | -11.6 | -1.1 | -16.68 | 19.744 | 39.346 | 0.068 | 0.085 |
| v16_processed_male_raw_core | -16.7 | -1.8 | -21.36 | 25.931 | 25.166 | 0.695 | 0.507 |
| v15_final_reference | -10.2 | -1.2 | -13.05 | 24.625 | 17.463 | 0.238 | 0.166 |
| v16_final_wav | -10.5 | -1.2 | -12.85 | 25.682 | 8.054 | 0.559 | 0.384 |
| v16_final_mp3 | -10.5 | -1.1 | -12.85 | 25.681 | 8.055 | 0.559 | 0.384 |
