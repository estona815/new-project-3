# Female Candidate QC Report

| label | vocal_score | offset_s | coverage_pct | pitch_window_median | score | decision |
| --- | --- | --- | --- | --- | --- | --- |
| candidate_1_0101_Stems | 0.6294 | -0.32 | 46.63 | 0.5 | 0.6803 | use_as_tucked_qc_support |
| candidate_2_0101_Stems-2 | 0.6294 | -0.32 | 46.63 | 0.5 | 0.6803 | use_as_tucked_qc_support |

- Selected candidate: `candidate_1_0101_Stems`.
- 여자 보컬은 전체 리드로 쓰지 않고, timing/pitch QC mask를 통과한 구간만 wide support/adlib texture로 사용했다.
- 가사 자동 인식은 로컬에서 신뢰 가능한 엔진이 없어 직접 보장하지 않았다. 대신 남자 보컬 phrasing, 음정 chroma, active overlap이 맞는 구간만 열었다.
- QC에 실패하는 구간은 음소거되어 전처럼 가사/음정이 다르게 크게 들리는 상황을 피했다.
