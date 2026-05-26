# 0101 Raw Clip-Safe v01 Report

- Source folder: `/Users/hantaeheuk/Documents/New project 3/audio_work/0101_suno_studio_v04_real_female_audible_vocal_ride/stems`
- Final WAV: `/Users/hantaeheuk/Documents/New project 3/renders/0101_raw_clip_safe_v01/0101_RAW_CLIP_SAFE_v01.wav`
- Preview WAV: `/Users/hantaeheuk/Documents/New project 3/renders/0101_raw_clip_safe_v01/0101_RAW_CLIP_SAFE_v01_preview_30s.wav`
- Source metrics CSV: `/Users/hantaeheuk/Documents/New project 3/reports/0101_raw_clip_safe_v01/source_stem_metrics.csv`
- Pre-mix sample peak before final gain: -1.22 dBFS
- Pre-mix true peak before final gain: -1.22 dBFS
- Final gain applied: 0.02 dB
- Final sample peak: -1.21 dBFS
- Final true peak 4x: -1.20 dBFS
- Final approximate integrated loudness: -15.29 LUFS
- Final clipped samples >= 0.999: 0

## Included Stems

- `0101_backing_vocals_raw.wav` at -5.8 dB
- `0101_bass808_raw.wav` at -0.9 dB
- `0101_drums_raw.wav` at -1.8 dB
- `0101_fx_raw.wav` at -5.5 dB
- `0101_keyboard_raw.wav` at -2.8 dB
- `0101_melody_raw.wav` at -2.2 dB
- `0101_synth_raw.wav` at -3.2 dB
- `0101_vocal_raw.wav` at +1.2 dB

## Analyzed But Not Mixed

- `0101_brass_raw.wav`: near-silent separated stem, analyzed but muted
- `0101_guitar_raw.wav`: near-silent separated stem, analyzed but muted
- `0101_instrumental_raw.wav`: reference/composite, analyzed but not mixed
- `0101_original_reference.wav`: reference/composite, analyzed but not mixed
- `0101_original_reference_duplicate.wav`: reference/composite, analyzed but not mixed
- `0101_percussion_raw.wav`: near-silent separated stem, analyzed but muted
- `0101_strings_raw.wav`: near-silent separated stem, analyzed but muted
- `0101_woodwinds_raw.wav`: near-silent separated stem, analyzed but muted

## Processing Notes

- Clip-safe rebuild from raw stems; no hard clipper, no aggressive maximizer.
- Vocal kept close/raw: HPF near 80 Hz, tiny mud/plastic/harshness cleanup, light 5.5-12 kHz de-ess/fizz reduction.
- Drums/bass kept transient/sub-forward with only minimal cleanup.
- The final file is intentionally less crushed than clipped versions, so it should hold up better without crackle/breakup.

## Remaining Check

- Human A/B check is still needed for AI vowel-tail artifacts and vocal emotion.
