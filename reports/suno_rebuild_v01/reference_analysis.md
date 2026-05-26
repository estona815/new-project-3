# Reference Analysis

The Suno material is used only as production reference and analysis context. It is not used as an active final mix source.

## Core Detection

- Reference: `/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/00_REF_Full_Mix.wav`
- Song length: `141.394 s`
- BPM: `162.0` from guide MIDI tempo metadata
- Bar estimate: `95.44` bars at detected BPM
- Key / scale: `B minor`; pitch-class guide confidence `guide_midi_pitch_class_profile`

## Arrangement Map

| section | bars | start | end | energy | full RMS | drums RMS | bass RMS | synth RMS |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| intro / filtered melody sketch | 1-8 | 0.0s | 11.85s | low | -20.55 | -29.66 | -36.92 | -25.09 |
| verse 1 / drums enter light | 9-24 | 11.85s | 35.56s | medium | -19.58 | -24.59 | -29.04 | -30.19 |
| hook 1 / full melody-forward lift | 25-40 | 35.56s | 59.26s | high | -17.79 | -22.15 | -25.3 | -32.79 |
| verse 2 / tighter groove variation | 41-56 | 59.26s | 82.96s | medium-high | -18.67 | -23.97 | -29.39 | -32.01 |
| bridge / half-drop and space | 57-64 | 82.96s | 94.81s | low-medium | -17.28 | -21.27 | -23.48 | -38.29 |
| hook 2 / full rebuild return | 65-80 | 94.81s | 118.52s | high | -18.15 | -24.09 | -27.1 | -31.96 |
| final lift / densest drums and counter melody | 81-88 | 118.52s | 130.37s | highest | -15.36 | -18.79 | -20.86 | -31.97 |
| outro / melody decay | 89-96 | 130.37s | 141.39s | low | -15.54 | -19.36 | -22.02 | -24.74 |

## Musical Structure Notes

- Main melody energy is present from the intro, becomes a clear forward hook function around bars 25-40, returns at bars 65-88, then decays in the outro.
- Drum guide density is closed-hat heavy with half-time snare/clap behavior and kick variation; the rebuild preserves the energy curve but changes the actual hits and timing.
- Bass/808 guide emphasizes B minor-related tones with frequent F# and B/D support; the rebuild keeps B natural minor and writes a new Bm-G-D-A movement.
- Major energy changes are treated at bars 9, 25, 41, 57, 65, 81, and 89.

## Guide MIDI Density

- `drums`: `1361` notes, last active bar `95.22`, average `14.18` notes per active bar, top notes `[{'midi': 42, 'count': 782}, {'midi': 36, 'count': 292}, {'midi': 38, 'count': 287}]`
- `bass_808`: `152` notes, last active bar `94.69`, average `2.81` notes per active bar, top notes `[{'midi': 30, 'count': 34}, {'midi': 35, 'count': 18}, {'midi': 26, 'count': 18}, {'midi': 28, 'count': 13}, {'midi': 37, 'count': 12}, {'midi': 42, 'count': 12}, {'midi': 25, 'count': 8}, {'midi': 38, 'count': 8}]`
- `melody_synth`: `284` notes, last active bar `94.0`, average `3.94` notes per active bar, top notes `[{'midi': 95, 'count': 51}, {'midi': 50, 'count': 20}, {'midi': 49, 'count': 19}, {'midi': 45, 'count': 17}, {'midi': 40, 'count': 16}, {'midi': 42, 'count': 15}, {'midi': 47, 'count': 14}, {'midi': 73, 'count': 13}]`
- `fx`: `1643` notes, last active bar `95.09`, average `17.11` notes per active bar, top notes `[{'midi': 82, 'count': 1585}, {'midi': 39, 'count': 58}]`

## Stem Separation Status

- Pre-separated Suno Studio stems were found and used for analysis-only reference: drums, bass, synth, FX, vocals, and related instrument stems.
- No separated Suno stem is routed into the active production mix.
- No new network install or paid separation dependency was used.

## Reference Metrics

| metric | value |
| --- | ---: |
| sample_rate | 48000 |
| channels | 2 |
| duration_s | 141.394 |
| peak_dbfs | -4.61 |
| approx_true_peak_dbfs | -4.604 |
| rms_dbfs | -17.853 |
| approx_lufs_i | -19.831 |
| stereo_correlation | 0.9407 |
| 20_60_hz_db_share | -5.94 |
| 60_120_hz_db_share | -5.63 |
| 120_350_hz_db_share | -6.99 |
| 1k_5k_db_share | -10.33 |
| 5k_8k_db_share | -25.44 |
| 8k_20k_db_share | -24.04 |
