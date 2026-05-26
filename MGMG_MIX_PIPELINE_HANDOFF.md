# MGMG Mix Pipeline Handoff

## Current Branch

`codex/mgmg-mix-pipeline-handoff`

This branch preserves the current MGMG mashup mixing/mastering work and adds a reproducible pipeline entrypoint for the next chat.

## New Chat Start

Paste this into a new Codex chat:

```text
Continue the MGMG mashup mix pipeline in /Users/hantaeheuk/Documents/New project 3.
First read MGMG_MIX_PIPELINE_HANDOFF.md, then inspect reports/final_balance_audit.md and reports/final_processing_settings.json.
Use tools/run_mgmg_current_pipeline.py to reproduce the current v13 render.
Do not overwrite source stems. Keep male lead centered, female layers/adlibs wide, and prioritize vocal/beat glue over -6 LUFS loudness.
```

## One Command Pipeline

Run:

```sh
python3 tools/run_mgmg_current_pipeline.py
```

This calls:

```sh
python3 tools/mgmg_v13_vocal_blended_stems_clear.py
```

It checks the required stem zip files, renders the current v13 balanced/loud masters, and prints the final metrics from `reports/render_audit_v13.csv`.

## Required Inputs

- `/Users/hantaeheuk/Downloads/ㅁㄱㅁㄱ x ㅁㄱㅁㄱ (Mashup) Stems.zip`
- `/Users/hantaeheuk/Downloads/ㅁㄱㅁㄱ x ㅁㄱㅁㄱ (Mashup) Stems (1).zip`
- Optional current preview zip used for audit comparison:
  `/Users/hantaeheuk/Documents/New project 3/output/mgmg_mashup_v12_vocals_down_clear_stems_lufs6_preview_320.mp3.zip`

## Current Outputs

- `output/mgmg_mashup_v13_vocal_blended_stems_clear_balanced_24-48.wav`
- `output/mgmg_mashup_v13_vocal_blended_stems_clear_loud_24-48.wav`
- `output/mgmg_mashup_v13_preview_320.mp3`
- `reports/final_balance_audit.md`
- `reports/final_processing_settings.json`

Latest measured targets:

- Balanced: about `-8.8 LUFS`, true peak `-1.0 dBTP`, LRA `2.4`
- Loud: about `-8.1 LUFS`, true peak `-1.0 dBTP`, LRA `2.3`

## Pipeline Shape

The current active pipeline is `tools/mgmg_v13_vocal_blended_stems_clear.py`.

Processing order:

1. Extract male-main stems and female/adlib stems.
2. Build male lead as mono center, then seat it with dynamic 800 Hz-9.2 kHz control and envelope-based level automation.
3. Build female/adlib layers with wide panning and reduced center presence.
4. Process drums, bass, keys, percussion, synth, and other stems with clarity EQ/saturation.
5. Apply instrumental M/S EQ:
   - MID 1-2.5 kHz slightly down.
   - MID 2.5-5.5 kHz down so vocal center stops popping forward.
   - SIDE 3.4 kHz, 6.8 kHz, and 9.8 kHz lifted for synth/FX/stem audibility.
6. Add short ambience, restrained plate, and phrase-only delay throws.
7. Apply master M/S tone control and render:
   - Balanced master around -9 to -8.5 LUFS.
   - Loud master around -8.3 to -7.8 LUFS.

## Version History

- `v08`: attempted -6 LUFS but had volume pumping.
- `v09`: fixed pumping but clipped/broke too much at -6 LUFS.
- `v10`: cleaner vocal/melody, lower loudness.
- `v11`: female vocal coverage increased to about 85%, wide M/S layers.
- `v12`: vocals reduced, stems clarified, pushed to -6 LUFS.
- `v13`: current best balance. Vocals are seated into the mix and master loudness is backed off to avoid vocal-only popout.

## Current Mix Rules

- Male lead stays center. Do not widen the lead vocal.
- Female vocal should stay as wide layer/adlib/backing support, not a second dry lead.
- If vocal sounds too large, do not only lower fader. First check:
  - center 1-5.5 kHz,
  - vocal-to-instrumental RMS,
  - short ambience level,
  - master clipper gain.
- Avoid -6 LUFS unless explicitly requested and accepted as a louder/rougher test. It tends to make the vocal center jump forward.
- Prefer balanced `-9` to `-8.5 LUFS` for the recommendation file.

## Quick QC

After rendering:

```sh
cat reports/render_audit_v13.csv
sed -n '1,220p' reports/final_balance_audit.md
```

Listen first to:

`output/mgmg_mashup_v13_preview_320.mp3`

Then compare:

- `output/mgmg_mashup_v13_vocal_blended_stems_clear_balanced_24-48.wav`
- `output/mgmg_mashup_v13_vocal_blended_stems_clear_loud_24-48.wav`

## Next Likely Revision Knobs

- Vocal still too forward:
  - Increase `vocal_auto_seat(... base_cut_db=2.2, peak_extra_db=1.2)` slightly.
  - Increase master MID dynamic cut in `master_ms_tone_v13`.
  - Lower `vocal_bus` gain before the final mix.
- Instruments too buried:
  - Raise `stem_gain_changes_db` for keys/synth/other.
  - Lift music SIDE 3-8 kHz more, but check mono.
- Female layer too small:
  - Raise `female_layers` bus, not the center shadow.
  - Keep `mseq_female_separation` center cut intact.
- Master too quiet:
  - Use the loud WAV first.
  - Raise `target_lufs` in `render_static_master` by small steps, not to -6 immediately.
