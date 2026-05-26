# REAPER Mix/Master Plan

Automation-friendly only: REAPER stock FX, JSFX, SWS/ReaPack utilities, and Python QC. No Antares. No reference audio should be mixed into the active premaster bus.

## Vocal Chain
- If `vocal_stem.wav` exists: ReaEQ high-pass around 70-100 Hz, body shaping around 150-500 Hz, dynamic ReaXcomp control around 2-8 kHz, light ReaComp leveling, short room/early reflection send for glue, optional ESTONA anti-harsh JSFX.
- If no vocal stem exists: do not guess vocal tuning changes from the full mix. Use full-mix high-mid repair conservatively.

## Instrumental Bus Chain
- ReaEQ low-end cleanup: control 120-350 Hz mud without thinning 808.
- JSFX/stock saturation or soft clipper for beat density if transients feel too flat or too clean.
- Mono sub guard below 100-120 Hz; keep wide material mostly above the bass range.

## Mix Bus Chain
- ReaXcomp: gentle 2-5 kHz and 5-8 kHz dynamic control if current mix exceeds reference harshness target.
- Gentle glue compression only if vocal/instrument feels detached; avoid pumping.
- Soft clipper before limiter for controlled digicore density.

## Master Chain
- ReaEQ corrective tone only.
- ReaComp or ReaXcomp for tiny broadband control.
- ReaLimit with ceiling around -1.0 dBFS and MP3 safety check.
- Reference target loudness direction: median -6.04 LUFS, IQR -6.11 to -6.03 LUFS. Do not chase unsafe clipping.

## Optional AI High-End Repair Chain
- ReaXcomp band 5-8 kHz: fast-ish attack, medium release, 1-3 dB dynamic reduction.
- ReaEQ narrow cuts only where harsh resonances are measured.
- De-ess style control around 6-9 kHz if vocal stem exists.
- Avoid bright exciters until high-end hash score is under control.

## Missing Inputs To Complete Automation
- `/Users/hantaeheuk/Documents/New project 3/00_AUDIO_INPUT`
- `/Users/hantaeheuk/Documents/New project 3/00_AUDIO_INPUT/current_mix.wav`
- `/Users/hantaeheuk/Documents/New project 3/00_AUDIO_INPUT/vocal_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/00_AUDIO_INPUT/instrumental_stem.wav`
- `/Users/hantaeheuk/Documents/New project 3/00_AUDIO_INPUT/reference_01.wav`
- `/Users/hantaeheuk/Documents/New project 3/00_AUDIO_INPUT/reference_02.wav`
- `/Users/hantaeheuk/Documents/New project 3/00_AUDIO_INPUT/reference_03.wav`

## Vocal/Instrument Relationship
vocal_stem.wav and instrumental_stem.wav were not both found.
