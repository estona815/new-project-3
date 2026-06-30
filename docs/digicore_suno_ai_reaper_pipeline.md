# Digicore / Suno AI REAPER Pipeline

This is the current operating guide for Suno/AI artifact reduction while
preserving intentional digicore, hip-hop, and hyperpop texture. It is not an AI
detector-evasion workflow. Do not claim listening results, reference matching,
or a finished master without measured evidence and user A/B review.

## 1. Routing Template

| Bus | Purpose | Inputs | Output | Recommended FX Chain |
| --- | --- | --- | --- | --- |
| `REF BUS` | Muted reference/meter lane only | `SOURCE full mix reference muted - not in master` | none by default | `mvMeter2` -> `ClearMaster Audit` |
| `VOX BUS` | All lead, doubles, adlibs, vocal FX | lead vocal, hook residual, low-mid support, side vocals, throws | `MIX BUS` | `TDR Nova` -> `TDR Kotelnikov` -> `Vocal Clarity Output Guard` |
| `DRUM BUS` | Kick/snare/hat/percussion control | drum stems | `MIX BUS` | `ReaEQ` -> `TDR Kotelnikov` -> `FreeClip` |
| `808/BASS BUS` | Mono low-end and 808/kick relationship | bass, 808, sub | `MIX BUS` | `ReaEQ` -> `ReaComp` -> `FreeClip` |
| `MUSIC BUS` | Synth, keys, guitar, FX bed | non-vocal/non-drum music stems | `MIX BUS` | `TDR Nova` -> `Ozone Imager 2` |
| `MIX BUS` | Balance trim before mastering | `VOX BUS`, `DRUM BUS`, `808/BASS BUS`, `MUSIC BUS` | `PREMASTER` | `Ozone 12 Equalizer` or `ReaEQ` -> `TDR Kotelnikov` |
| `PREMASTER` | Master processing lane | `MIX BUS` | `PRINT MASTER` | `Ozone 12 Equalizer` or `ReaEQ` -> `TDR Kotelnikov` -> `Codex V20 Master Glue` -> `FreeClip` -> `ReaLimit` |
| `PRINT MASTER` | Final print, output guard, metering | `PREMASTER` | REAPER master/hardware | `mvMeter2` -> `ClearMaster Audit` -> `Vocal Clarity Output Guard` |

The reference/full mix track must stay muted, master-send disabled, and out of
all active buses. A send to `REF BUS` is allowed only because `REF BUS` is also
muted and master-send disabled by default.

## 2. Digicore Vocal Chain Presets

### Lead Vox

Order:

1. `JS: Codex Vocal AI Artifact Split Tamer`
2. `JS: Vocal Clarity De-Mud Dynamic EQ`
3. `ReaEQ` or `Ozone 12 Equalizer`
4. `TDR Nova`
5. `JS: De-esser`
6. `JS: Vocal Clarity Air Guard`
7. `UADx LA-2A`
8. `UADx 1176`
9. `JS: Vocal Clarity Output Guard`

Starting ranges: high-pass 60-100 Hz, de-mud 150-350 Hz with 0.5-2 dB dynamic
reduction, sibilance 5-10 kHz with 1-4 dB reduction, LA-2A/1176 combined gain
reduction normally below 5 dB. Keep the first FX slot exact.

A/B: loudness-match the raw or previous accepted vocal against the processed
lead. Accept only if intelligibility improves without dulling consonants,
flattening formants, or making the vocal less emotional.

Forbidden by default: pitch correction, Decapitator, BYOD, Krush, heavy OTT, or
Fresh Air on clean-main-vocal rescue unless the user re-authorizes stylized
processing.

### Lead Vox Parallel Crush

Order: duplicate/parallel send -> `ReaEQ` band-limit -> `OTT` or `ReaXcomp` ->
`Decapitator` or `IVGI2` -> `FreeClip` -> `ReaEQ`.

Starting ranges: blend -18 to -10 dB under lead, high-pass 120-250 Hz,
low-pass 7-12 kHz, compression obvious but tucked. This lane preserves the
blown-out digicore vocal energy without damaging the clean lead.

A/B: bypass the parallel lane only. The lead should lose density/attitude but
not collapse in clarity.

Forbidden: do not use parallel crush as a replacement for de-essing, artifact
cleanup, or level riding.

### Doubles / Adlibs

Order: `Codex Vocal AI Artifact Split Tamer` -> `ReaEQ` -> `TDR Nova` ->
`Vocal Doubler` or pan/delay -> `ReaDelay` send -> `ReaVerbate`/Valhalla send.

Starting ranges: -5 to -12 dB below lead, high-pass 120-180 Hz, dynamic dip
around 2-5 kHz when lead is present, side width only after mono check.

A/B: mute doubles/adlibs. The lead should remain fully readable; the layer
should add size, emotion, or hook lift only.

Forbidden: do not let side vocals become the lead by accident; mute off-time or
off-pitch regions rather than forcing them.

### Vox FX Return

Order: `ReaDelay` or ValhallaSupermassive -> `ReaEQ` -> `TDR Nova` ->
ducking/sidechain if available -> output guard.

Starting ranges: send -24 to -12 dB, high-pass 180-300 Hz, low-pass 6-10 kHz,
duck 1-4 dB against lead vocal.

A/B: FX should disappear from the center while the vocal line is active and
appear at line ends or transitions.

Forbidden: do not let reverb/delay tails mask the next lyric or trigger master
compression.

## 3. Suno / AI Artifact Cleanup Cookbook

| Problem | Detection | Tools | Starting Range | Failure Signs |
| --- | --- | --- | --- | --- |
| metallic high-end hiss | 8-16 kHz band share, side hash, spectrum glare | Artifact Split Tamer, TDR Nova, Air Guard, ReaEQ | 0.5-2.5 dB dynamic reduction, Air Guard mix 0.20-0.45 | dull consonants, missing air, hats vanish |
| harsh sibilance | 5-10 kHz S/T/SH bursts | TDR Nova, JS De-esser, ReaXcomp, item gain | 1-4 dB GR, release 40-160 ms | lisping, vowel pumping |
| vocal warble | unstable pitch/formant trace, watery note tails | Artifact Split Tamer, De-Mud, TDR Nova | Amount 20-45, Mask 0.25-0.45, Max Reduction 4-8 dB | flattened formants, robotic tone |
| smeared hats/cymbals | blurred 6-12 kHz transients, mono top collapse | TDR Nova, ReaEQ, ReaXcomp | 0.5-2 dB dynamic trim, reduce width before boost | hats lose groove, snare dulls |
| fake stereo/mono collapse | correlation below 0.25, side dominates mid | Ozone Imager 2, pan/routing, M/S EQ | mono low end below 120 Hz, side artifact band -2 to -4 dB | hook gets smaller in mono |
| over-compressed pumping | sustained bus/master GR >2 dB, low-end dips | reduce bus input, Kotelnikov, FreeClip, ReaLimit | bus GR 0.5-2 dB, limiter catches peaks only | vocal ducks on kick, 808 pulls mix down |

## 4. Master Chain

Use this chain for both master profiles:

`Ozone 12 Equalizer` or `ReaEQ` -> `TDR Kotelnikov` -> `JS: Codex V20 Master Glue` -> `FreeClip` -> `ReaLimit` -> `mvMeter2`/`ClearMaster Audit`/`Output Guard`.

Loud reference master: target -9.5 to -8.0 LUFS-I, true peak <= -1.0 dBTP.
Use this for loud review/reference comparison only when the mix bus is stable.

Safer streaming master: target -14.5 to -12.5 LUFS-I, true peak <= -1.0 dBTP.
Use this as the default shareable copy.

If the master chain sustains more than 2 dB of gain reduction, stop and return
to vocal, 808/bass, drum, or music-bus balance. Do not solve buried vocals or
harsh hats by pushing the master harder.

## 5. JSFX Audit

| JSFX | Code Status | Smoothing | Zipper/Click Risk | Delta Monitor | Oversampling | Mono Impact | Gain Comp / Guard | Action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Codex Vocal AI Artifact Split Tamer | present | attack/release and band smoothing present | low if sliders are moved moderately | residual monitor present | not present; acceptable for attenuation-first design | M/S path guarded | output trim, dry fallback, collapse guard | keep first on lead |
| Vocal Clarity De-Mud Dynamic EQ | present | patched detector/gain smoothing | low | residual mode added | not needed | linked stereo | no makeup boost, ceiling guard | use after Artifact Split Tamer |
| Vocal Clarity Presence Enhancer | present | patched gain smoothing | low | residual mode added | not needed | linked stereo | output ceiling guard | use sparingly |
| Vocal Clarity Air Guard | present | patched detector/gain smoothing | low | residual mode added | not needed | linked stereo | attenuation-only guard | use for fizz/air risk |
| Vocal Clarity Output Guard | present | patched trim smoothing | low | not needed | not needed | linked stereo | ceiling limiter | final insert/print guard |
| Codex Dynamic EQ Band | missing | unknown | unknown | needed | not until nonlinear | unknown | needed | log missing |
| Codex Pro Dynamic MS EQ | missing | unknown | unknown | needed | not until nonlinear | high risk; needs mono tests | needed | log missing |
| Codex MS Melody Tuck | missing | unknown | unknown | needed | no | high risk; M/S sidechain | needed | log missing |
| Codex Presence Tilt | missing | unknown | unknown | useful | no | linked stereo required | guard required | log missing |
| Codex Noise Floor Tamer | missing | unknown | gate chatter risk | useful | no | linked stereo required | no makeup boost | log missing |
| Codex V20 Channel Polish | missing | unknown | unknown | useful | if saturation | unknown | required | log missing |
| Codex V20 Master Glue | missing | unknown | unknown | useful | if nonlinear | must pass mono | required | log missing |
| Codex Vocal Gate Expander | missing | unknown | high if unsmoothed | useful | no | linked stereo | guard required | log missing |
| Codex Vocal Pitch Monitor | missing | monitor only | low | not applicable | no | none | not applicable | log missing |
| Codex Glitch Diffuse Spread | missing | unknown | click risk | useful | if nonlinear | high risk | guard required | log missing |

## 6. ReaScript Automation Skeletons

REAPER Lua scripts currently live under `automix/`:

- `automix/scan_reaper_plugin_inventory.lua`
- `automix/apply_conservative_pitch_draft.lua`
- `automix/apply_vocal_recovery_draft.lua`
- `automix/apply_vocal_placement_draft.lua`
- `automix/apply_premaster_draft.lua`
- `automix/reaper_scripts/collect_plugin_semantic_validation_runtime.lua`

They are dry, conservative starting points. Test on a saved project copy before
real sessions, verify the Routing Matrix after every routing script, and do not
grant external plugin parameter-write safety without runtime validation reports.

## 7. Reference Analysis Script

Use `tools/analyze_reference_features.py` for user-owned audio only:

```sh
python3 tools/analyze_reference_features.py input/reference/reference.wav --output reports/reference_analysis.csv
```

It reports LUFS-I when `pyloudnorm` is available, sample peak, spectral
centroid, spectral rolloff, low/mid/high energy ratio, and stereo correlation.
It does not fabricate values when the file is missing or dependencies fail.

For the Goal 02 20-second chorus pass, use the stricter eight-reference entry:

```sh
python3 tools/analyze_goal02_reference_match.py \
  --manifest configs/goal02_8_reference_manifest.json \
  --output-dir reports/goal02_8_reference_match
```

This writes a target-plus-eight-reference CSV, JSON summary, and Markdown
report. Fewer than eight measured references or a missing target produces an
explicit `blocked_missing_inputs` result rather than a guessed reference match.

For a deterministic non-final transfer sketch, render the Goal 02 Python DSP
preview package:

```sh
python3 tools/render_goal02_chorus_candidate.py \
  --manifest configs/goal02_8_reference_manifest.json \
  --analysis reports/goal02_8_reference_match/goal02_reference_match.json \
  --render-dir renders/goal02_chorus_v01 \
  --report-dir reports/goal02_chorus_v01
```

This creates current/candidate/reference A/B WAVs plus CSV/JSON/Markdown QC.
It is useful for deciding REAPER moves, but it is not a plugin runtime trace,
not a final master, and not proof that the lead vocal first-slot JSFX gate has
passed.

To create the actual REAPER 20-second runtime project, render, plugin trace,
safe streaming review candidate, loud reference review candidate, and
primary-reference A/B package:

```sh
python3 tools/render_goal02_chorus_reaper.py
```

Then validate the main-vocal first-slot gate:

```sh
python3 tools/validate_reaper_vocal_chain_gate.py \
  --trace reports/goal02_chorus_reaper_v01/actual_reaper_plugin_trace.json \
  --main-track '08 MALE_NONHOOK_CENTER'
```

Then collect FFmpeg LUFS-I/true-peak evidence and build corrected target files
when needed:

```sh
python3 tools/analyze_goal02_runtime_loudness.py
python3 tools/build_goal02_lufs_target_package.py
```

## REAPER Application Order

1. Run `tools/build_asset_manifest.py`.
2. Run `tools/install_reaper_jsfx.py` in dry-run, then apply only if paths are
   correct.
3. Create/verify routing: `REF BUS`, `VOX BUS`, `DRUM BUS`, `808/BASS BUS`,
   `MUSIC BUS`, `MIX BUS`, `PREMASTER`, `PRINT MASTER`.
4. Run Goal 02 reference analysis if doing the 20-second chorus match pass.
5. Optionally render the Goal 02 Python DSP preview to narrow the REAPER moves.
6. Insert lead-vocal first-slot Artifact Split Tamer and write
   `work/traces/plugin_trace.json`.
7. For Goal 02, run the actual REAPER runtime pass and validate
   `actual_reaper_plugin_trace.json`.
8. Measure LUFS/true peak and build the corrected LUFS target package.
9. Fix vocal, 808/bass, and drums before touching master loudness.
10. Render actual REAPER loudness-matched A/B review copies.
11. Render loud and safe masters only after QC gates are explicit pass/fail.
12. Deliver only when renders, QC, traces, reports, and package exist.
