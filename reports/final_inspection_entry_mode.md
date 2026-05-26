# Final Inspection Entry Mode

목적: 레퍼런스 마스터에서 추출한 기술적 흔적을 기준으로, REAPER 자동화/렌더 전 최후검수 항목을 기입한다.

## 0. Safety
- [ ] 레퍼런스의 멜로디/훅/리듬/편곡/보컬 정체성을 복제하지 않는다.
- [ ] provenance, watermark, metadata를 기만적으로 제거하지 않는다.
- [ ] Antares 사용 없음.
- [ ] 유료 플러그인은 사용자가 명시 허용한 것만 사용.

## 1. Source/Codec/Container
- Target noise floor proxy: -29.006 dBFS (IQR -29.911 to -27.438 dBFS)
- Target high hash score: 0.858 (IQR 0.823 to 0.889)
- [ ] 현재 믹스가 reference보다 HF cutoff/hash가 과한지 확인
- [ ] clipping/true-peak proxy가 안전한지 확인
- Notes:

## 2. EQ Static 후보
- [ ] 20-120 Hz: mono sub/808 weight 확인
- [ ] 120-350 Hz: mud/boxiness 확인
- [ ] 350-1000 Hz: body/readability 확인
- [ ] 2-5 kHz: vocal/presence 과밀 확인
- [ ] 5-8 kHz: harshness 확인
- [ ] 8-20 kHz: air/hash/fizz 확인
- Notes:

## 3. Dynamic EQ 후보
- [ ] ReaXcomp/TDR Nova 후보 band를 dense control map에서 확인
- [ ] p90/burstiness가 높은 대역만 dynamic cut
- [ ] 보컬 stem 없을 때는 full-mix de-harsh만 보수적으로
- Notes:

## 4. Reverb/Delay Trace
- Reference early reflection ratio: 0.883 (IQR 0.796 to 0.903)
- Reference tail ratio: 0.774 (IQR 0.763 to 0.816)
- Reference tail width lift: 8.808 dB (IQR 7.086 to 10.762 dB)
- [ ] 현재 보컬이 dry/detached이면 short room or plate send 추가
- [ ] delay repeat 후보가 곡 groove와 충돌하지 않는지 확인
- [ ] high damping이 부족하면 reverb return LPF/De-ess
- Notes:

## 5. Saturation/Clip/Limiter
- Limiter trace target: 0.088 (IQR 0.033 to 0.137)
- Clipper trace target: 0.849 (IQR 0.797 to 0.988)
- Saturation/exciter trace target: 0.723 (IQR 0.671 to 0.733)
- [ ] loudness를 올리기 전에 5-8 kHz harshness를 먼저 제어
- [ ] clipper는 drum/beat/mix bus에 소량, master는 ceiling 안전
- Notes:

## 6. M/S EQ and Width
- Stereo widener trace target: 0.141 (IQR 0.106 to 0.429)
- [ ] 20-120 Hz side가 reference보다 크면 MonoSub/side cut
- [ ] 8-20 kHz side가 과하면 high-side hash cut
- Notes:

## 7. Final Decision
- [ ] PASS: current mix matches broad technical target and listening check passes.
- [ ] REVISE: specific issue remains.
- [ ] HOLD: missing current/stem material prevents honest decision.
- Decision notes:
