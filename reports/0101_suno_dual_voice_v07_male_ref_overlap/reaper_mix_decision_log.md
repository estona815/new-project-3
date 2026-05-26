# REAPER Mix Decision Log

## Version

- Slug: `0101_suno_dual_voice_v07_male_ref_overlap`.
- Source: 기존 0101 Studio stems + 새 Suno two-voice 2-stem zip.
- Routing: reference/full-mix/new instrumental tracks are muted; active final print is the dual-voice layer mix.

## Decisions

- 새 보컬은 +8.269s 오프셋으로 정렬했다.
- 이전 로컬 피치업 여자보컬 레이어는 사용하지 않았다.
- 새 Instrumental은 길이 차이 때문에 반주 베드로 쓰지 않고 정렬 reference로만 사용했다.
- 보컬은 지직/삑 시작음, 스읍성 고역 흡입음, 5.5-12kHz AI fizz를 먼저 줄인 뒤 선명도만 소량 보강했다.
- v07에서는 남자 보컬을 lead/reference 음량으로 다시 올리고, 여자/두목소리 보컬은 남자 보컬과 실제로 겹치는 phrase에서만 열리게 만들었다.
- 여자/두목소리 overlap layer coverage: 44.03%, detected regions: 224.
- 여자/두목소리 레이어는 center lead가 아니라 wide support/double 역할로 낮춰서 남자 보컬과 조화롭게 섞이게 했다.
- 멜로디는 keyboard/synth/melody stem을 따로 정리해 약간 더 앞으로 올렸다.
- 킥/808은 새 베드 추가 없이 기존 drums/bass stem에 round kick support와 mono sub reinforcement만 얹었다.
- Antares 제품, 랜덤 애드립, vocal chop hook, 새 EDM/K-pop식 베드는 사용하지 않았다.

Detailed DSP log: `/Users/hantaeheuk/Documents/New project 3/reports/0101_suno_dual_voice_v07_male_ref_overlap/processing_decisions.json`
