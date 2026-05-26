# Final QC Report

| version | duration_s | integrated_lufs | true_peak_dbfs | peak_dbfs | rms_dbfs | stereo_corr |
| --- | --- | --- | --- | --- | --- | --- |
| dual_voice_layer_wav | 139.441 | -11.5 | -1.2 | -1.23 | -14.37 | 0.1404 |
| new_dual_voice_alt_wav | 139.441 | -11.6 | -1.2 | -1.23 | -14.5 | 0.141 |
| male_lead_new_voice_support_wav | 139.441 | -11.6 | -1.2 | -1.23 | -14.5 | 0.1383 |

## QC Notes

- 메인 추천본은 `0101_FINAL_dual_voice_layer.wav`이다.
- 새 두목소리 보컬은 실제 Suno 생성 보컬을 사용했고, 이전 피치변환식 여자 레이어는 제외했다.
- 보컬은 이전보다 덜 크도록 gain을 내리고 라이드했으며, 선명도는 presence layer와 dynamic de-ess로 보강했다.
- 멜로디는 별도 overlay로 더 앞으로 뺐다.
- 초반 지직/삑과 중간 스읍성 고역 transient는 vocal/source 단계에서 억제했다.
- 새 보컬 길이가 짧아 마지막 아웃트로 일부에는 새 두목소리 레이어가 없다.
- 최종 판단은 감정선 보존 우선이다. 기술적으로 가장 깨끗한 무보컬/저보컬 버전보다 새 보컬 감정이 살아있는 레이어 버전을 메인으로 선택했다.

## Deliverables

- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/0101_FINAL_dual_voice_layer.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/0101_FINAL_dual_voice_layer_320.mp3`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/0101_FINAL_male_lead_new_voice_support.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/0101_FINAL_male_lead_new_voice_support_320.mp3`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/0101_FINAL_new_dual_voice_alt.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/0101_FINAL_new_dual_voice_alt_320.mp3`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/0101_mix_dual_voice_layer_premaster.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/0101_mix_male_lead_new_voice_support_premaster.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/0101_mix_new_dual_voice_alt_premaster.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/bass808_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/drums_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/melody_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/processed_female_vocal_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/processed_instrumental_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/processed_male_vocal_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/renders/0101_suno_dual_voice_v06/processed_new_dual_voice_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/reaper/0101_suno_dual_voice_v06/0101_REAPER_DUAL_VOICE_MIX_MASTER_PROJECT.rpp`
