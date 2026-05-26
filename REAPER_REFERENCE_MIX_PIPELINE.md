# REAPER Reference Mix Pipeline

Use this route for future user-owned REAPER mix/master revisions in this workspace, especially Hangang Shadow-style stem work.

## Default Route

1. Start from the latest timing-approved session, not the loudest or newest render.
2. Inspect source stems, previous render notes, alignment reports, and current user complaints before changing sound.
3. Preserve song timing and arrangement unless the user explicitly asks for edits.
4. Keep reference/full-mix tracks muted and out of the active premaster bus.
5. Build a new versioned REAPER folder under `reaper/<song_slug_vNN>`.
6. Put processed side assets under `audio_work/<song_slug_vNN>`.
7. Render into `renders/<song_slug_vNN>`.
8. Write QC and decision notes under `reports/<song_slug_vNN>`.
9. Render premaster and REAPER print first, then run loudness/brickwall conversion and MP3 export.
10. Create a final deliverable ZIP only after measured QC passes.

## Hangang Shadow Defaults

- Male lead is the main vocal when `12 Vocals.wav` is present.
- Female vocal is never the lead by default. Use it only as a quiet panned adlib/double layer where timing and pitch overlap pass alignment checks.
- Remove or mute female regions that are off-grid, off-pitch, or feel like intro chops.
- Do not repeat the rejected v24 direction: do not activate the new female instrumental bed to glue the beat.
- Favor the v23/v25/v27 timing-safe structure for revisions.
- Keep vocal slightly tucked if the user says the vocal feels over-forward.
- Improve kick/bass with controlled saturation/body, not broad level pushing.
- Make the main melody clearer by taming resonances first, then adding embedded M/S presence.
- Reduce synthetic AI-like top glare before boosting air.

## Reference-Informed Pass

When the user provides a reference folder or track:

1. Treat the reference as user-provided context and analyze the actual audio before changing the mix.
2. Measure at least LUFS, LRA, true peak, RMS/crest, stereo correlation, side-mid level, and spectral bands.
3. Compare the current approved master to the reference median or selected reference track.
4. Translate traits conservatively. Do not chase clipped true peaks or claim an identical match.
5. Keep status as `genre_based_draft` unless lawful source/reference analysis plus user listening feedback supports stronger claims.

For the Estona/Nib reference-set pass, the useful translation was:

- Slightly louder but true-peak-safe final master.
- More low-end density and kick/bass saturation.
- Wider music bed.
- Less 1.5-5 kHz and upper-air glare.
- Melody readable but still embedded.

## REAPER Execution Pattern

Use a deterministic wrapper sequence:

1. `run_build_<slug>.lua` opens REAPER and builds/saves the versioned `.rpp`.
2. `run_render_<slug>_premaster.lua` prepares a premaster render project with print FX disabled.
3. `REAPER -newinst -nosplash -renderproject /tmp/..._PREMASTER_RENDER.rpp`
4. `run_render_<slug>_master.lua` prepares a REAPER print render project with print FX enabled.
5. `REAPER -newinst -nosplash -renderproject /tmp/..._REAPERPRINT_RENDER.rpp`
6. `tools/<slug>_qc.py` runs final loudness/brickwall conversion, MP3 export, metrics, CSV/JSON audit, notes, and optional final ZIP.

Wait for wrapper logs to show `wrapper ok` before rendering. If a wrapper logs an error, fix the script before continuing.

## QC Gate

Before delivering, confirm:

- Final WAV exists.
- Final MP3 exists when requested or useful.
- True peak is safe after WAV and encoded MP3 checks.
- Loudness target is measured, not guessed.
- Reference/full-mix tracks remained muted.
- Notes explain what changed, what did not change, and the remaining limitation.

Do not say the result is commercially finished or reference-matched unless those claims are supported by measured analysis and user listening approval.
