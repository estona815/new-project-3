# Troubleshooting

## ffmpeg Missing

Install ffmpeg with Homebrew:

```bash
brew install ffmpeg
```

Without ffmpeg, the workflow tries macOS `afconvert`. MP3 preview export is skipped if ffmpeg is unavailable.

## afconvert Missing

`afconvert` is normally included on macOS. If both ffmpeg and afconvert are missing, input conversion or final export will fail cleanly. Install ffmpeg or run on a macOS machine with the command-line audio tools available.

## Logic Pro Not Detected

The workflow checks `/Applications/Logic Pro.app`. If Logic Pro is elsewhere or not installed, Logic automation is marked unavailable and fallback processing is used. Check `03_LOGIC_PROJECT/logic_automation_status.md`.

## Input File Cannot Be Read

Supported extensions are `.mp3`, `.wav`, `.aiff`, `.aif`, `.flac`, and `.m4a`, depending on the available converter. If conversion fails, inspect `01_ANALYSIS/conversion_error.md`.

## Output Clipping

Check `06_QC_REPORT/qc_report.md` and `06_QC_REPORT/final_verification.json`. If peak is too high or clipping is detected, lower fallback gain, avoid limiter abuse, or revise the mix in Logic.

## Vocal Texture Still Audible

Fallback processing is stereo-only and cannot truly remove vocals. Use manual Logic editing, stem separation, clip gain, EQ, or arrangement changes. The report marks vocal-like regions as heuristic candidates, not confirmed vocals.

## Melody Still Buried

Use `02_EDIT_PLAN/edit_plan.md` to identify melody-buried candidates. In Logic, automate melody up, reduce 808/drum bus during the hook, and carve low-mid mud. Stereo fallback cannot independently rebalance melody stems.

## Final WAV Not Created

Check these files:

- `01_ANALYSIS/conversion_error.md`
- `04_PROCESSED_AUDIO/processing_log.md`
- `06_QC_REPORT/final_verification.json`

The CLI will not print `COMPLETE` unless final WAV verification passes and the QC report exists.

## Permission Issues On macOS

Logic/AppleScript automation may require Accessibility permissions. Grant Terminal/Codex/osascript permissions in System Settings, or follow the manual Logic checklist in `02_EDIT_PLAN/edit_plan.md`.

