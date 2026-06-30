# Plugin Policy

Plugin insertion is conservative and traceable. Missing plugins are logged and never treated as loaded.

## Available External Plugins

Use these only when already installed. Missing plugins must be logged, not treated as loaded:

`OTT`, `TDR Nova`, `TDR Kotelnikov`, `ClearMaster Audit`, `Graillon 3`, `BYOD`, `Decapitator`, `FreeClip`, `Fresh Air`, `IVGI2`, `Krush`, `MAutoPitch`, `mvMeter2`, `Ozone 12 Equalizer`, `Ozone Imager 2`, `Raum`, `UADx 1176 FET Compressor`, `UADx LA-2A Tube Compressor`, `ValhallaSupermassive`, `ValhallaVintageVerb`, `Vocal Doubler`, `Wider`.

## Required Clean Lead Vocal Chain

Use this order as the clean-main-vocal default when plugins are available:

1. `JS: Codex Vocal AI Artifact Split Tamer`
2. `JS: Vocal Clarity De-Mud Dynamic EQ`
3. `VST: ReaEQ (Cockos)` or `VST3: Ozone 12 Equalizer`
4. `VST3: TDR Nova (Tokyo Dawn Labs)`
5. `JS: De-esser`
6. `JS: Vocal Clarity Air Guard`
7. `VST3: UADx LA-2A Tube Compressor`
8. `VST3: UADx 1176 FET Compressor`
9. `JS: Vocal Clarity Output Guard`

The first FX slot on `08 MALE_NONHOOK_CENTER` must be `JS: Codex Vocal AI Artifact Split Tamer`.

Pitch tools (`Graillon 3`, `MAutoPitch`, `ReaTune`, `ReaPitch`) are not part of clean-main-vocal rescue unless explicitly authorized for stylized tuning. Saturators (`Decapitator`, `BYOD`, `IVGI2`, `Krush`) are parallel or special-effect tools, not first-line cleanup.

## Bus Chains

- `REF BUS`: `mvMeter2`, `ClearMaster Audit`; muted and not in the print path.
- `VOX BUS`: `TDR Nova`, `TDR Kotelnikov`, `Vocal Clarity Output Guard`.
- `DRUM BUS`: `ReaEQ`, `TDR Kotelnikov`, `FreeClip`.
- `808/BASS BUS`: `ReaEQ`, `ReaComp`, `FreeClip`; mono/phase safety before master.
- `MUSIC BUS`: `TDR Nova`, `Ozone Imager 2`; widen only after mono checks.
- `MIX BUS`: `Ozone 12 Equalizer` or `ReaEQ`, `TDR Kotelnikov`.
- `PREMASTER`: `Ozone 12 Equalizer` or `ReaEQ`, `TDR Kotelnikov`, `JS: Codex V20 Master Glue`, `FreeClip`, `ReaLimit`.
- `PRINT MASTER`: `mvMeter2`, `ClearMaster Audit`, `JS: Vocal Clarity Output Guard`.

If a chain uses two compressors, dynamic EQs, clippers, wideners, or saturators, document their separate roles in `work/traces/plugin_trace.json` or the pass report.

## Parameter Safety

- Do not hardcode UAD, TDR, or other external plugin parameters without calibration.
- Parameter writes for repo JSFX must be logged in `plugin_trace.json`.
- Cockos parameter writes require an explicit verified mapping.
- External plugins default to insert-only with no blind parameter writes.

## Repo JSFX

The available custom JSFX under `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/` are designed to be safe at defaults:

- `Codex Vocal AI Artifact Split Tamer`: conservative high fizz and unstable harshness reduction.
- `Vocal Clarity De-Mud Dynamic EQ`: low-mid attenuation with smoothed detector.
- `Vocal Clarity Presence Enhancer`: subtle presence tilt with output guard.
- `Vocal Clarity Air Guard`: high-air attenuation guard, not an air boost.
- `Vocal Clarity Output Guard`: final peak safety and gain trim.

The following requested JSFX names are policy-recognized but code is not present in this repo unless added later: `Codex Dynamic EQ Band`, `Codex Pro Dynamic MS EQ`, `Codex MS Melody Tuck`, `Codex Presence Tilt`, `Codex Noise Floor Tamer`, `Codex V20 Channel Polish`, `Codex V20 Master Glue`, `Codex Vocal Gate Expander`, `Codex Vocal Pitch Monitor`, `Codex Glitch Diffuse Spread`.
