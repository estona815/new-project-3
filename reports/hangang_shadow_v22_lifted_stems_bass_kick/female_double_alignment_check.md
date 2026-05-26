# Female Double Alignment Check

- Male source: `12 Vocals.wav`
- Female source: `11 Backing_Vocals.wav`

## Metrics

- same_sample_rate: True
- duration_s: 141.394
- length_difference_samples: 0
- envelope_best_lag_ms_positive_female_late: 0.0
- envelope_lag_corr: 0.0843
- male_active_frames_100hz: 6354
- female_active_frames_100hz: 3372
- overlap_frames_100hz: 1370
- female_active_overlaps_male_ratio: 0.4063
- male_active_has_female_ratio: 0.2156
- pitch_class_similarity_frame_count: 313
- pitch_class_similarity_median: 0.8934
- pitch_class_similarity_p10: 0.7441
- pitch_class_similarity_p90: 0.9627
- timing_likely_aligned: False
- pitch_class_likely_compatible: True
- female_safe_as_low_double: False
- verdict: not_safe_as_audible_double_without_manual_edit

## Note

This is an automated timing/envelope and octave-insensitive chroma check. It does not prove exact note-by-note pitch correction; use it to decide whether the female layer should stay low or be muted.
