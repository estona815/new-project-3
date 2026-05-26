# Stem Quality Report

| stem | role | peak_dbfs | rms_dbfs | stereo_corr | status | phase |
| --- | --- | --- | --- | --- | --- | --- |
| 0101_backing_vocals_raw.wav | female_or_backing_vocal | -13.27 | -35.88 | 0.0578 | usable with cleanup | check width |
| 0101_bass808_raw.wav | bass_808 | -8.09 | -23.6 | 0.9474 | usable with cleanup | stable |
| 0101_brass_raw.wav | reference_only_sparse_or_aux | -55.2 | -106.62 | -0.2235 | reference only | check width |
| 0101_drums_raw.wav | drums | -3.77 | -21.94 | 0.9779 | usable with cleanup | stable |
| 0101_fx_raw.wav | fx_ambience | -2.77 | -36.1 | 0.5552 | usable with cleanup | stable |
| 0101_guitar_raw.wav | reference_only_sparse_or_aux | -55.53 | -106.64 | -0.257 | reference only | check width |
| 0101_keyboard_raw.wav | melody_keyboard | -6.37 | -25.3 | 0.0787 | usable with cleanup | check width |
| 0101_original_reference.wav | original_reference | -2.12 | -16.61 | 0.7903 | support/reference only | stable |
| 0101_original_reference_duplicate.wav | duplicate_reference | -2.12 | -16.61 | 0.7903 | reference only | stable |
| 0101_percussion_raw.wav | reference_only_sparse_or_aux | -54.45 | -106.58 | -0.2439 | reference only | check width |
| 0101_strings_raw.wav | reference_only_sparse_or_aux | -54.72 | -106.81 | -0.2333 | reference only | check width |
| 0101_synth_raw.wav | melody_synth | -9.92 | -36.81 | -0.4499 | usable with cleanup | check width |
| 0101_vocal_raw.wav | male_vocal | -5.82 | -24.46 | 1.0 | usable with cleanup | stable |
| 0101_woodwinds_raw.wav | reference_only_sparse_or_aux | -54.96 | -106.53 | -0.2605 | reference only | check width |

## Notes

- `0 0101.wav` is the main full-mix reference and remains muted/reference-only in the REAPER project.
- `1 0101.wav` is a duplicated full-mix reference from the working Studio session and is not used in the final mix.
- Woodwinds, Brass, Strings, Percussion, and Guitar are effectively sparse or near-silent support exports, so they are kept only as low-level melody/context material.
- `Vocals`, `Backing_Vocals`, `Drums`, `Bass`, `Keyboard`, `Synth`, and `FX` are usable after cleanup.
