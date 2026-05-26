# Final QC Report

| version | duration_s | integrated_lufs | true_peak_dbfs | peak_dbfs | rms_dbfs | stereo_corr |
| --- | --- | --- | --- | --- | --- | --- |
| female_qc_support_wav | 139.441 | -11.6 | -1.2 | -1.22 | -14.5 | 0.838 |
| female_qc_support_mp3 | 139.441 | -11.6 | -1.1 | -1.14 | -14.5 | 0.8379 |
| male_only_safety_wav | 139.441 | -11.5 | -1.2 | -1.23 | -14.58 | 0.8491 |
| male_only_safety_mp3 | 139.441 | -11.5 | -1.1 | -1.1 | -14.58 | 0.8491 |
| processed_male_vocal | 139.441 | -21.1 | -2.0 | -2.0 | -25.95 | 0.9996 |
| processed_female_qc_support | 139.441 | -22.7 | -8.1 | -8.1 | -29.0 | 0.5701 |

## Notes

- 메인 렌더는 `0101_FINAL_female_qc_support.wav`이다.
- 여자 보컬은 전체가 아니라 QC 통과 구간만 들어가며, 보컬 중심은 남자 리드다.
- 전처럼 이상하게 튀는 가사/음정/엇박 구간은 마스크에서 닫히도록 했다.
- 리버브/딜레이는 짧고 어둡게 넣고 남자 보컬에 사이드체인으로 밀리게 했다.
- MP3도 320kbps로 렌더했다.

## Deliverables

- `/Users/hantaeheuk/Documents/New project 3/renders/0101_female_candidate_v10_qc_support/0101_FINAL_female_qc_support.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_female_candidate_v10_qc_support/0101_FINAL_female_qc_support_320.mp3`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_female_candidate_v10_qc_support/0101_FINAL_male_only_safety.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_female_candidate_v10_qc_support/0101_FINAL_male_only_safety_320.mp3`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_female_candidate_v10_qc_support/processed_male_vocal_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_female_candidate_v10_qc_support/processed_female_qc_support_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/reaper/0101_female_candidate_v10_qc_support/0101_REAPER_FEMALE_QC_SUPPORT_PROJECT.rpp`
