# Final QC Report

| version | duration_s | integrated_lufs | true_peak_dbfs | peak_dbfs | rms_dbfs | stereo_corr |
| --- | --- | --- | --- | --- | --- | --- |
| dual_voice_layer_wav | 139.441 | -11.4 | -1.2 | -1.23 | -14.27 | 0.1713 |
| new_dual_voice_alt_wav | 139.441 | -11.6 | -1.2 | -1.23 | -14.42 | 0.1552 |
| male_lead_new_voice_support_wav | 139.441 | -11.5 | -1.2 | -1.23 | -14.37 | 0.1765 |

## QC Notes

- 메인 추천본은 `0101_FINAL_male_ref_female_overlap.wav`이다.
- 새 두목소리 보컬은 실제 Suno 생성 보컬을 사용했고, 이전 피치변환식 여자 레이어는 제외했다.
- 남자 보컬은 lead/reference 역할을 유지했고, 추가 dynamic EQ와 spectral denoise로 노이즈/레조넌스를 더 정리했다.
- 여자/두목소리 레이어는 남자 보컬과 박자/phrase가 맞는 local timing window에서만 열린다.
- 여자/두목소리 overlap layer coverage: 58.22%, detected regions: 45.
- 보컬 음량감은 v07과 크게 달라지지 않게 유지하고, 선명도는 presence restore와 dynamic EQ로 보강했다.
- 멜로디는 별도 overlay로 더 앞으로 뺐다.
- 초반 지직/삑과 중간 스읍성 고역 transient는 vocal/source 단계에서 억제했다.
- 새 보컬 길이가 짧아 마지막 아웃트로 일부에는 새 두목소리 레이어가 없다.
- 최종 판단은 감정선 보존 우선이다. 기술적으로 가장 깨끗한 무보컬/저보컬 버전보다 새 보컬 감정이 살아있는 레이어 버전을 메인으로 선택했다.

## Deliverables

- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/0101_FINAL_male_lead_reference_balance.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/0101_FINAL_male_lead_reference_balance_320.mp3`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/0101_FINAL_male_ref_female_overlap.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/0101_FINAL_male_ref_female_overlap_320.mp3`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/0101_FINAL_overlap_layer_louder_check.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/0101_FINAL_overlap_layer_louder_check_320.mp3`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/0101_mix_male_lead_reference_balance_premaster.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/0101_mix_male_ref_female_overlap_premaster.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/0101_mix_overlap_layer_louder_check_premaster.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/bass808_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/drums_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/melody_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/processed_female_vocal_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/processed_instrumental_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/processed_male_vocal_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v08_male_clear_strict_female_timing/processed_new_dual_voice_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/reaper/0101_suno_dual_voice_v08_male_clear_strict_female_timing/0101_REAPER_DUAL_VOICE_MIX_MASTER_PROJECT.rpp`
