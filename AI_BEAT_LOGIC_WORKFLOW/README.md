# AI_BEAT_LOGIC_WORKFLOW

Local AI producer workflow for analyzing songs, samples, vocals, and stems, then generating arrangement plans, MIDI/region guides, Logic Pro instructions, mix/master plans, fallback exports, verified WAVs, and QC reports.

## Project Goal

Turn a user-provided song, sample, vocal, stereo sketch, Suno-style render, or stem folder into a controllable production plan. The workflow focuses on Korean natural-language production requests, sample/vocal analysis, arrangement control, Logic Pro manual guidance, mix/master discipline, verified exports, and honest safety/QC status.

## What It Can Do

- Create the required project folder structure.
- Collect production choices through CLI flags or interactive prompts.
- Copy and sanitize input audio without overwriting originals.
- Convert supported audio to `04_PROCESSED_AUDIO/working_input.wav`.
- Analyze metadata, levels, clipping, silence, low-end risk, vocal-like texture candidates, melody-buried candidates, and section candidates.
- Generate a producer-readable edit plan for Logic Pro/manual editing.
- Attempt optional Logic Pro automation and write a status report without fake success claims.
- Run conservative stereo-only fallback processing: trim, fade, gain-stage, basic EQ/compression when tools support it, and verification.
- Plan mode-aware vocal song mix/master work for instrumental beats, separate vocal plus beat files, full stereo songs, or user-provided stems.
- Run sample/vocal/song/stems-to-arrangement autopilot and write plan-only guide files without claiming rendered audio.
- Rescue bad AI/Suno-style songs by diagnosing missing lead/hook/structure, rebuilding arrangement intent, generating a proposed lead/hook motif, demoting weird vocal-like textures, and optionally rendering a demo/final rescue WAV.
- Export a final WAV, write QC reports, and generate a release-ready package only after the file exists and verification passes.

## What It Cannot Do

- It cannot truly remix stems from a single stereo file unless stem separation is added.
- It cannot guarantee real vocal removal; vocal-like detection is heuristic unless a real model is added.
- It cannot claim professional stem-level vocal mixing from a full stereo song. Separate vocal processing requires separate vocal or stem files.
- It cannot exactly copy a reference song, artist, or producer.
- It cannot fully automate Logic Pro mixing, plugin insertion, region edits, or automation curves.
- It cannot replace human listening and arrangement judgment.
- It cannot make a weak AI song feel finished by mastering alone when no lead, hook, or structure exists.
- It must not claim production completion unless final WAV verification and QC report creation pass.
- "Release-ready" does not mean distribution approval, rights clearance, chart success, or commercial success.

## Requirements

- macOS is recommended.
- Python 3.9+.
- `afconvert`/`afinfo` on macOS, or `ffmpeg`/`ffprobe`.
- Logic Pro is optional.
- C compiler for helper tools: `cc` or compatible.

Install ffmpeg if you want broader input support, MP3 preview export, and richer filter processing:

```bash
brew install ffmpeg
```

If `ffmpeg` is missing, the workflow tries macOS `afconvert`. If both are missing, conversion/export fails cleanly and writes an error/status file where relevant.

## macOS / Logic Pro Note

Logic Pro automation is optional and limited. The workflow checks `/Applications/Logic Pro.app` and `osascript`, then writes `03_LOGIC_PROJECT/logic_automation_status.md`. It never reports Logic success unless the expected `.logicx` project/package exists. See `docs/LOGIC_AUTOMATION_LIMITS.md`.

## Example Commands

From the project root:

```bash
cd AI_BEAT_LOGIC_WORKFLOW
```

Rough full release package:

```bash
python3 src/main.py \
  --input "/path/song.wav" \
  --workflow song_to_release \
  --rough-request "마음대로 상업 음악 퀄. 디지코어/하이퍼팝 결, 808 강하게, 보컬 앞으로, 릴스 훅, 믹마까지." \
  --release-ready true \
  --target-deliverable release_package \
  --export-format wav24_48k
```

Sample to release draft:

```bash
python3 src/main.py \
  --input "/path/sample.wav" \
  --workflow sample_to_release \
  --rough-request "이 샘플로 SYSTEM SEOUL/ycs 결 비트 짜고 믹마 플랜까지." \
  --owned-samples true \
  --release-ready true
```

Vocal to release:

```bash
python3 src/main.py \
  --vocal-file "/path/vocal.wav" \
  --beat-file "/path/beat.wav" \
  --workflow vocal_to_release \
  --rough-request "오토튠 더, 디카페이터 살짝, 내 목소리 유지, 발매용 믹스." \
  --owned-vocals true
```

Stems to release:

```bash
python3 src/main.py \
  --stems-folder "/path/stems" \
  --workflow stems_to_release \
  --rough-request "상업 음악 퀄로 ycs/SYSTEM SEOUL 결. 보컬 앞으로, 808 강하게, 클리핑 없이." \
  --owned-stems true \
  --release-ready true
```

Bad AI song rescue:

```bash
python3 src/main.py \
  --input "/path/bad_ai_song.wav" \
  --workflow bad_ai_song_rescue \
  --rough-request "이거 노래 느낌이 없고 리드멜로디도 없고 편곡도 이상해. SYSTEM SEOUL/ycs 결로 훅 만들고 2분 이내로 사람이 만든 곡처럼 구조 다시 잡아줘." \
  --sample-folder "/path/samples" \
  --rescue-mode final \
  --generate-lead true \
  --target-length under_2min \
  --style-cluster system_seoul_adjacent \
  --export-format wav24_48k
```

Optional release metadata can be supplied up front:

```bash
python3 src/main.py \
  --input "/path/song.wav" \
  --workflow song_to_release \
  --release-ready true \
  --target-deliverable release_package \
  --metadata-title "Track Title" \
  --metadata-artist "Artist Name" \
  --metadata-version "single" \
  --metadata-genre "hyperpop" \
  --metadata-language "ko" \
  --metadata-explicit false \
  --metadata-copyright-year "2026" \
  --metadata-copyright-owner "Artist Name" \
  --metadata-producer "Producer Name" \
  --metadata-composer "Composer Name"
```

Leave `--metadata-isrc` and `--metadata-upc` blank unless you already have real codes; the workflow never invents them.

Legacy explicit options still work:

```bash
python3 src/main.py \
  --input "/path/to/suno_song.mp3" \
  --mode "full_song_stereo" \
  --reference-text "bright emotional hyperpop, clean but hard 808" \
  --length-mode "under_2min" \
  --vocal-mode "suppress" \
  --melody-focus "front" \
  --drum-808 "strong_controlled" \
  --export-format "wav24_48k" \
  --save-logic-project true
```

Natural Korean production request example:

```bash
python3 src/main.py \
  --input "/path/song.wav" \
  --creative-target-text "웨스트우드 Just Touched Down 베이스랑 킥 느낌. 따오는 건 아니고 질감만." \
  --vocal-fx-text "보컬 오토튠 더 걸고 디카페이터 살짝" \
  --style-cluster-text "2hollis, ycs, SYSTEM SEOUL 쪽인데 cheap rage clipping은 피하기" \
  --owned-reference-sample false \
  --owned-reference-stems false \
  --export-format wav24_48k
```

These text fields are preserved in `02_EDIT_PLAN/creative_brief.json` and passed to the reference parser as one combined production request. Exact sample/stem/vocal use is blocked unless the user provides a local owned/licensed source and marks the relevant ownership flag true.

Release CLI options:

- `--workflow`: `bad_ai_song_rescue`, `song_to_release`, `sample_to_release`, `vocal_to_release`, `stems_to_release`, `song_to_mix_master`, `sample_to_arrangement`, `vocal_to_code`, or `plan_only`.
- `--release-ready true|false`: request release-package readiness checks.
- `--target-deliverable demo|final_master|release_package`: choose the intended output depth.
- `--release-profile commercial_digicore|hip_hop|hyperpop|internet_underground|system_seoul_adjacent|custom`: apply safe production defaults.
- `--owned-samples true|false`, `--owned-stems true|false`, `--owned-vocals true|false`: user-confirmed rights inputs for release QC.
- `--metadata-title`, `--metadata-artist`, `--metadata-version`, `--metadata-genre`, `--metadata-language`, `--metadata-explicit true|false`, `--metadata-isrc`, `--metadata-upc`, `--metadata-copyright-year`, `--metadata-copyright-owner`, `--metadata-producer`, `--metadata-composer`, `--metadata-lyricist`: draft or complete release metadata fields.

Bad AI song rescue options:

- `--rescue-mode plan|demo|final`: `plan` writes diagnosis/plans only, `demo` renders `04_PROCESSED_AUDIO/rescue_demo.wav`, and `final` additionally renders/verifies `05_FINAL_WAV/final_bad_ai_song_rescue_24bit_48k.wav`.
- `--generate-lead true|false`: generate and optionally render a proposed lead/hook motif when the source has no clear lead.
- `--sample-folder "/path/to/samples"`: optional local owned/cleared samples for musical motif rebuilding. Unknown ownership remains a release blocker.
- `--demote-vocal-texture true|false`: reduce weird vocal-like textures so they stop dominating the lead role. Stereo-only demotion is not vocal removal.
- `--target-length reels_15sec|short_30sec|under_2min|full_song`: target rescue form.
- `--style-cluster commercial_digicore_hyperpop|system_seoul_adjacent|custom`: broad production direction only; exact artist/song copying is prohibited.

Interactive mode:

```bash
python3 src/main.py --interactive
```

Interactive mode asks for one full Korean request, optional reference audio, owned/licensed sample or stem confirmation, priority, avoid list, vocal FX direction, export format, and Logic project preference. Use the same rough request text you would pass to `--rough-request`. The generated `creative_brief.md` includes the raw request, parsed interpretation, copy/sampling policy, reference confidence, automatic scope, manual/Logic/stem requirements, and final target summary.

Logic-only status attempt:

```bash
python3 src/main.py --logic-only
```

Generate and run the dummy integration fixture:

```bash
python3 tests/generate_dummy_audio.py
python3 src/main.py --input tests/fixtures/dummy_suno_like.wav
```

## Output Folders

- `00_INPUT_SUNO/`: sanitized copy of the original source audio.
- `01_ANALYSIS/`: input metadata, analysis JSON, and producer-readable analysis summary.
- `02_EDIT_PLAN/`: manual Logic/edit plan.
- `03_LOGIC_PROJECT/`: Logic automation status and optional `.logicx` project.
- `04_PROCESSED_AUDIO/`: working WAV, fallback processed WAV, and processing log.
- `05_FINAL_WAV/`: final WAV and optional MP3 preview.
- `06_QC_REPORT/`: final verification JSON and QC report.
- `07_VOCAL_PROCESSING/`: mode-aware vocal analysis, chain plan, processing log, and reserved processed vocal outputs.
- `08_REFERENCE_MATCH/`: broad reference analysis and target profile. This does not clone a reference.
- `09_MIX_MASTER/`: mix/master session plan and master QC notes.
- `10_RELEASE_PACKAGE/`: release manifest, metadata, rights checklist, distribution checklist, release QC report, cover-art requirements when missing, and copied deliverables.

Common autopilot outputs:

- `01_ANALYSIS/dependency_capabilities.json`: detected tools, optional libraries, render/export ability, Logic/automation availability, and limitations.
- `01_ANALYSIS/sample_analysis.json`: sample metadata, level, rough timing/key, loop, motif, onset, transient, and ownership safety analysis.
- `01_ANALYSIS/vocal_to_code.json`: phrase regions, estimated notes, rhythm grid, pitch contour, mix risks, and false-claim guard.
- `01_ANALYSIS/song_structure_analysis.json`: heuristic song sections, hook candidates, transition risks, AI-loop/artifact candidates, and limitations.
- `02_EDIT_PLAN/production_intent.json`: normalized rough-request intent, composition ideas, safety flags, copying policy, and release-ready scope.
- `01_ANALYSIS/bad_song_diagnosis.json`, `01_ANALYSIS/bad_song_diagnosis.md`: bad AI song diagnosis, including when mix/master alone is insufficient.
- `02_EDIT_PLAN/rescue_arrangement_plan.json`, `rescue_arrangement_plan.md`, `lead_melody_plan.json`, `hook_identity_plan.json`, `vocal_texture_rescue_plan.json`, `sample_motif_rebuild_plan.json`, `logic_rescue_plan.md`: rescue plans for structure, lead/hook identity, vocal texture control, sample motif rebuilding, and manual Logic Pro execution.
- `04_PROCESSED_AUDIO/rescue_demo.wav`: optional rescue demo render. This is not a final master and never allows `COMPLETE` by itself.
- `05_FINAL_WAV/final_bad_ai_song_rescue_24bit_48k.wav`: final rescue WAV only when `--rescue-mode final` is requested and render/export verification passes.
- `06_QC_REPORT/rescue_qc_report.md`, `06_QC_REPORT/rescue_qc_score.json`: rescue scoring, verdict, technical checks, manual Logic requirements, and false-claim guard.
- `02_EDIT_PLAN/arrangement_plan.json`: plan-only arrangement autopilot result.
- `02_EDIT_PLAN/midi_region_guide.json`: MIDI/region guide. This is not a claim that MIDI was imported into Logic.
- `02_EDIT_PLAN/logic_arrangement_plan.md`: manual Logic Pro session plan.
- `06_QC_REPORT/arrangement_qc_report.md`: plan-readiness QC when generated.
- `10_RELEASE_PACKAGE/release_manifest.json`: release package manifest after verified final export/QC. It can be draft or ready.
- `10_RELEASE_PACKAGE/release_metadata.json`, `release_metadata.md`, `rights_clearance_checklist.md`, `distribution_checklist.md`, `release_qc_report.md`: metadata, rights, distribution, safety, scoring, and remaining limitations.
- `10_RELEASE_PACKAGE/deliverables/final_master.wav`: copied only from an existing final master WAV. Optional preview, reels/short, instrumental, acapella, stems, and premaster files are included only when real source artifacts exist.
- `05_FINAL_WAV/final_*.wav`: written only if render/export runs and final verification passes.

## QC Report

`06_QC_REPORT/qc_report.md` records exactly what happened. If fallback processing was used, it says so. It includes input file details, final export metadata, melody preservation notes, vocal-like texture notes, drum/808 balance warnings, clipping/loudness checks, AI-feel reduction notes, remaining problems, and next improvement options.

`06_QC_REPORT/rescue_qc_report.md` records the bad AI song rescue verdict. It answers whether the result gained a clear lead, whether the hook appears early, whether sections became intentional, whether weird vocal texture stopped dominating, whether sample motifs act like a hook rather than random chops, whether mix/master technical checks passed, and what remains manual. `FINAL_RESCUE_PASS` requires a verified final WAV, a QC report, and a passing completion gate.

## Bad AI Song Rescue

Bad AI song rescue is not just mastering. If the stereo source has no lead melody, no hook identity, weak structure, strange vocal-like textures, or random AI transitions, the workflow first recommends or creates a recomposition/arrangement rescue plan. EQ and loudness alone are not treated as a fix for missing musical identity.

When no usable lead/hook exists, the system creates `lead_melody_plan.json` and `hook_identity_plan.json` with a proposed generated motif. If enabled, it can render a simple synth lead stem/demo, but that lead is a production proposal, not a guaranteed final composition and not an artist melody imitation.

If samples are available, `sample_motif_rebuild_plan.json` assigns musical roles such as main motif, response motif, texture layer, and transition element. The goal is fewer stronger motifs, not random chop spam.

Stereo-only sources have hard limits: the workflow can demote center-heavy vocal-like texture, duck source texture under a new lead, and reshape the stereo bus, but it cannot honestly claim vocal removal, stem-level remixing, kick replacement, 808 rewrite, drum rewrite, plugin insertion, or Logic automation success from one stereo file.

`10_RELEASE_PACKAGE/release_manifest.json` records whether the local release package is draft or ready. In this project, release-ready means verified audio deliverables, metadata/checklist files, safety notes, QC reports, and clear remaining limitations. It does not mean distribution submission occurred and does not guarantee distribution approval, rights clearance by a third party, placement, sales, charting, or commercial success.

Metadata and rights must be user-confirmed. Missing metadata can still produce a draft package with `release_ready=false`. If direct sample use occurred and sample ownership/clearance is unknown, release readiness is blocked. Voice clone, exact-copy, web-audio download, plugin false-claim, or stem false-claim issues also block release readiness.

## Tests

Run Python tests:

```bash
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
```

Run C helper smoke tests:

```bash
make -C AI_BEAT_LOGIC_WORKFLOW/tools test
```

## Completion Rule

The CLI prints `COMPLETE` only through `src/completion_gate.py`, after the final WAV exists, is non-empty, is readable as the requested 24-bit PCM format/sample rate, peak/RMS/clipping verification has completed, `qc_report.md` exists, any required master QC report exists, and release-ready package reports exist for a release-package path.

Plan-ready statuses such as `ARRANGEMENT_PLAN_READY`, `VOCAL_CODE_READY`, `MIDI_GUIDE_READY`, `RESCUE_PLAN_READY`, and `PLAN_PASS` are useful production milestones, but they are not `COMPLETE`. A fallback export, rescue demo, or guide-only Logic plan also is not complete until a final WAV is exported, verified, and accepted by the completion gate.

Plan-only workflows never print `COMPLETE`.

For `--workflow bad_ai_song_rescue`, `--rescue-mode plan` and `--rescue-mode demo` never print `COMPLETE`. `--rescue-mode final` can print `COMPLETE` only after `final_bad_ai_song_rescue_24bit_48k.wav` is verified as the requested 24-bit/48 kHz WAV and `rescue_qc_report.md`/completion gate pass.

## Vocal / Song Modes

- `instrumental_beat`: default beat-only workflow.
- `vocal_plus_beat`: use when separate vocal and beat files are provided. The pipeline can plan more precise vocal processing, while rendered vocal processing remains limited to available tools.
- `full_song_stereo`: use when vocal is already embedded in one stereo file. Standard mix/master workflow only performs broad mastering-style processing and heuristic vocal-region analysis. Bad AI song rescue can additionally render a conservative stereo-bus rescue demo/final with a generated lead proposal and arrangement restructure, but stereo-only processing still cannot honestly claim stem-level remixing, guaranteed vocal removal, true kick/bass replacement, true drum rewrite, true stem separation, or plugin insertion.
- `stems`: use when the user provides separate stems. Stems improve control because drums, 808/bass, melody/synth, vocals, adlibs, and backing vocals can be planned and balanced separately. Stem-level claims are limited to stems actually provided or verified generated stems.

Autotune defaults to `subtle`, but the plan records it as unavailable unless a local pitch tool is detected and the process is verified. Reference audio/text is translated into broad mix and arrangement traits only; exact song, kick, bassline, melody, lyrics, drum pattern, sound recording, artist voice, or producer cloning is not claimed.

## Autopilot Limits

- Stereo-only files allow broad EQ/gain/fade/width/saturation/mastering polish and heuristic arrangement analysis, not true stem-level remixing.
- Stems improve control because drums, 808/bass, melody/synth, vocals, adlibs, and backing vocals can be planned separately.
- True kick/bass replacement, true drum rewrite, reliable vocal removal, plugin insertion, Logic region import, and Logic bounce/export require real stems, supported tools, manual Logic work, or verified artifacts.
- Commercial QC means technical readiness, arrangement control, mix clarity, and completion integrity. It does not guarantee commercial success or chart success.
