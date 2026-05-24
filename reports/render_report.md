
# Render Report

- REAPER render scripts were generated for premaster and master targets.
- This Codex patch did not claim a verified REAPER audio render because REAPER was not run and no rendered files were verified in this turn.
- Expected render targets:
  - `renders/PREMASTER_24bit_48k.wav`
  - `renders/MASTER_24bit_48k.wav`
  - `renders/MASTER_320k.mp3` if ffmpeg is available
- Run the generated REAPER project script, inspect plugin insertions, then run the render script.
