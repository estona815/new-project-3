# QC Report

## A. 코드가 측정한 사실
- Status: ok
- WAV `estona_dummy_v29_normal_20260525.wav`: LUFS -16.870693291956734, TP proxy -6.8973110604104875, peak -10.41913624152411, crest 1.921549142213439
  - Risks: {'clipping_risk': False, 'mp3_overshoot_risk': False, 'low_end_mono_safety': True, 'high_glare_risk': False, 'sibilance_risk': False}
- MP3 `estona_dummy_v29_normal_20260525_mp3check.mp3`: LUFS -16.8784822660074, TP proxy -7.022239050573166, peak -10.544064231686791, crest 1.896120952655567
  - Risks: {'clipping_risk': False, 'mp3_overshoot_risk': False, 'low_end_mono_safety': True, 'high_glare_risk': False, 'sibilance_risk': False}

## Method Limits
- true_peak_proxy is a risk proxy, not a formal oversampled BS.1770 true-peak implementation.
- MP3 encode check: {'attempted': True, 'ffmpeg_path': '/Users/hantaeheuk/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1', 'created': ['/Users/hantaeheuk/Documents/New project 3/ESTONA_AUTO_MIX_ENGINE/06_OUTPUTS/mp3_check/estona_dummy_v29_normal_20260525_mp3check.mp3'], 'errors': []}

## B. 정책 엔진이 추천한 수정
- See `03_POLICY_ENGINE/mix_policy.json` and `master_policy.json` after policy generation.

## C. 사용자가 청감으로 확인해야 하는 항목
- 보컬이 너무 앞으로 튀는지
- 보컬이 너무 묻히는지
- 여자 더블이 리드처럼 들리는지
- 808이 폰에서도 들리는지
- 고역이 피곤한지
- AI/Suno 느낌이 줄었는지
- 레퍼런스와 감정적 방향이 맞는지
