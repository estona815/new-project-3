# Branch Plan

Repository: `AI_BEAT_LOGIC_WORKFLOW`

## Branch Order

1. `main`
2. `dev`
3. `feature/00-project-scaffold`
4. `feature/01-input-ingest-convert`
5. `feature/02-c-wav-tools`
6. `feature/03-python-analysis-engine`
7. `feature/04-edit-plan-generator`
8. `feature/05-logic-pro-integration`
9. `feature/06-fallback-processing`
10. `feature/07-export-qc-report`
11. `feature/08-tests-docs-release`

`main` is stable. `dev` is integration. Every `feature/*` branch is created from `dev`, tested in isolation, committed, and merged back to `dev` only after verification passes.

## Permanent Branches

### `main`

Purpose:
- Stable branch only.
- Contains tested releases from `dev`.

Acceptance criteria:
- Release candidate from `dev` has passing tests.
- Final WAV completion is never claimed unless a real final WAV exists and its duration, format, and peak are verified.
- External dependencies are reported accurately when missing.

Test commands:

```bash
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
python3 AI_BEAT_LOGIC_WORKFLOW/scripts/ai_beat_logic_workflow.py init
```

Merge order:
- Merge `dev` into `main` only for tagged or release-ready states.

Rollback strategy:
- Revert the release merge commit on `main`.
- Keep the faulty work on `dev` or a repair branch until fixed.

### `dev`

Purpose:
- Integration branch.
- Receives all feature branches first.

Acceptance criteria:
- Feature branch tests pass before merge.
- No unrelated workspace files are staged.
- Documentation and generated artifacts stay in sync with source scripts.

Test commands:

```bash
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
python3 AI_BEAT_LOGIC_WORKFLOW/scripts/ai_beat_logic_workflow.py init
```

Merge order:
- Merge feature branches in numeric order.

Rollback strategy:
- Revert the faulty feature merge commit on `dev`.
- If the branch was not merged, delete or reset only that feature branch after confirming no needed work would be lost.

## Feature Branches

### `feature/00-project-scaffold`

Purpose:
- Required folder structure.
- README.
- CLI skeleton.
- Config schema and default options.

Acceptance criteria:
- All required directories exist.
- CLI can initialize the workflow.
- Defaults match the requested production defaults.
- Starter analysis, edit-plan, and QC files are clearly marked pending.
- No final WAV completion is claimed.

Test commands:

```bash
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
python3 AI_BEAT_LOGIC_WORKFLOW/scripts/ai_beat_logic_workflow.py init
python3 -m py_compile AI_BEAT_LOGIC_WORKFLOW/scripts/ai_beat_logic_workflow.py AI_BEAT_LOGIC_WORKFLOW/src/workflow.py
```

Merge order:
- Create from `dev`.
- Commit scaffold changes.
- Merge into `dev` before any audio implementation branch starts.

Rollback strategy:
- Revert the scaffold merge on `dev` if the layout or CLI contract is wrong.
- Preserve user audio and unrelated files.

### `feature/01-input-ingest-convert`

Purpose:
- Copy the input MP3/WAV into `00_INPUT_SUNO/`.
- Sanitize filename.
- Preserve original files and never overwrite.
- Detect `ffmpeg` and `afconvert`.
- Convert to `04_PROCESSED_AUDIO/working_input.wav`, preferring 32-bit float WAV for internal processing where supported.

Acceptance criteria:
- Missing input paths fail with a clear error.
- Unsupported extensions fail with a clear error.
- Repeated imports create unique copies.
- Converter detection reports actual availability.
- Working WAV exists only after successful conversion.

Test commands:

```bash
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
command -v ffmpeg || true
command -v afconvert || true
```

Merge order:
- Create from `dev` after `feature/00-project-scaffold` is merged.
- Merge into `dev` after copy/conversion tests pass.

Rollback strategy:
- Revert the feature merge on `dev`.
- Delete only generated test outputs created inside `00_INPUT_SUNO/` or `04_PROCESSED_AUDIO/` after confirming they are not user originals.

### `feature/02-c-wav-tools`

Purpose:
- Add C WAV helper tools:
  - `tools/wav_analyzer.c`
  - `tools/wav_gain_stage.c`
  - `tools/wav_trim_fade.c`
  - `tools/wav_integrity_check.c`
- Add `Makefile`.
- Add CLI usage docs.

Acceptance criteria:
- Tools compile on macOS with the system C compiler.
- Tools fail clearly on unsupported or corrupt WAV input.
- Tools do not modify original source audio.
- CLI docs include example commands and expected outputs.

Test commands:

```bash
make -C AI_BEAT_LOGIC_WORKFLOW/tools
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
```

Merge order:
- Create from `dev` after ingest/conversion is merged.
- Merge into `dev` after compile and fixture checks pass.

Rollback strategy:
- Revert the feature merge on `dev`.
- Remove compiled binaries with `make -C AI_BEAT_LOGIC_WORKFLOW/tools clean` if that target exists.

### `feature/03-python-analysis-engine`

Purpose:
- Python audio analysis for duration, peak, RMS, estimated LUFS, clipping, and silence.
- Low-end excess detection.
- Vocal-like texture candidate detection.
- Melody-buried candidate detection.
- Intro, hook, drop, and outro section candidates.

Acceptance criteria:
- `01_ANALYSIS/analysis.json` contains measured fields, not placeholders, when an input exists.
- `analysis_summary.md` explains results without pretending heuristic detections are certain.
- Estimated LUFS is labeled as an estimate unless a true loudness implementation is available.
- Edge cases for silence, clipping, and short audio are covered by tests.

Test commands:

```bash
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
python3 AI_BEAT_LOGIC_WORKFLOW/scripts/ai_beat_logic_workflow.py init
```

Merge order:
- Create from `dev` after C tools are merged or after deciding Python-only analysis is sufficient for this phase.
- Merge into `dev` after dummy WAV fixture tests pass.

Rollback strategy:
- Revert the feature merge on `dev`.
- Keep generated analysis files only if they are useful fixtures; otherwise regenerate from source scripts.

### `feature/04-edit-plan-generator`

Purpose:
- Generate `02_EDIT_PLAN/edit_plan.md`.
- Include Logic Pro manual editing instructions.
- Include arrangement, melody-forward mix, drum/808 balance, and AI-feel reduction guidance.

Acceptance criteria:
- Edit plan reflects analysis results when available.
- Manual Logic instructions are exact enough to follow if automation is blocked.
- Plan emphasizes melody preservation, vocal texture suppression, controlled low end, and headroom.
- No claim is made that Logic edits were performed unless automation actually succeeds.

Test commands:

```bash
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
python3 AI_BEAT_LOGIC_WORKFLOW/scripts/ai_beat_logic_workflow.py init
```

Merge order:
- Create from `dev` after analysis engine is merged.
- Merge into `dev` after plan generation tests pass.

Rollback strategy:
- Revert the feature merge on `dev`.
- Regenerate `edit_plan.md` from the previous stable generator if needed.

### `feature/05-logic-pro-integration`

Purpose:
- Detect macOS and Logic Pro availability.
- Add optional AppleScript or `osascript` automation.
- Create/import/save a Logic project where possible.
- Never pretend Logic automation succeeded if it failed.

Acceptance criteria:
- Logic Pro detection reports real availability.
- Automation failures are written to the run output and edit plan.
- Project file is only reported saved if it exists.
- Fallback instructions remain available when Logic automation is blocked.

Test commands:

```bash
uname -s
command -v osascript || true
osascript -e 'id of app "Logic Pro"' || true
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
```

Merge order:
- Create from `dev` after edit-plan generation is merged.
- Merge into `dev` after detection and failure-path tests pass.

Rollback strategy:
- Revert the feature merge on `dev`.
- Do not delete user-created Logic projects unless explicitly requested.

### `feature/06-fallback-processing`

Purpose:
- Fallback trim, fade, and gain staging.
- Optional EQ through ffmpeg filters where available.
- Export WAV even if Logic Pro automation fails.
- Preserve musical intent as much as possible.

Acceptance criteria:
- Fallback processing runs without Logic Pro.
- Missing `ffmpeg` is reported and an available alternative path is used where possible.
- Processing leaves headroom and avoids over-mastering.
- Original input files are never modified.

Test commands:

```bash
command -v ffmpeg || true
command -v afconvert || true
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
```

Merge order:
- Create from `dev` after Logic integration failure-path handling is merged.
- Merge into `dev` after fallback export tests pass.

Rollback strategy:
- Revert the feature merge on `dev`.
- Remove only generated fallback test exports inside `04_PROCESSED_AUDIO/` and `05_FINAL_WAV/`.

### `feature/07-export-qc-report`

Purpose:
- Final WAV export.
- Optional MP3 preview.
- Verify output file existence.
- Verify metadata.
- Generate `06_QC_REPORT/qc_report.md`.

Acceptance criteria:
- Final WAV exists before completion is claimed.
- Duration, format, and peak are verified.
- QC report includes all required sections.
- MP3 preview is optional and never replaces the final WAV.
- True peak target around `-1.0 dBTP` is respected where measurement support exists.

Test commands:

```bash
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
command -v ffmpeg || true
afinfo AI_BEAT_LOGIC_WORKFLOW/05_FINAL_WAV/final_suno_logic_processed_24bit_48k.wav || true
```

Merge order:
- Create from `dev` after fallback processing is merged.
- Merge into `dev` after export and QC verification pass.

Rollback strategy:
- Revert the feature merge on `dev`.
- Move bad generated exports out of release paths or delete only generated test outputs.

### `feature/08-tests-docs-release`

Purpose:
- Integration test with dummy WAV.
- README finalization.
- Troubleshooting.
- Release checklist.

Acceptance criteria:
- Dummy WAV integration test covers ingest, analysis, fallback processing, export, and QC report generation.
- README documents dependencies and missing-dependency behavior.
- Troubleshooting covers Logic Pro, `ffmpeg`, `afconvert`, permissions, and final WAV verification.
- Release checklist blocks release if final WAV verification is missing.

Test commands:

```bash
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
python3 AI_BEAT_LOGIC_WORKFLOW/scripts/ai_beat_logic_workflow.py init
command -v ffmpeg || true
command -v afconvert || true
command -v osascript || true
```

Merge order:
- Create from `dev` after export/QC reporting is merged.
- Merge into `dev` after integration tests pass.
- Merge `dev` into `main` only after release checklist passes.

Rollback strategy:
- Revert the release-prep merge on `dev`.
- If already promoted, revert the release merge on `main` and fix forward on `dev`.

## External Dependency Detection

Do not write fake dependency results. Detection commands must report the current machine state:

```bash
command -v ffmpeg || true
command -v afconvert || true
command -v osascript || true
osascript -e 'id of app "Logic Pro"' || true
```

If a dependency is missing:
- Report it in the terminal output, generated report, or QC notes.
- Use the documented fallback path if available.
- Do not claim automation, conversion, export, or verification succeeded.

## Merge Order

```text
feature/00-project-scaffold -> dev
feature/01-input-ingest-convert -> dev
feature/02-c-wav-tools -> dev
feature/03-python-analysis-engine -> dev
feature/04-edit-plan-generator -> dev
feature/05-logic-pro-integration -> dev
feature/06-fallback-processing -> dev
feature/07-export-qc-report -> dev
feature/08-tests-docs-release -> dev
dev -> main
```

## Rollback Strategy

- Prefer `git revert` for merged work so history stays auditable.
- Revert the smallest bad merge or commit.
- Never use destructive Git commands such as `git reset --hard` unless explicitly requested.
- Do not delete original user audio.
- For generated artifacts, remove only files known to be produced by tests or the current workflow run.
- If an external dependency is missing, keep the code path and mark the feature blocked or partially verified rather than inventing a successful result.

