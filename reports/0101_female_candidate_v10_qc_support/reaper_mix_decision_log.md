# REAPER Mix Decision Log

- Slug: `0101_female_candidate_v10_qc_support`.
- 새 폴더 `0101 Stems` / `0101 Stems-2`의 여자/새 리드 후보를 분석했다.
- 선택 후보: `candidate_1_0101_Stems`.
- 여자 후보는 남자 보컬과 맞는 구간에만 마스크로 열고, 남자 리드를 덮지 않도록 center/wide 모두 사이드체인 덕킹했다.
- 여자 후보 처리: spectral denoise, dynamic EQ, de-ess, AI fizz tame, short reverb, stereo delay, male-lead sidechain duck.
- 남자 보컬 처리: 강한 tune-feel density layer, spectral denoise, dynamic resonance EQ, sip/breath/beep suppress.
- 반주 처리: melody-forward, round kick support, mono sub reinforcement, vocal-triggered ducking.
- 마스터: -11 LUFS대, true peak -1.25 dBTP target.
- 같이 제공되는 `male_only_safety`는 여자 레이어가 취향에 안 맞을 때 바로 비교용이다.
