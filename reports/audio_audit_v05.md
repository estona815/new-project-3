# mgmg mashup v05 audit

## Direction
- Male vocal remains the main lead.
- Female vocal is now deliberately louder and denser: continuous side double bed, phrase adlibs, response doubles, and vocal chops.
- Male tone is pushed toward the reference attitude with tighter formant, stronger tuned sheen, more compression/saturation, and less airy glass.
- Bass is rougher through mid-band saturation/clipping while keeping sub centered.

## Render audit
| label | file | duration_s | peak_dbfs | true_peak_dbfs | integrated_lufs | lra_lu | short_term_lufs_median | stereo_corr | side_mid_db |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v05_clean | mgmg_mashup_v05_more_female_tuned_grit_clean_24-48.wav | 109.6 | -2.36 | -1.2 | -9.5 | 1.5 | -9.5 | 0.9224 | -13.94 |
| v05_loud | mgmg_mashup_v05_more_female_tuned_grit_loud_24-48.wav | 109.6 | -2.1 | -1.2 | -8.3 | 1.4 | -8.3 | 0.92 | -13.8 |
| v05_preview_mp3 | mgmg_mashup_v05_preview.mp3 | 109.6 | -1.26 | -1.0 | -8.3 | 1.4 | -8.3 | 0.9199 | -13.8 |

## Reference audit
| label | file | integrated_lufs | lra_lu | true_peak_dbfs | stereo_corr | side_mid_db | sub_20_80_pct | body_200_500_pct | presence_1500_5000_pct | sibilance_5000_10000_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Am i 5u5ide? 320kbps | Am i 5u5ide? 320kbps.mp3 | -6.5 | 1.4 | 0.3 | 0.7238 | -7.95 | 44.36 | 10.053 | 5.17 | 2.947 |
| 030 320kbps | 030 320kbps.mp3 | -7.3 | 5.6 | 0.3 | 0.8336 | -10.42 | 18.431 | 26.795 | 5.388 | 3.171 |
| 00 320kbps | 00 320kbps.mp3 | -6.4 | 2.4 | 0.6 | 0.9165 | -13.6 | 46.462 | 11.308 | 6.693 | 3.571 |

## Female vocal use
- Phrase endings detected from male vocal: 25
- Female adlib/layer events used: 24
- Female chop placements generated: 57
- Female bed is a low-level wide double across the song, with sibilance softened.
| time_s | confidence | following_pause_s | long_tail |
| --- | --- | --- | --- |
| 4.587 | 0.522 | 0.171 | False |
| 5.995 | 0.488 | 0.192 | False |
| 12.395 | 0.461 | 0.192 | False |
| 15.317 | 0.461 | 0.192 | False |
| 18.24 | 0.548 | 0.363 | False |
| 20.736 | 0.479 | 0.235 | False |
| 21.845 | 0.5 | 0.256 | False |
| 24.085 | 0.545 | 0.363 | False |
| 25.024 | 0.475 | 0.171 | False |
| 28.395 | 0.486 | 0.213 | False |
| 29.867 | 0.484 | 0.256 | False |
| 40.491 | 0.475 | 0.235 | False |
| 53.781 | 0.456 | 0.171 | False |
| 55.04 | 0.452 | 0.171 | False |
| 56.875 | 0.491 | 0.171 | False |
| 57.813 | 0.452 | 0.171 | False |
| 69.397 | 0.55 | 0.32 | False |
| 71.424 | 0.46 | 0.171 | False |
| 73.131 | 0.564 | 0.299 | False |
| 77.44 | 0.543 | 0.213 | False |
| 79.253 | 0.456 | 0.171 | False |
| 82.773 | 0.452 | 0.171 | False |
| 90.859 | 0.538 | 0.256 | False |
| 92.8 | 1.0 | 8.363 | True |

## Limits
- The tuned male layer is a DSP approximation, not actual note-by-note Auto-Tune/Melodyne.
- The reference singer identity is not cloned; only mix/tone behavior is approximated.
- Final subjective balance still needs listening, especially whether female layers are now too loud.
