# Source Stem Report

| stem | role | duration_s | peak_dbfs | rms_dbfs | stereo_corr | status |
| --- | --- | --- | --- | --- | --- | --- |
| 0101_backing_vocals_raw.wav | old_backing_reference | 139.441 | -13.27 | -35.88 | 0.0578 | reference only / muted |
| 0101_bass808_raw.wav | bass_808 | 139.441 | -8.09 | -23.6 | 0.9474 | usable with cleanup |
| 0101_drums_raw.wav | drums | 139.441 | -3.77 | -21.94 | 0.9779 | usable with cleanup |
| 0101_fx_raw.wav | fx | 139.441 | -2.77 | -36.1 | 0.5552 | support |
| 0101_instrumental_raw.wav | base_instrumental | 139.441 | -2.5 | -18.48 | 0.7447 | usable with cleanup |
| 0101_keyboard_raw.wav | keyboard_melody_support | 139.441 | -6.37 | -25.3 | 0.0787 | support |
| 0101_melody_raw.wav | melody | 139.441 | -6.37 | -24.99 | 0.032 | usable with cleanup |
| 0101_new_suno_dual_voice_raw.wav | new_suno_dual_voice | 117.28 | -2.28 | -20.73 | 0.9309 | support |
| 0101_new_suno_instrumental_reference.wav | new_suno_instrumental_reference_muted | 117.28 | -2.36 | -18.34 | 0.8193 | reference only / muted |
| 0101_original_reference.wav | muted_reference | 139.441 | -2.12 | -16.61 | 0.7903 | reference only / muted |
| 0101_percussion_raw.wav | percussion | 139.441 | -54.45 | -106.58 | -0.2439 | support |
| 0101_synth_raw.wav | synth_melody_support | 139.441 | -9.92 | -36.81 | -0.4499 | support |
| 0101_vocal_raw.wav | original_male_vocal | 139.441 | -5.82 | -24.46 | 1.0 | usable with cleanup |

## Notes

- 새 Suno zip은 `0 Lead Vocals.wav`와 `1 Instrumental.wav` 두 파일만 포함했다.
- 새 Instrumental은 정렬 검사용으로만 사용했고, 기존 반주를 덮는 새 베드는 활성화하지 않았다.
- 새 Lead Vocals는 두목소리 레이어 소스로 채택했다. 단, 길이가 기존 0101보다 짧아서 끝 13.9초는 기존 보컬/반주 중심으로 유지된다.
