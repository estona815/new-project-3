# AI_BEAT_LOGIC_WORKFLOW

Local Suno-to-Logic beat post-production workflow for digicore, hyperpop, and underground hip-hop instrumentals.

This project is designed to turn a Suno-generated MP3/WAV sketch into a cleaner, more intentional, human-produced instrumental beat. The core priority is to preserve the main melody and emotional atmosphere while reducing fake vocal textures, random AI artifacts, weak section logic, generic loop feel, harsh low-end distortion, and over-mastered exports.

## Current Scope

The current branch contains the scaffold plus input ingestion and working WAV conversion. It does not claim final mix, master, Logic automation, or QC completion yet. The CLI can:

- create the required folder structure
- collect or default the production choices
- load `config/defaults.json`
- copy supported source audio into `00_INPUT_SUNO/`
- sanitize filenames without overwriting existing files
- convert a source file into `04_PROCESSED_AUDIO/working_input.wav`
- write `01_ANALYSIS/input_metadata.json`
- write `01_ANALYSIS/conversion_error.md` on conversion failure
- print a clear configuration summary
- clearly mark final WAV export as pending until a real output exists and is verified

## Required Folder Structure

```text
AI_BEAT_LOGIC_WORKFLOW/
  00_INPUT_SUNO/
  01_ANALYSIS/
  02_EDIT_PLAN/
  03_LOGIC_PROJECT/
  04_PROCESSED_AUDIO/
  05_FINAL_WAV/
  06_QC_REPORT/
  tools/
  scripts/
  src/
  tests/
```

## Default Production Choices

If the user does not answer a prompt, the workflow defaults to:

- final length: under 2 minutes
- vocal handling: suppress vocal chops / no vocal texture
- main melody: forward
- drums and 808: strong but not covering melody
- final export: WAV 24-bit 48 kHz
- Logic project: save Logic project and final WAV if possible

## Quick Start

Show help:

```bash
python3 AI_BEAT_LOGIC_WORKFLOW/src/main.py --help
```

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

Supported input extensions are `.mp3`, `.wav`, `.aiff`, `.aif`, `.flac`, and `.m4a`. Conversion prefers `ffmpeg`; if `ffmpeg` is unavailable on macOS, it tries `afconvert`.

Run the questionnaire:

```bash
python3 AI_BEAT_LOGIC_WORKFLOW/src/main.py --interactive
```

The shell wrapper passes arguments to the same CLI:

```bash
AI_BEAT_LOGIC_WORKFLOW/scripts/run_workflow.sh --input dummy.wav
```

Run tests:

```bash
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
```

## Completion Rule

Do not mark a production run as complete unless the final WAV file exists and its duration, format, and peak have been verified.
