# AI_BEAT_LOGIC_WORKFLOW

Local Suno-to-Logic beat post-production workflow for digicore, hyperpop, and underground hip-hop instrumentals.

This project is designed to turn a Suno-generated MP3/WAV sketch into a cleaner, more intentional, human-produced instrumental beat. The core priority is to preserve the main melody and emotional atmosphere while reducing fake vocal textures, random AI artifacts, weak section logic, generic loop feel, harsh low-end distortion, and over-mastered exports.

## Current Scope

This first branch contains the repository scaffold, branch strategy, and initial CLI skeleton. It does not claim to finish audio processing yet. The CLI can:

- create the required folder structure
- collect or default the production choices
- sanitize and copy a user input file into `00_INPUT_SUNO/`
- write initial session settings
- write starter analysis, edit-plan, and QC report files
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

Initialize the folders and write starter artifacts:

```bash
python3 AI_BEAT_LOGIC_WORKFLOW/scripts/ai_beat_logic_workflow.py init
```

Start a session with an input file:

```bash
python3 AI_BEAT_LOGIC_WORKFLOW/scripts/ai_beat_logic_workflow.py prepare --input "/path/to/suno_track.mp3" --non-interactive
```

Run tests:

```bash
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
```

## Completion Rule

Do not mark a production run as complete unless the final WAV file exists and its duration, format, and peak have been verified.
