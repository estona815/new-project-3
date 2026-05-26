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

## Vocal Mix Modes

Use `--mode vocal_plus_beat` only when you have a separate vocal file and beat file. Use `--mode full_song_stereo` when the vocal is already embedded in a stereo song; in that mode the workflow can only do broad mastering-style processing and heuristic vocal-region analysis. Use `--mode stems` only for stems actually provided by the user.

The workflow must not claim real vocal removal from stereo, exact reference-song copying, artist/producer cloning, or stem-level drum changes without stems. Autotune requests are documented as unavailable unless a supported local pitch tool is detected.

## Melody Still Buried

Use `02_EDIT_PLAN/edit_plan.md` to identify melody-buried candidates. In Logic, automate melody up, reduce 808/drum bus during the hook, and carve low-mid mud. Stereo fallback cannot independently rebalance melody stems.

## Final WAV Not Created

Check these files:

- `01_ANALYSIS/conversion_error.md`
- `04_PROCESSED_AUDIO/processing_log.md`
- `06_QC_REPORT/final_verification.json`

The CLI will not print `COMPLETE` unless `src/completion_gate.py` verifies the final WAV, requested 24-bit PCM format/sample rate, audio metrics, QC report, and any required master QC report.

## Permission Issues On macOS

Logic/AppleScript automation may require Accessibility permissions. Grant Terminal/Codex/osascript permissions in System Settings, or follow the manual Logic checklist in `02_EDIT_PLAN/edit_plan.md`.
