# Release-Ready Implementation Plan

Base branch: `feature/30-integration-tests-release`

Target branch sequence starts with `feature/31-release-ready-autopilot`.

Branch rule: create each branch from the previous passing branch, implement only the listed scope, add focused tests, run verification, and avoid committing generated WAV/log/report/MIDI artifacts unless they are intentional fixtures.

## Acceptance Criteria

- `docs/RELEASE_READY_AUTOPILOT_ARCHITECTURE.md` exists.
- `docs/RELEASE_READY_IMPLEMENTATION_PLAN.md` exists.
- Branch plan is clear and ordered.
- Plan-only, demo render, final master, and release package statuses are distinct.
- Stereo-only and stem-mode claims are honest.
- Exact-copy and living artist voice-clone policies are explicit.
- Release package scope states that it does not guarantee distribution approval or commercial success.
- No generated audio, logs, reports, MIDI files, or temporary build artifacts are committed accidentally.

## Branch Plan

### `feature/31-release-ready-autopilot`

Scope:
- Add top-level workflow orchestration for release-ready autopilot.
- Convert rough request to a release-ready flow plan.
- Update status model to distinguish plan-only, analysis, guide, demo render, verified final WAV, release package, and complete.
- Write production intent artifacts for rough Korean/English requests.
- Keep `COMPLETE` gated through `src/main.py` and `src/completion_gate.py`.

Implementation targets:
- `src/main.py`
- `src/user_options.py`
- `src/production_intent_resolver.py`
- `src/autopilot_status.py`
- `src/export_status.py`
- `src/completion_gate.py`
- README and release-ready docs

Tests:
- rough request creates intent/status artifacts
- `song_to_mix_master` enters full orchestration
- plan-ready statuses do not print `COMPLETE`
- copying-risk requests are marked unsafe for exact copying
- release-ready wording does not promise distribution approval or commercial success

Out of scope:
- no new composition algorithms beyond intent-level ideas
- no final release package folder builder yet
- no new plugin automation claims

Merge gate:
- focused unit tests pass
- full unittest suite passes when practical
- `git diff --check` passes
- generated artifact scan is clean

### `feature/32-composition-autopilot`

Scope:
- Add composition idea generation from rough request, sample analysis, vocal code, song structure, and stems metadata.
- Generate chord, melody, bass/808, and drum guide ideas.
- Preserve no-exact-copy policy for references and samples.
- Treat style clusters as high-level production direction only.

Implementation targets:
- composition idea module
- chord/progression guide updates
- melody variation guide updates
- bass/808 guide updates
- drum guide updates
- Korean production-request parser tests

Tests:
- commercial/digicore/hyperpop requests create usable composition directions
- sample/vocal inputs influence guides without exact transcription claims
- `따와라`, `가져와라`, `똑같이`, `그대로` remain copying-risk unless owned/cleared local source is confirmed
- living artist vocal references become production traits only

Out of scope:
- no final audio render changes
- no release package builder
- no claimed MIDI import into Logic

Merge gate:
- composition guide tests pass
- copying policy tests pass
- generated artifact cleanup confirmed

### `feature/33-arrangement-to-production-package`

Scope:
- Convert arrangement plans into a Logic production package.
- Consolidate MIDI, region, automation, section marker, drum, bass/808, chord, vocal, and sample-chop guides.
- Make package outputs clear, practical, and manual-execution oriented.

Implementation targets:
- arrangement package builder
- MIDI/region guide consolidation
- automation guide consolidation
- Logic manual plan renderer
- guide schemas and docs

Tests:
- arrangement package includes all expected guide files
- MIDI/region/automation guides are guide-only
- Logic manual plan includes manual requirements and no fake automation success
- stereo-only arrangements keep limitation language
- stem-mode arrangements expose more direct but verified-only capabilities

Out of scope:
- no actual Logic UI automation guarantee
- no verified plugin insertion
- no final master or release package builder

Merge gate:
- guide tests pass
- Logic/manual claim-safety tests pass
- no generated MIDI/report artifacts staged unless intentional fixtures

### `feature/34-universal-mix-master-autopilot`

Scope:
- Add universal mix/master planning for song, sample, stems, vocal, and full-stereo modes.
- Define final render modes and limitations.
- Distinguish demo render from final master.
- Keep plugin requests manual or approximation-only unless verified.

Implementation targets:
- mix/master autopilot module
- render orchestrator
- master target modes
- vocal mix plans
- stem mix plans
- fallback processing status

Tests:
- full stereo mode stays broad and heuristic
- stem mode allows direct stem planning but remains verification-gated
- demo render does not count as final master
- final master requires format/audio verification
- plugin request tests block false AutoTune/Decapitator claims

Out of scope:
- no release package builder
- no distribution metadata
- no guaranteed commercial loudness approval

Merge gate:
- mix/master tests pass
- final render status tests pass
- no generated WAVs committed

### `feature/35-release-package-builder`

Scope:
- Build final deliverables folder or manifest.
- Generate metadata sheet.
- Generate rights/safety checklist.
- Generate release QC report.
- Create alternate deliverables when possible, such as MP3 preview, instrumental, radio edit, short-form cut, or stems, only if the required source artifacts exist.

Implementation targets:
- release package builder
- release metadata schema
- rights/safety checklist renderer
- release QC renderer
- alternate-deliverables planner
- docs/README updates

Tests:
- verified final WAV creates release package manifest
- missing final WAV blocks package readiness
- missing QC/master QC blocks release package
- alternate deliverables are listed as unavailable instead of faked
- release package states no distribution approval or commercial success guarantee

Out of scope:
- no upload to distributors
- no rights clearance validation beyond user-provided checklist
- no external platform approval checks

Merge gate:
- release package tests pass
- generated artifact scan is clean
- no final audio artifacts staged unless intentional fixtures

### `feature/36-final-release-qc-integration`

Scope:
- Integrate release package into completion gate.
- Add release status model and final audit.
- Add integration tests across representative workflows.
- Finalize docs and release checklist.

Implementation targets:
- completion gate
- release status model
- autopilot QC report
- commercial readiness QC
- integration tests
- release checklist docs

Tests:
- plan-only never completes
- demo render never completes as final master
- verified final WAV without release package blocks completion
- release package with failing safety QC blocks completion
- release package with verified WAV, QC reports, safety notes, and checklist allows final complete
- `COMPLETE` literal remains printed only from `src/main.py`
- generated artifact cleanliness test passes

Out of scope:
- no new creative feature work
- no exact-copy exception beyond owned/cleared local material policy
- no living artist voice clone support

Merge gate:
- full unittest suite passes
- C helper smoke tests pass
- `git diff --check` passes
- final generated artifact audit is clean

## Cross-Branch Safety Rules

- Reference prompts are high-level production targets only.
- Do not copy exact songs, kick samples, basslines, melodies, lyrics, drum patterns, or sound recordings.
- Do not clone living artist vocal identity.
- Do not claim Logic automation success without verified artifacts.
- Do not claim plugin insertion or plugin processing without verified artifacts.
- Do not claim stem-level remixing, guaranteed vocal removal, true kick/bass replacement, true drum rewrite, or true stem separation from stereo-only input.
- `COMPLETE` may print only from `src/main.py` after `src/completion_gate.py` passes.

## Artifact Cleanup Plan

Before each branch is considered ready:
- run `git status --short --branch`
- scan output folders for generated WAV/log/report/MIDI artifacts
- remove only artifacts created by the branch verification run
- leave unrelated untracked workspace files untouched
- confirm generated C helper binaries and temporary test artifacts are cleaned or ignored

Project output folders to scan:
- `00_INPUT_SUNO/`
- `01_ANALYSIS/`
- `02_EDIT_PLAN/`
- `03_LOGIC_PROJECT/`
- `04_PROCESSED_AUDIO/`
- `05_FINAL_WAV/`
- `06_QC_REPORT/`
- `07_VOCAL_PROCESSING/`
- `08_REFERENCE_MATCH/`
- `09_MIX_MASTER/`

## Verification Checklist

Recommended per branch:
- narrow focused unit tests first
- full `python3 -m unittest discover -s tests -v` before merge when practical
- `make -C tools test` when C helpers or render verification are relevant
- `git diff --check -- .`
- generated artifact scan

If `pytest` is unavailable, report it as a dependency block, not a code failure.
