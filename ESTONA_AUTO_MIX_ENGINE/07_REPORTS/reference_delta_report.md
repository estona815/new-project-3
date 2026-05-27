# Reference Delta Report

## A. 코드가 측정한 사실
- Status: ok
- Reference status: ok
- 808_sub_dummy.wav (bass_808)
  - integrated_lufs: current -15.831, ref median -16.923, delta 1.092
  - peak_dbfs: current -12.042, ref median -11.857, delta -0.186
  - rms_db: current -15.140, ref median -16.232, delta 1.092
  - crest_factor: current 1.414, ref median 1.638, delta -0.224
  - low_band_energy_20_120hz: current -0.000, ref median -47.143, delta 47.143
  - low_mid_energy_120_350hz: current -90.314, ref median -0.018, delta -90.296
  - vocal_presence_energy_1k_4k: current -95.791, ref median -32.502, delta -63.289
  - harshness_energy_3k_6k: current -97.569, ref median -32.645, delta -64.924
- beat_dummy.wav (beat)
  - integrated_lufs: current -17.583, ref median -16.923, delta -0.660
  - peak_dbfs: current -9.636, ref median -11.857, delta 2.221
  - rms_db: current -16.892, ref median -16.232, delta -0.660
  - crest_factor: current 2.283, ref median 1.638, delta 0.644
  - low_band_energy_20_120hz: current -0.192, ref median -47.143, delta 46.951
  - low_mid_energy_120_350hz: current -33.836, ref median -0.018, delta -33.818
  - vocal_presence_energy_1k_4k: current -22.304, ref median -32.502, delta 10.199
  - harshness_energy_3k_6k: current -22.446, ref median -32.645, delta 10.199
- female_adlib_dummy.wav (backing_vocal)
  - integrated_lufs: current -25.587, ref median -16.923, delta -8.664
  - peak_dbfs: current -18.571, ref median -11.857, delta -6.714
  - rms_db: current -24.896, ref median -16.232, delta -8.664
  - crest_factor: current 2.051, ref median 1.638, delta 0.412
  - low_band_energy_20_120hz: current -38.475, ref median -47.143, delta 8.668
  - low_mid_energy_120_350hz: current -35.368, ref median -0.018, delta -35.350
  - vocal_presence_energy_1k_4k: current -23.835, ref median -32.502, delta 8.668
  - harshness_energy_3k_6k: current -23.977, ref median -32.645, delta 8.668
- lead_vocal_dummy.wav (lead_vocal)
  - integrated_lufs: current -18.660, ref median -16.923, delta -1.736
  - peak_dbfs: current -12.782, ref median -11.857, delta -0.926
  - rms_db: current -17.969, ref median -16.232, delta -1.736
  - crest_factor: current 1.799, ref median 1.638, delta 0.160
  - low_band_energy_20_120hz: current -45.410, ref median -47.143, delta 1.733
  - low_mid_energy_120_350hz: current -0.027, ref median -0.018, delta -0.009
  - vocal_presence_energy_1k_4k: current -30.770, ref median -32.502, delta 1.732
  - harshness_energy_3k_6k: current -30.913, ref median -32.645, delta 1.732

## B. 정책 엔진이 추천한 수정
- Generate policies with `generate_mix_policy.py` and `generate_master_policy.py`.

## C. 사용자가 청감으로 확인해야 하는 항목
- 레퍼런스와 감정적 방향이 맞는지
- 분석 수치가 맞아도 보컬/비트 밸런스가 음악적으로 자연스러운지
