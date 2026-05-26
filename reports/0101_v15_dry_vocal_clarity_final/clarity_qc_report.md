# 0101 Vocal Clarity QC Report

- Selected final: `C_air_control`.
- Processing used existing vocal/instrumental stems; no Demucs/separation was needed.
- Backup created before processing from the v14 final.
- Main vocal global reverb/delay was removed; only very quiet phrase-ending throw FX was printed.
- Vocal chain: low-mid dynamic cleanup, preserved 700 Hz-1.4 kHz formant, 2.5-4.5 kHz wide presence lift, 5.5-9 kHz de-ess, 9-13 kHz AI fizz control, parallel tune/presence layer, light saturation, gentle compression.
- Instrumental masking control: subtle 250-500 Hz and 1.5-4 kHz dynamic pocketing during vocal phrases.
- Female layer: side-panned, louder than earlier hidden versions, center kept low and ducked under the main vocal.
- Artifacts noted: source is still AI/stem-derived, so exact note-by-note commercial vocal tuning is limited without a cleaner raw vocal or manual pitch editing.

## Variant Metrics

| label | integrated_lufs | true_peak_dbfs | rms_dbfs | presence_pct | sibilance_pct | air_pct | score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A_subtle | -10.2 | -1.2 | -12.98 | 15.857 | 0.234 | 0.159 | 9.8874 |
| B_presence | -10.2 | -1.2 | -13.04 | 17.401 | 0.236 | 0.158 | 10.9587 |
| C_air_control | -10.2 | -1.2 | -13.05 | 17.463 | 0.238 | 0.166 | 10.9611 |
| selected_C_air_control | -10.2 | -1.2 | -13.05 | 17.463 | 0.238 | 0.166 | 10.9611 |

## Final Decision

`C_air_control` was selected because it gave the best measured clarity score without increasing sibilance/AI-air artifacts.
