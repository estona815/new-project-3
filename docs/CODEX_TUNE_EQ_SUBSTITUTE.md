# Codex Tune/EQ Substitute

This repo cannot honestly claim to clone Antares Auto-Tune or FabFilter Pro-Q. The substitute route is practical:

- Use REAPER stock `ReaTune` as the pitch-correction engine.
- Use `Codex Vocal Pitch Monitor` to show key/scale target, estimated pitch, and cents error before/around ReaTune.
- Use `Codex Pro Dynamic MS EQ` as a local dynamic M/S EQ for mud, harshness, sibilance, and AI fizz control.
- Use the existing claim/QC harness before saying `vocal tuned`, `noise removed`, or `mastered`.

## Files

- `reaper/jsfx/codex_vocal_pitch_monitor.jsfx`
- `reaper/jsfx/codex_pro_dynamic_ms_eq.jsfx`
- `scripts/apply_codex_tune_eq_substitute.lua`
- `presets/tune_eq_substitute/vocal_clean_default.json`

## What This Can Replace

### Auto-Tune Replacement Route

Use this when Antares is unavailable:

1. Put the isolated vocal stem on a REAPER track.
2. Insert `Codex Vocal Pitch Monitor`.
3. Insert `ReaTune`.
4. Set key/scale manually or from a validated key report.
5. Render a vocal-only before/after check.
6. Do not claim `vocal tuned` until pitch-correction settings and before/after evidence exist.

This is not Antares Graph Mode, Flex-Tune, formant/throat modelling, or note-by-note manual tuning. It is a free REAPER-native pitch correction route.

### FabFilter Replacement Route

Use `Codex Pro Dynamic MS EQ` for:

- Band 1: low-mid mud/box control.
- Band 2: upper-mid harshness/resonance control.
- Band 3: de-ess/sibilance control.
- Band 4: side-aware 10-16 kHz AI fizz/air wash control.

This is not Pro-Q's full UI, spectral dynamics, linear phase engine, or advanced analyzer. It is a deterministic REAPER JSFX that the harness can audit.

## REAPER Command

Load the Lua script from REAPER Actions or run it with REAPER ReaScript:

```sh
/Applications/REAPER.app/Contents/MacOS/REAPER -newinst -nosplash
```

Then run:

`scripts/apply_codex_tune_eq_substitute.lua`

The script targets selected tracks first. If no tracks are selected, it searches for track names containing `vocal`, `vox`, or `lead`.

## Claim Policy

Allowed:

- `ReaTune-based vocal pitch correction route`
- `Codex dynamic M/S EQ`
- `fullmix-derived vocal-focused processing` when no isolated vocal exists
- `requires human listening`

Forbidden without evidence:

- `Antares-quality tuning`
- `FabFilter clone`
- `vocal tuned`
- `pitch corrected`
- `noise completely removed`
- `professional final master`

## Next Upgrade

The highest-value next step is a pitch audit that exports:

- estimated key
- pitch contour
- corrected note targets
- before/after cents error
- vocal-only A/B preview

That evidence is what lets the system move from `tune route inserted` to a real `vocal tuned` claim.
