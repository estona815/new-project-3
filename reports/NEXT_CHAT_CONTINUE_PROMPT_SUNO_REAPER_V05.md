# New Chat Continue Prompt

Paste this into a new Codex chat to continue from the current project state.

```text
/Users/hantaeheuk/Documents/New project 3 프로젝트를 이어서 작업해줘.

먼저 AGENTS.md 지시를 확인하고, 필요한 경우 hpdc-reaper-automix-bible 스킬을 읽어줘. 현재 브랜치는 `codex/suno-reaper-harness-v05-handoff`이고, 작업은 새로 처음부터 만들지 말고 현재 v23/v0.5 기준에서 이어서 해줘.

중요 규칙:
- MP3 master/fullmix/final은 production source가 아니라 reference_only 또는 problem_reference로만 써.
- production rebuild는 Suno Studio WAV stems와 stem-derived guide MIDI 기준으로만 진행해.
- REAPER가 메인 DAW야.
- premium plugin이 없다고 hard-fail 하지 말고 REAPER stock fallback으로 진행하고 limitation을 문서화해.
- 플러그인이 감지됐다고 실제 적용됐다고 말하지 마. REAPER insertion과 render verification이 끝난 뒤에만 적용을 주장해.
- 기술 레퍼런스는 톤/공간/밸런스/다이내믹 참고용만 사용하고, 멜로디/가사/편곡/코드/탑라인/아티스트 정체성은 복사하지 마.

현재 기준 파일:
- v23 완성본 MP3:
  /Users/hantaeheuk/Documents/New project 3/suno_studio_extract/v11_precision_mix/renders/hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_320k.mp3
- v23 완성본 WAV:
  /Users/hantaeheuk/Documents/New project 3/suno_studio_extract/v11_precision_mix/renders/hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_24-48.wav
- v23 processed stems ZIP:
  /Users/hantaeheuk/Documents/New project 3/suno_studio_extract/v11_precision_mix/renders/hangang_shadow_mashup_v23_vocal_clarity_rebalance_processed_stems.zip
- 현재 분류 보관본:
  /Users/hantaeheuk/Documents/New project 3/suno_studio_extract/_classified_current_v23_for_new_work
- raw Suno stems:
  /Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems
- guide MIDI:
  /Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides
- external female vocal source:
  /Users/hantaeheuk/Documents/New project 3/suno_studio_extract/external_female_v20_stems/0 Lead Vocals.wav

v0.5 harness handoff:
- /Users/hantaeheuk/Documents/New project 3/reports/SUNO_REAPER_HARNESS_V05_HANDOFF.md
- /Users/hantaeheuk/Documents/New project 3/reports/codex_patch_report.md
- /Users/hantaeheuk/Documents/New project 3/reports/plugin_inventory.md
- /Users/hantaeheuk/Documents/New project 3/reports/source_classification.md
- /Users/hantaeheuk/Documents/New project 3/reports/audio_qc.md
- /Users/hantaeheuk/Documents/New project 3/reports/reference_comparison.md
- /Users/hantaeheuk/Documents/New project 3/reaper/build_project.lua
- /Users/hantaeheuk/Documents/New project 3/reaper/apply_mix_chains.lua
- /Users/hantaeheuk/Documents/New project 3/reaper/render_project.lua
- /Users/hantaeheuk/Documents/New project 3/reaper/launch_reaper.sh

현재 v0.5 상태 요약:
- source classification: production rebuild allowed true, production audio files 14, references 5, guide MIDI 13.
- audio QC: 208 issues, 83 REAPER marker candidates.
- QC quarantine sources:
  - /Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/03_FX.wav
  - /Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/08_Guitar.wav
- REAPER에서 위 두 파일은 ARTIFACT_QUARANTINE_BUS로 보내고 mute해야 해.
- 12_Vocals.wav는 main male lead vocal.
- 11_Backing_Vocals.wav와 external_female_v20_stems/0 Lead Vocals.wav는 female BGV/support layer.
- external_female_v20_stems/1 Instrumental.wav는 duplicate 방지를 위해 reference_only.
- Current/problem reference MP3 zip은 프로젝트 안 fallback을 찾아 분석됨.
- Technical reference `/mnt/data/Estona,Nib-Lovee_MASTER_24-48.wav.zip`은 현재 환경에서 missing으로 기록됨. 있으면 다시 compare-reference를 실행해.

Plugin inventory:
- 감지된 후보: Auto-Tune Pro, TDR Nova, Decapitator, Ozone Imager 2, UAD LA-2A/1176 계열.
- fallback: ReaTune, ReaEQ, ReaXcomp, ReaComp, ReaVerbate, ReaDelay, ReaLimit, ReaFIR.
- 실제 적용 claim은 REAPER에서 확인 전까지 하지 마.

다음 작업 목표:
1. `reports/SUNO_REAPER_HARNESS_V05_HANDOFF.md`와 관련 reports를 읽고 현재 상태를 파악해.
2. REAPER script가 실제 세션을 제대로 만들 수 있는지 Lua 구조를 점검해.
3. 가능하면 `./reaper/launch_reaper.sh`로 REAPER 세션을 열 준비를 해. 다만 REAPER 실행/렌더 검증을 했는지 안 했는지 명확히 구분해.
4. main vocal 중심으로 Auto-Tune/ReaTune strategy, TDR Nova dynamic EQ, de-essing, serial compression, send-based plate/delay, M/S EQ, master bus를 실제 REAPER workflow에 맞게 더 정교화해.
5. REAPER render가 가능하면 premaster와 master를 생성하고, 아니면 정확한 manual steps와 limitation을 reports에 남겨.
6. 새로 만든 산출물은 source script/report와 동기화하고, 중간 파일은 정리해.

검증 참고:
- Targeted v0.5 tests:
  `PYTHONPATH=AI_BEAT_LOGIC_WORKFLOW/src python3 -m unittest AI_BEAT_LOGIC_WORKFLOW.tests.test_suno_reaper_harness -v`
  결과: 13/13 통과.
- Full unittest discover는 495개 중 493개 통과. 남은 2개는 기존 fixture/worktree 상태 문제:
  missing `AI_BEAT_LOGIC_WORKFLOW/05_FINAL_WAV/plugg_reference_matched_v4_24bit_48k.wav`,
  existing untracked `AI_BEAT_LOGIC_WORKFLOW/08_REFERENCE_MATCH/web_reference_sources.json`.
- pytest는 설치되어 있지 않음.

최종 답변은 한국어로 간결하게, 무엇을 바꿨고 어떤 검증을 했는지 중심으로 정리해줘.
```

