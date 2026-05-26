# Implementation Roadmap

Base branch: `feature/20-commercial-digicore-autopilot` or the current working branch at the time the branch is started.

Branch rule: create each feature branch from the previously passing branch, implement only that branch scope, add focused tests, avoid generated artifact commits, run unit tests, and merge only after passing.

Do not implement later-branch behavior early unless the roadmap is explicitly revised.

## Branch Sequence

### 1. `feature/21-audio-capability-registry`

Scope:
- Add a central capability registry for local dependencies and runtime availability.
- Track Python-only support, ffmpeg/ffprobe, afconvert, pitch tools, Logic Pro availability, plugin detection status, and render/export support.
- Expose capability levels to planning, processing, QC, and docs.

Tests:
- registry reports unavailable tools without crashing
- registry distinguishes plan-only, analysis, render, and Logic capabilities
- plugin/Logic statuses use honest `available`, `unavailable`, `manual_required`, or `unknown` states

Out of scope:
- no new MIR algorithms
- no render/export changes
- no Logic automation behavior changes

Merge gate:
- focused unit tests pass
- no generated artifacts staged

### 2. `feature/22-sample-mir-analysis`

Scope:
- Improve sample/loop MIR analysis.
- Estimate BPM, key/pitch center, loop candidates, motif candidates, transient/onset density, brightness, low-end weight, and arrangement role.
- Keep all results heuristic and guide-only.

Tests:
- synthetic loops produce stable tempo/onset/motif schema
- weak or silent files fail closed with limitations
- ownership/copying language remains present for sample use

Out of scope:
- no MIDI export yet
- no final rendering
- no exact sample copying

Merge gate:
- sample MIR tests pass
- existing reference copying tests pass

### 3. `feature/23-vocal-to-code`

Scope:
- Improve vocal phrase and pitch-contour coding.
- Produce phrase regions, rough note candidates, contour, rhythm grid cues, tuning guide, and vocal chain inputs.
- Keep all transcription language honest.

Tests:
- synthetic vocal phrases produce phrase events
- pitch guide says guide-only and not verified score transcription
- AutoTune/Flex Pitch is not claimed unless a verified processing stage exists

Out of scope:
- no actual AutoTune application
- no artist voice cloning
- no lyric scraping or transcription

Merge gate:
- vocal-to-code tests pass
- artist vocal safety tests pass

### 4. `feature/24-song-structure-analysis`

Scope:
- Improve full-song and stereo-song structure analysis.
- Detect intro, hook/motif candidates, drops, repeated blocks, transition/glitch candidates, silence, energy curve, low-end risk, and melody-buried regions.
- Preserve stereo-only limitations.

Tests:
- synthetic song structures produce expected section candidates
- full-song stereo analysis labels are heuristic
- no isolated vocal/stem control is claimed from one stereo file

Out of scope:
- no arrangement autopilot generation beyond section analysis
- no final WAV changes

Merge gate:
- structure tests pass
- stereo limitation tests pass

### 5. `feature/25-arrangement-autopilot`

Scope:
- Build the sample/vocal/song/stems-to-arrangement autopilot planner.
- Combine sample MIR, vocal code, song structure, stems metadata, Korean request intent, and copying policy.
- Produce arrangement structure, progression guide, drum programming guide, 808/chord/synth guide, and manual Logic arrangement plan.

Tests:
- sample-only, vocal-only, sample+vocal, full-song, and stems modes produce correct workflow schemas
- copying-risk requests are blocked without owned/cleared local sources
- commercial quality language avoids success promises

Out of scope:
- no actual MIDI file writing
- no render/export changes
- no fake Logic project success

Merge gate:
- arrangement autopilot tests pass
- reference safety tests pass

### 6. `feature/26-midi-region-logic-guides`

Scope:
- Convert autopilot plan data into guide-only MIDI/region/Logic instructions.
- Create schemas for region guides, MIDI note candidates, 808 guide notes, chord/progression suggestions, section markers, and Logic checklist steps.
- If MIDI files are generated, they must be intentional fixtures or ignored generated artifacts.

Tests:
- guide schema is stable
- guide output clearly says guide-only
- no MIDI/region guide claims verified performance or exact transcription
- generated guide artifacts are not accidentally committed unless fixtures

Out of scope:
- no final audio rendering
- no Logic UI automation success claims

Merge gate:
- guide tests pass
- generated artifact cleanup confirmed

### 7. `feature/27-mix-master-autopilot`

Scope:
- Build source-aware mix/master planning.
- Use capabilities, stems/stereo mode, vocal analysis, reference traits, and arrangement plan to generate vocal chain, beat balance, low-end, stereo width, saturation, loudness, and master plans.
- Keep fallback processing stereo-only unless stems are provided.

Tests:
- full-song stereo plan stays broad and heuristic
- stems plan is more direct but still verification-gated
- Decapitator/AutoTune/plugin requests remain claim-safe
- loud demo vs master-ready headroom changes QC language

Out of scope:
- no final export gate changes
- no unverified plugin insertion

Merge gate:
- mix/master tests pass
- plugin request tests pass

### 8. `feature/28-render-export-verification`

Scope:
- Harden render/export path.
- Verify 24-bit PCM, sample rate, duration, peak, RMS, clipping count, file size, source type, and preview export status.
- Keep fallback outputs honest and stereo-only.

Tests:
- wrong sample rate blocks
- wrong bit depth blocks
- clipping blocks
- missing final source blocks
- fallback log does not claim stem-level remixing

Out of scope:
- no new arrangement features
- no commercial QC scoring changes beyond verification inputs

Merge gate:
- export verification tests pass
- no generated WAVs committed

### 9. `feature/29-commercial-qc-completion`

Scope:
- Expand commercial QC and completion reporting.
- Score arrangement control, mix clarity, low-end control, vocal intelligibility where applicable, stereo-only limitations, stem readiness, safety compliance, artifact integrity, and final WAV verification.
- Enforce `COMPLETE` only through completion gate from `main.py`.

Tests:
- missing QC report blocks
- missing master QC report blocks when required
- incomplete verification blocks
- `COMPLETE` literal appears only in allowed main gate path
- commercial QC never promises chart or commercial success

Out of scope:
- no new MIR features
- no MIDI guide changes

Merge gate:
- completion gate tests pass
- QC report tests pass
- no generated reports staged unless intentional fixtures

### 10. `feature/30-integration-tests-release`

Scope:
- Add full integration tests and release cleanup.
- Exercise representative workflows:
  - stereo song polish
  - sample-to-arrangement
  - vocal-to-code
  - stems-to-production
  - reference/copying-risk request
  - verified final WAV path
- Update release checklist and architecture docs.

Tests:
- focused unit suite passes
- integration suite passes
- dummy pipeline passes where supported by local tools
- generated artifact cleanup checks pass

Out of scope:
- no new major feature behavior unless fixing integration bugs

Merge gate:
- `python3 -m unittest discover -s tests -v` or project-equivalent command passes
- C/helper tests pass if present
- dummy pipeline passes or unsupported dependency is documented
- generated WAV/log/report/MIDI artifacts cleaned
- final `git status --short` reviewed

## Cross-Branch Rules

For every branch:
- implement only that branch scope
- add narrow tests first or alongside implementation
- preserve existing file structure where practical
- avoid new dependencies unless justified in the branch docs or PR notes
- never run destructive git commands
- never touch unrelated untracked workspace files
- never commit generated WAV/log/report/MIDI artifacts unless they are intentional fixtures
- keep source scripts and generated docs/reports in sync when a script produces them

## Safety Rules Across The Roadmap

- References are high-level production targets only.
- Do not copy exact songs, samples, kick samples, basslines, melodies, lyrics, drum patterns, sound recordings, or living artist vocal identity.
- `따와라`, `가져와라`, `똑같이`, and `그대로` mean copying risk.
- Exact sample/stem use requires local owned/licensed/cleared source confirmation.
- Web research may collect high-level public descriptors only.
- Do not download copyrighted web audio.
- Do not scrape lyrics.
- Do not infer exact sonic details from a title-only reference.

## Plan-Only vs Complete Status

Plan-only branches may produce:
- architecture docs
- JSON/Markdown plans
- analysis schemas
- guide-only MIDI/region data
- Logic manual instructions

Plan-only branches must not print or imply `COMPLETE`.

Final-WAV-complete is allowed only after:
- final WAV exists and is non-empty
- requested format/sample rate/24-bit PCM are verified
- peak/RMS/clipping metrics are verified
- QC report exists
- master QC report exists when required
- `src/completion_gate.py` returns complete
- `src/main.py` prints `COMPLETE`

## Generated Artifact Cleanup Plan

Before merging each branch:
- remove generated final WAVs
- remove temporary working WAVs
- remove fallback processing logs unless intentionally updated docs
- remove final verification JSON generated by local runs
- remove generated MIDI files unless intentional fixtures
- keep only source code, tests, templates, and docs
- review `git status --short`

## Recommended Merge Order

1. `feature/21-audio-capability-registry`
2. `feature/22-sample-mir-analysis`
3. `feature/23-vocal-to-code`
4. `feature/24-song-structure-analysis`
5. `feature/25-arrangement-autopilot`
6. `feature/26-midi-region-logic-guides`
7. `feature/27-mix-master-autopilot`
8. `feature/28-render-export-verification`
9. `feature/29-commercial-qc-completion`
10. `feature/30-integration-tests-release`

Each branch should merge only after tests pass and the worktree is clean of accidental generated artifacts.
