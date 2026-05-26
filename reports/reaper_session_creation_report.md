# REAPER Session Creation Report

- Status: created and saved.
- Project: `reaper/FRESH_MIX_REBUILD.rpp`
- Verified time: 2026-05-24 17:04 KST

## Error Cause

- The old launch command used `-reascript`, but REAPER v7.73 command-line help does not list or support that option.
- Passing the Lua file directly works, but the project path contains spaces, so the launch now uses a no-space `/tmp/codex_fresh_reaper/run_build_fresh_mix.lua` wrapper that calls the real script with `dofile()`.
- Automatic `.mid` import caused REAPER to wait on MIDI import options. Guide MIDI is now represented as muted placeholder tracks with source-path metadata instead of imported MIDI items.
- `InsertMedia()` advanced the edit cursor, placing stems sequentially. The script now resets the edit cursor and all inserted items to position `0.0`.

## Verification

- Wrapper log reached `wrapper ok`.
- All audio/reference items in the saved `.rpp` have `POSITION 0`.
- `REF_BUS`, reference tracks, guide MIDI placeholders, and quarantine tracks are muted.
- `03_FX.wav` and `08_Guitar.wav` remain routed to `ARTIFACT_QUARANTINE_BUS`.
- `12_Vocals.wav` is active on `MALE_LEAD_VOX_BUS`.
- Required vocal FX sends and master routing buses exist.

## Next Manual Step

- Open `reaper/FRESH_MIX_REBUILD.rpp`, verify stock fallback FX insertion, then manually upgrade detected plugins only where they actually load.
- Do vocal tuning and balance by ear before running `reaper/render_fresh_mix.lua`.
