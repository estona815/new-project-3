# REAPER Mix Pipeline

## 오디오 제작 과정과 품질 확인을 위한 작업공간

REAPER 세션, 오디오 처리 도구, 렌더 결과와 검수 보고서를 버전별로 연결하는 개인 음악 제작 작업공간입니다. 저장소 주소는 기존 `new-project-3`를 유지합니다.

[채용 포트폴리오](https://github.com/estona815/engineering-portfolio) · [프로젝트 안내](https://github.com/estona815/engineering-portfolio/blob/main/docs/PROJECT_INDEX.md)

## 먼저 볼 문서

- [REAPER 작업 절차](REAPER_REFERENCE_MIX_PIPELINE.md): 승인된 타이밍에서 시작해 세션·렌더·품질 확인·기록으로 이어지는 흐름.
- [믹스 파이프라인 인계](MGMG_MIX_PIPELINE_HANDOFF.md): 작업을 이어가기 위한 기준과 인계 기록.
- [오디오 검사 의존성](requirements-audio-qc.txt): 오디오 품질 확인용 Python 패키지 목록.

## 폴더 안내

| 경로 | 내용 |
|---|---|
| `tools/` · `scripts/` | 오디오 처리와 검사 보조 도구 |
| `reaper/` | 버전별 REAPER 작업 자료 |
| `renders/` | 렌더 결과 |
| `reports/` | 품질 검사와 판단 기록 |
| `config/` | 작업 설정 |
| `AI_BEAT_LOGIC_WORKFLOW/` | 비트·Logic 관련 제작 자료 |

## 작업 흐름에서 확인할 점

타이밍이 승인된 세션을 기준으로 수정하고, 새 버전의 세션·렌더·검사 기록을 연결합니다. 레퍼런스 분석, 음량·true peak 등의 측정, 사용자 청취 피드백을 구분해 다음 판단에 활용하는 구조입니다.

이 README는 기존 작업공간의 탐색 안내입니다. 실제 실행에는 해당 문서의 DAW·플러그인·오디오 자산 환경이 필요합니다. 음악 제작 결과와 검사 기록은 각 버전의 보고서 범위에서 확인할 수 있습니다.
