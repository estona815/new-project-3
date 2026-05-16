# AI_BEAT_LOGIC_WORKFLOW

Local Suno-to-Logic beat post-production workflow for digicore, hyperpop, and underground hip-hop instrumentals.

## Project Goal

Turn a Suno-generated MP3/WAV sketch into a cleaner, more intentional, melody-forward instrumental beat. The workflow preserves the main melody and emotional atmosphere while reducing obvious AI artifacts, fake vocal textures, weak section logic, generic loop feel, harsh low-end distortion, and over-mastered output.

## What It Can Do

- Create the required project folder structure.
- Collect production choices through CLI flags or interactive prompts.
- Copy and sanitize input audio without overwriting originals.
- Convert supported audio to `04_PROCESSED_AUDIO/working_input.wav`.
- Analyze metadata, levels, clipping, silence, low-end risk, vocal-like texture candidates, melody-buried candidates, and section candidates.
- Generate a producer-readable edit plan for Logic Pro/manual editing.
- Attempt optional Logic Pro automation and write a status report without fake success claims.
- Run conservative stereo-only fallback processing: trim, fade, gain-stage, basic EQ/compression when tools support it, and verification.
- Export a final WAV and write a QC report only after the file exists and verification passes.

## What It Cannot Do

- It cannot truly remix stems from a single stereo file unless stem separation is added.
- It cannot guarantee real vocal removal; vocal-like detection is heuristic unless a real model is added.
- It cannot fully automate Logic Pro mixing, plugin insertion, region edits, or automation curves.
- It cannot replace human listening and arrangement judgment.
- It must not claim production completion unless final WAV verification and QC report creation pass.

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

Run with explicit options:

```bash
python3 AI_BEAT_LOGIC_WORKFLOW/src/main.py \
  --input "/path/to/suno_song.mp3" \
  --length-mode "under_2min" \
  --vocal-mode "suppress" \
  --melody-focus "front" \
  --drum-808 "strong_controlled" \
  --export-format "wav24_48k" \
  --save-logic-project true
```

Interactive mode:

```bash
python3 AI_BEAT_LOGIC_WORKFLOW/src/main.py --interactive
```

Logic-only status attempt:

```bash
python3 AI_BEAT_LOGIC_WORKFLOW/src/main.py --logic-only
```

Generate and run the dummy integration fixture:

```bash
python3 AI_BEAT_LOGIC_WORKFLOW/tests/generate_dummy_audio.py
python3 AI_BEAT_LOGIC_WORKFLOW/src/main.py --input AI_BEAT_LOGIC_WORKFLOW/tests/fixtures/dummy_suno_like.wav
```

## Output Folders

- `00_INPUT_SUNO/`: sanitized copy of the original source audio.
- `01_ANALYSIS/`: input metadata, analysis JSON, and producer-readable analysis summary.
- `02_EDIT_PLAN/`: manual Logic/edit plan.
- `03_LOGIC_PROJECT/`: Logic automation status and optional `.logicx` project.
- `04_PROCESSED_AUDIO/`: working WAV, fallback processed WAV, and processing log.
- `05_FINAL_WAV/`: final WAV and optional MP3 preview.
- `06_QC_REPORT/`: final verification JSON and QC report.

## QC Report

`06_QC_REPORT/qc_report.md` records exactly what happened. If fallback processing was used, it says so. It includes input file details, final export metadata, melody preservation notes, vocal-like texture notes, drum/808 balance warnings, clipping/loudness checks, AI-feel reduction notes, remaining problems, and next improvement options.

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

The CLI prints `COMPLETE` only if the final WAV exists, verification passed, and `qc_report.md` exists.
