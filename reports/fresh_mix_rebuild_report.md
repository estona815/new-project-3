
# Fresh Mix Rebuild Report

## Why the previous output failed

- Treated here as over-processed, noisy, unstable, poorly balanced, and not reliable enough for commercial-release claims.
- Specific avoid-list: buried or unstable lead vocal, imprecise reverb/delay, weak M/S control, uncontrolled dynamic EQ, phasey width, crushed loudness, and old FX/master decisions.

## What was rebuilt from scratch

- New REAPER build script: `reaper/build_fresh_mix.lua`.
- New chain/notes script: `reaper/apply_fresh_mix_chains.lua`.
- New render setup: `reaper/render_fresh_mix.lua`.
- New save target: `reaper/FRESH_MIX_REBUILD.rpp`.
- Required fresh buses, send returns, QC markers, muted references, and muted quarantine routing are generated from zero.
- Guide MIDI tracks are created as muted placeholders with source-path metadata instead of auto-imported MIDI items, because REAPER can block on MIDI import option dialogs during command-line session creation.
- REAPER session creation was verified: `reaper/FRESH_MIX_REBUILD.rpp` saved successfully at 2026-05-24 17:04 KST.
- The original launch error was caused by an invalid `-reascript` CLI option plus REAPER MIDI import modal behavior; fixed by passing Lua as a direct script argument through a `/tmp` wrapper and by skipping automatic MIDI item import.
- Imported audio/reference items are aligned at 0.0 seconds.

## Production stems

[
  "0 Lead Vocals.wav",
  "01_Woodwinds.wav",
  "02_Brass.wav",
  "04_Synth.wav",
  "05_Strings.wav",
  "06_Percussion.wav",
  "07_Keyboard.wav",
  "09_Bass.wav",
  "10_Drums.wav",
  "11_Backing_Vocals.wav",
  "12_Vocals.wav",
  "female_vocal_candidate_clean.wav"
]

## References only

[
  "1 Instrumental.wav",
  "00_REF_Full_Mix.wav",
  "동반자살 WAV.wav",
  "hangang_shadow_mashup_v21_clear_male_blended_female_MASTER_320k.mp3.zip",
  "hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_24-48.wav",
  "hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_320k.mp3",
  "hangang_shadow_mashup_v19_polished_balance_melody_vocal_MASTER_320k Stems.zip"
]

## Quarantined artifacts

[
  "03_FX.wav",
  "08_Guitar.wav"
]

## Vocal and mix strategy

- Male lead: centered, dominant, pitch correction before dynamic EQ, de-essing, serial compression, tone EQ, light saturation only if clean.
- Female BGV: support only, quiet and wide, lower than male lead.
- Dynamic EQ: mud, sibilance, harshness, and 1-5 kHz masking are handled dynamically instead of with dull static cuts.
- Reverb/delay: send-based, tempo-aware, filtered, and ducked where possible.
- M/S space: low end centered, side low-mids reduced, width limited to synth/BGV ranges that remain mono-compatible.
- Mix/master: premaster first, conservative master second, true peak ceiling -1.0 dBTP, no extreme limiting.

## Known limitations

- Plugin inventory is detection/placeholder/fallback guidance only until verified in REAPER.
- The fresh auto-build script inserts stock-safe fallback FX to avoid premium plugin license/modal stalls; detected premium plugins remain manual upgrade candidates.
- Guide MIDI should be imported manually inside REAPER only after the session opens if you need piano-roll inspection.
- No premaster/master render is claimed yet; rendering before human tuning/balance review would be a fake production result.
- Automated QC is not a substitute for human listening to vocal pitch, phrase endings, emotional timing, or commercial polish.
- Any severe AI vocal artifact that remains audible requires regeneration or manual re-recording.
