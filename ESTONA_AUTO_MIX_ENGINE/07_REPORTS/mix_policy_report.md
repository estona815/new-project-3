# Mix Policy Report

## A. 코드가 측정한 사실
- See current, masking, pitch, and saturation JSON analysis files.

## B. 정책 엔진이 추천한 수정
- lead_vocal_gain_db: 2.0 — Current vocal-to-beat ratio is -1.08 dB; target is a conservative user-approved balance around 1.5 dB.
- backing_vocal_gain_db: -3.77 — Backing intrusion score is 1.89; female backing must not take over the male lead.
- adlib_gate_strength: 1.0 — Gate strength follows backing overlap so adlibs stay in phrase gaps where possible.
- backing_center_reduction: 1.0 — Center reduction protects lead-vocal dominance when backing presence overlaps 1k-4k.
- backing_width_increase: 0.8 — Wider backing keeps doubles/adlibs supportive instead of lead-like.
- vocal_body_boost_db: 0.0 — Vocal thin/AI score is 0.00; add body while avoiding harsh top boost.
- vocal_harsh_dynamic_cut_db: 0.0 — Harshness band proxy is -30.91 dB and pitch snap score is 0.00.
- deess_amount: 0.0 — Sibilance band proxy is -30.75 dB relative to safety threshold.
- vocal_parallel_saturation_amount: 0.0 — Parallel saturation follows vocal thinness 0.00, saturation shortage 0.35, and overbright risk 1.00.
- beat_bus_saturation_amount: 0.51 — Beat harmonic body 4.30, reference median 8.31, saturation shortage 0.35, and overbright risk 1.00 set drive conservatively.
- drum_clip_drive: 0.26 — Soft clip drive supports digicore energy while avoiding a flat overcompressed master.
- 808_upper_harmonic_amount: 1.0 — 808 phone translation proxy is -90.31; upper harmonics help small-speaker audibility.
- 808_mud_reduction_db: 0.0 — Mud reduction is applied only when 100-250 Hz energy appears excessive.
- mono_sub_crossover_hz: 120 — Sub below 120 Hz defaults to mono-compatible protection.
- mono_sub_amount: 0.75 — Mono sub guard prevents side low-end from weakening translation.
- vocal_beat_glue_amount: 1.0 — Vocal/beat glue score is 0.00; apply gentle bus glue only as needed.

## C. 사용자가 청감으로 확인해야 하는 항목
- 보컬이 너무 앞으로 튀는지
- 여자 더블이 리드처럼 들리는지
- 808이 폰에서도 들리는지
- 고역이 피곤한지
