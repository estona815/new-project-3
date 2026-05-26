# Hangang Shadow v28 Estona Reference Analysis

## Scope

- Reference material: Estona/Nib 24-bit 48 kHz master WAV set from the user-provided folder.
- Comparison basis: final v28, baseline v27, and original full mix.
- Status: genre_based_draft; this is measured reference-informed direction, not an identical match claim.

## Reference Median vs Final v28

| metric | reference median | final v28 | v28 - ref | v28 - v27 |
| --- | ---: | ---: | ---: | ---: |
| integrated_lufs | -6.0 | -8.5 | -2.5 | 0.4 |
| lra_lu | 6.15 | 1.6 | -4.55 | -0.2 |
| true_peak_dbfs | 1.4 | -1.0 | -2.4 | 0.0 |
| rms_dbfs | -7.455 | -10.92 | -3.465 | 0.37 |
| crest_db | 7.455 | 9.92 | 2.465 | -0.37 |
| stereo_corr | 0.8871 | 0.9398 | 0.0527 | -0.0103 |
| side_mid_db | -12.23 | -15.08 | -2.85 | 0.84 |
| sub_20_80_pct | 52.5375 | 31.288 | -21.2495 | 0.544 |
| bass_body_80_200_pct | 18.809 | 24.472 | 5.663 | 0.486 |
| body_200_500_pct | 10.6095 | 7.24 | -3.3695 | -0.181 |
| formant_500_1500_pct | 9.572 | 25.13 | 15.558 | -0.499 |
| presence_1500_5000_pct | 5.0825 | 8.321 | 3.2385 | -0.311 |
| sibilance_5000_10000_pct | 1.8875 | 2.456 | 0.5685 | -0.059 |
| air_10000_16000_pct | 0.522 | 1.093 | 0.571 | 0.019 |
| short_term_lufs_median | -5.9 | -8.5 | -2.6 | 0.4 |
| short_term_lufs_max | -4.45 | -7.3 | -2.85 | 0.4 |

## Baseline v27

| metric | v27 | final v28 |
| --- | ---: | ---: |
| integrated_lufs | -8.9 | -8.5 |
| lra_lu | 1.8 | 1.6 |
| true_peak_dbfs | -1.0 | -1.0 |
| rms_dbfs | -11.29 | -10.92 |
| crest_db | 10.29 | 9.92 |
| stereo_corr | 0.9501 | 0.9398 |
| side_mid_db | -15.92 | -15.08 |
| sub_20_80_pct | 30.744 | 31.288 |
| bass_body_80_200_pct | 23.986 | 24.472 |
| body_200_500_pct | 7.421 | 7.24 |
| formant_500_1500_pct | 25.629 | 25.13 |
| presence_1500_5000_pct | 8.632 | 8.321 |
| sibilance_5000_10000_pct | 2.515 | 2.456 |
| air_10000_16000_pct | 1.074 | 1.093 |
| short_term_lufs_median | -8.9 | -8.5 |
| short_term_lufs_max | -7.7 | -7.3 |

## Per-Reference Metrics

| label | LUFS | LRA | true peak | RMS | crest | side/mid | sub | bass body | low-mid | presence | sibilance | air |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ref_Broken | -6.0 | 9.4 | 1.9 | -7.35 | 7.35 | -12.19 | 52.346 | 27.381 | 9.998 | 2.243 | 1.876 | 0.715 |
| ref_Dough | -6.2 | 6.7 | 1.2 | -7.42 | 7.42 | -9.26 | 59.084 | 17.833 | 6.912 | 5.702 | 2.115 | 0.446 |
| ref_IMnK | -6.0 | 2.4 | 1.5 | -8.6 | 8.5 | -10.88 | 37.12 | 19.785 | 11.221 | 10.659 | 3.558 | 1.545 |
| ref_Lovee | -6.3 | 7.6 | 1.5 | -7.35 | 7.35 | -12.58 | 56.746 | 21.758 | 9.406 | 3.429 | 1.536 | 0.473 |
| ref_Missu | -6.0 | 5.6 | 1.4 | -7.49 | 7.49 | -6.21 | 52.729 | 19.827 | 13.106 | 3.642 | 1.973 | 0.467 |
| ref_Phobia | -6.0 | 1.3 | 1.4 | -7.57 | 7.56 | -12.27 | 45.065 | 15.339 | 15.171 | 6.87 | 1.899 | 0.437 |
| ref_Stuck in Seoul | -6.0 | 1.4 | 1.1 | -7.63 | 7.53 | -14.92 | 47.979 | 14.944 | 16.493 | 6.479 | 1.792 | 0.65 |
| ref_Why | -6.0 | 7.2 | 0.5 | -7.4 | 7.3 | -14.32 | 60.815 | 13.728 | 7.918 | 4.463 | 1.619 | 0.571 |
| source_full_mix | -14.9 | 3.2 | -2.6 | -16.99 | 14.37 | -14.26 | 37.044 | 27.26 | 6.604 | 6.812 | 2.904 | 1.413 |
| baseline_v27_premaster | -24.9 | 2.8 | -10.1 | -27.26 | 17.13 | -16.08 | 32.339 | 24.857 | 7.01 | 8.341 | 2.368 | 1.015 |
| baseline_v27_master | -8.9 | 1.8 | -1.0 | -11.29 | 10.29 | -15.92 | 30.744 | 23.986 | 7.421 | 8.632 | 2.515 | 1.074 |
| final_v28_premaster | -24.8 | 3.1 | -9.9 | -26.97 | 17.1 | -15.34 | 34.908 | 25.543 | 6.405 | 7.645 | 2.209 | 0.987 |
| final_v28_master | -8.5 | 1.6 | -1.0 | -10.92 | 9.92 | -15.08 | 31.288 | 24.472 | 7.24 | 8.321 | 2.456 | 1.093 |

## Translation Into v28

- Keep male vocal main and female layer tucked; no broad vocal lift.
- Move low-end density toward the reference set with controlled kick/bass saturation and 80-200 Hz body, while keeping sub mono and clipped safely.
- Make the main melody more readable by removing resonant bite first, then adding a small embedded presence lift.
- Reduce synthetic top glare instead of simply boosting air.
- Use slightly stronger bus glue and limiter conditioning only after checking true peak.
