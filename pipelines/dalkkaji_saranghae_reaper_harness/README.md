# Dalkkaji Saranghae REAPER Harness

This harness reproduces the Suno vocal repair / female support-layer / REAPER mix-master pipeline used for `달까지 사랑해`.

It is designed for user-owned Suno multitrack exports. Large audio sources, processed stems, renders, and handoff ZIPs are intentionally not committed.

## Goals

- Preserve the main male vocal as lead.
- Treat female Suno takes as `LOW_LAYER_ONLY` unless they pass timing, pitch, and bleed checks.
- Use short masked female phrase endings, M/S separation, pan-delay, and endpoint reverb throws.
- Improve kick/808 texture with light saturation and soft clipping.
- Carve the instrumental with dynamic EQ-style processing so the vocal and main melody both read.
- Build a REAPER project with local/free plugin equivalents for the paid reference chain.

## Expected Source Folder

The default source folder is:

```text
/Users/hantaeheuk/Downloads/달까지 사랑해
```

Expected filenames:

```text
0 달까지 사랑해.wav
1 Woodwinds.wav
2 Brass.wav
3 FX.wav
4 Synth.wav
5 Strings.wav
6 Percussion.wav
7 Keyboard.wav
8 Guitar.wav
9 Bass.wav
10 Drums.wav
11 Backing_Vocals.wav
12 Vocals.wav
13 여자목소리1.wav
14 달까지 사랑해 (Vocals) (Add Instrumental).wav
15 달까지 사랑해 (Vocals) (Add Instrumental).wav
16 달까지 사랑해 (Vocals) (Add Instrumental).wav
```

## Run

```sh
pipelines/dalkkaji_saranghae_reaper_harness/run_pipeline.sh
```

Optional overrides:

```sh
DALKK_SOURCE_DIR="/path/to/suno_multitrack" \
DALKK_SLUG="my_song_v01_repair_mix" \
pipelines/dalkkaji_saranghae_reaper_harness/run_pipeline.sh
```

## Outputs

The script writes versioned folders under:

```text
audio_work/<slug>/
reaper/<slug>/
renders/<slug>/
reports/<slug>/
```

Final files:

```text
renders/<slug>/FINAL_dalkkaji_saranghae_max_chain_24bit.wav
renders/<slug>/FINAL_dalkkaji_saranghae_max_chain_320k.mp3
reaper/<slug>/FEMALE_TAKE_REPAIR_AND_DOUBLE_COMP_V01.rpp
reports/<slug>/female_layer_repair_comp_qc_report.md
```

## Safety Rules

- No Antares / Auto-Tune / login-required paid plugin chain.
- No full-take female lead takeover.
- No forced long phrase stretching.
- No random `ahh/ooh/yeah/hello` adlibs.
- No heavy denoise to hide bad source quality.
- Reference/full-mix material stays for checking, not as active premaster glue.
