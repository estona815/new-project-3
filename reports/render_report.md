
# Render Report

- Fresh render setup generated: `reaper/render_fresh_mix.lua`.
- Fresh REAPER session creation verified: `reaper/FRESH_MIX_REBUILD.rpp` exists and was saved by REAPER at 2026-05-24 17:04 KST.
- Launch blocker fixed: REAPER v7.73 does not support the old `-reascript` command-line option; launch scripts now pass the Lua file as a direct script argument through a `/tmp/codex_fresh_reaper` wrapper.
- Expected outputs:
  - `renders/FRESH_PREMASTER_24bit_48k.wav`
  - `renders/FRESH_MASTER_24bit_48k.wav`
  - `renders/FRESH_MASTER_320k.mp3` if ffmpeg is available after WAV verification.
- Automatic REAPER render is not claimed until the `.rpp` opens, plugin insertion is inspected, and output files are verified.
- Guide MIDI tracks are muted placeholders in the auto-built session to avoid REAPER command-line MIDI import dialogs; import them manually if needed for pitch/key inspection.
- All imported WAV/MP3 reference/audio items were reset to position 0.0 seconds after insertion so stems align from the session start.
- Render intentionally not run yet: the session is render-ready, but vocal tuning, plugin insertion checks, delay throw automation, and human balance review must happen before printing a real premaster/master.
