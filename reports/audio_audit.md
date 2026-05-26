# Audio Audit

## Source And Render Metrics
| label | file | duration_s | peak_dbfs | true_peak_dbfs | integrated_lufs | lra_lu | short_term_lufs_median | stereo_corr | side_mid_db |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| target_v04_clean | mgmg_mashup_v04_male_main_female_adlibs_clean_24-48.wav | 109.6 | -2.51 | -1.2 | -9.7 | 1.5 | -9.6 | 0.944 | -15.4 |
| voice_reference_master | Am i 5u5ide? 320kbps.mp3 | 145.104 | 0.17 | 0.3 | -6.5 | 1.4 | -6.2 | 0.7238 | -7.95 |
| voice_reference_proxy | reference_vocal_proxy.wav | 145.104 | -6.0 | -5.9 | -16.5 | 2.7 | -16.3 | 1.0 | -240.0 |
| v05_original_voice_match_natural | mgmg_mashup_v05_original_voice_match_natural_24-48.wav | 109.6 | -1.9 | -1.2 | -8.9 | 1.5 | -8.9 | 0.9222 | -13.93 |
| v05_original_voice_match_loud | mgmg_mashup_v05_original_voice_match_loud_24-48.wav | 109.6 | -2.01 | -1.2 | -8.3 | 1.4 | -8.3 | 0.9203 | -13.82 |
| v05_original_voice_match_ref_loud | mgmg_mashup_v05_original_voice_match_ref_loud_24-48.wav | 109.6 | -1.88 | -1.2 | -7.6 | 1.6 | -7.6 | 0.9185 | -13.72 |
| v05_preview_320 | mgmg_mashup_v05_preview_320.mp3 | 109.6 | -1.31 | -1.0 | -8.3 | 1.4 | -8.3 | 0.9203 | -13.82 |

## Level Matched Comparison
- Target v04 clean: -9.7 LUFS.
- Voice reference master: -6.5 LUFS.
- For fair A/B, turn reference down by -3.2 dB when comparing to target.
- Reference true peak/clipping is intentionally not copied.

## Analysis Notes
- Target processing used stems available from the previous stem zips.
- Reference vocal extraction used a vocal-dominant mid/high proxy because Demucs is not installed in this environment.
- Stem separation artifact risk was avoided for the target because direct male/female stems exist.
