# mgmg mashup v04 audit

## Direction correction
- Male vocal from the earlier stem zip is the main vocal foundation.
- Female vocal from the newer `(1)` zip is used only as adlibs, phrase-end layers, and occasional vocal chops.
- Female drums/bass/music stems from the newer zip were not used.

## Render audit
| label | file | duration_s | peak_dbfs | true_peak_dbfs | integrated_lufs | lra_lu | short_term_lufs_median | stereo_corr | side_mid_db |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v04_clean | mgmg_mashup_v04_male_main_female_adlibs_clean_24-48.wav | 109.6 | -2.51 | -1.2 | -9.7 | 1.5 | -9.6 | 0.944 | -15.4 |
| v04_loud | mgmg_mashup_v04_male_main_female_adlibs_loud_24-48.wav | 109.6 | -2.17 | -1.2 | -8.5 | 1.6 | -8.5 | 0.9409 | -15.16 |
| v04_preview_mp3 | mgmg_mashup_v04_preview.mp3 | 109.6 | -1.5 | -1.1 | -8.5 | 1.6 | -8.5 | 0.9408 | -15.16 |

## Reference audit
| label | file | integrated_lufs | lra_lu | true_peak_dbfs | stereo_corr | side_mid_db | sub_20_80_pct | body_200_500_pct | formant_500_1500_pct | presence_1500_5000_pct | sibilance_5000_10000_pct | air_10000_16000_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Am i 5u5ide? 320kbps | Am i 5u5ide? 320kbps.mp3 | -6.5 | 1.4 | 0.3 | 0.7238 | -7.95 | 44.36 | 10.053 | 12.245 | 5.17 | 2.947 | 1.492 |
| 030 320kbps | 030 320kbps.mp3 | -7.3 | 5.6 | 0.3 | 0.8336 | -10.42 | 18.431 | 26.795 | 16.734 | 5.388 | 3.171 | 0.874 |
| 00 320kbps | 00 320kbps.mp3 | -6.4 | 2.4 | 0.6 | 0.9165 | -13.6 | 46.462 | 11.308 | 11.672 | 6.693 | 3.571 | 2.58 |

## Male main stems
| file | role | duration_s | peak_dbfs | rms_dbfs | stereo_corr | side_mid_db |
| --- | --- | --- | --- | --- | --- | --- |
| 0 Lead Vocals.wav | lead_vocal | 109.6 | -3.24 | -24.02 | 0.9835 | -20.79 |
| 1 Backing Vocals.wav | backing_vocal | 109.6 | -10.57 | -37.15 | -0.1271 | 1.1 |
| 2 Drums.wav | drums | 109.6 | -2.41 | -21.98 | 0.9985 | -31.39 |
| 3 Bass.wav | bass | 109.6 | -3.47 | -22.52 | 0.9951 | -26.11 |
| 4 Keyboard.wav | keys | 109.6 | -6.39 | -32.43 | 0.42 | -3.88 |
| 5 Percussion.wav | percussion | 109.6 | -2.44 | -47.68 | 0.8479 | -10.84 |
| 6 Synth.wav | synth | 109.6 | -3.58 | -31.67 | 0.4921 | -4.65 |
| 7 Other.wav | other | 109.6 | -5.91 | -33.85 | 0.9473 | -15.68 |

## Female source stems
| file | role | duration_s | peak_dbfs | rms_dbfs | stereo_corr | side_mid_db |
| --- | --- | --- | --- | --- | --- | --- |
| 0 Lead Vocals.wav | female_lead_source | 109.6 | -3.05 | -23.71 | 0.9744 | -18.87 |
| 1 Backing Vocals.wav | female_backing_source | 109.6 | -14.19 | -48.31 | 0.065 | -0.57 |

## Vocal routing
- Male lead: cleanup, dynamic de-harsh/de-ess, light saturation, 1176/LA-style controlled compression, front position.
- Male backing: tucked support under the male lead.
- Female adlib/layer bus: phrase-end gated, alternating left/right pan, filtered and softened so it does not replace the lead.
- Female chop bus: selected short 105 ms snippets after important phrase endings, alternating pan, some reverse chops, filtered 260 Hz-7.2 kHz.
- FX returns are ducked from the male vocal bus, so reverb/delay should bloom after lines instead of covering the main vocal.
- Reference response: sub/low-end density and restrained air were used as the tonal guide; unsafe positive true peaks in the MP3 references were not copied.

## Phrase/adlib selection
- Phrase endings detected from male vocal: 36
- Female adlib/layer events used: 9
- Female chop placements generated: 11
| time_s | confidence | following_pause_s | long_tail |
| --- | --- | --- | --- |
| 3.563 | 0.621 | 0.299 | False |
| 24.085 | 0.554 | 0.384 | False |
| 34.24 | 0.6 | 0.512 | False |
| 61.163 | 0.596 | 0.384 | False |
| 69.461 | 0.584 | 0.384 | False |
| 71.424 | 0.537 | 0.363 | False |
| 73.109 | 0.701 | 0.661 | False |
| 90.901 | 0.582 | 0.213 | False |
| 92.8 | 1.0 | 16.811 | True |

## QC notes
- Stem separation was not needed because both male and female vocal stems were available.
- Clean/loud masters are true-peak-safe and non-destructive; v03 files were not overwritten.
- This is a measured DSP render. Final call still needs playback listening for whether female chops are too frequent or too quiet.
