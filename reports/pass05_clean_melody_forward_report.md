# Pass 05 Clean Melody-Forward Report

Generated: 2026-05-24T18:57:45

## User Direction
- Mix/master in REAPER.
- Follow the technical reference as a broad mix compass only.
- Reduce noisy ambience/fizz and make the main melody easier to hear.

## Executed
- Started from PASS04 and saved a separate PASS05 REAPER project.
- Kept reference, quarantine, guide MIDI, and short Suno candidate stems muted.
- Lowered BGV, general FX, vocal plate, delay, short room, and constant delay bed.
- Raised synth/keyboard melody and added a subtle REAPER JSFX presence tilt.
- Added custom REAPER JSFX high-band noise-floor tamers on vocal, FX, and music buses.
- Used dynamic cut bands for low-mid bloom, high fizz, BGV sibilance, and limiter edge.
- MP3 export was skipped because this REAPER install exposes WAV/AIFF/CAF render sinks only; a 320k AAC M4A preview is provided instead.

## Metrics

| File | Exists | Peak dBFS | Approx LUFS-I | Approx LRA | Clips | Corr |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| pass03_master | True | -1.0 | -5.64 | 3.32 | 0 | 0.99 |
| pass04_master | True | -1.0 | -6.49 | 4.37 | 0 | 0.99 |
| pass05_premaster | True | -12.74 | -26.52 | 3.96 | 0 | 0.991 |
| pass05_master | True | -1.0 | -6.66 | 3.82 | 0 | 0.991 |
| technical_reference | True | -0.1 | -6.11 | 1.59 | 0 | 0.938 |

## Tonal / Noise Proxy

| File | sub_20_120_db | mud_120_350_db | melody_presence_1k5_4k5_db | sibilance_5k5_9k_db | hiss_air_9k_14k_db | side_150_400_db |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| pass03_master | -12.5 | -15.26 | -18.23 | -30.89 | -32.21 | -38.51 |
| pass04_master | -12.19 | -15.9 | -19.56 | -32.11 | -33.54 | -38.81 |
| pass05_master | -13.18 | -16.59 | -19.52 | -33.17 | -34.59 | -40.02 |
| technical_reference | -10.53 | -14.96 | -19.66 | -26.51 | -28.65 | -28.11 |

## Interpretation
- PASS05 master exists: True.
- PASS05 approximate loudness: -6.66 LUFS-I proxy, peak -1.0 dBFS, clips 0.
- Quiet-window 9-14 kHz hiss proxy delta vs PASS04: -0.82 dB. Negative means less high-band noise by this heuristic.
- This is measured QC, not a substitute for listening in REAPER for vocal artifacts, pumping, or taste.

## Important Track Levels

| Track | Volume dB | Pan | Muted |
| --- | ---: | ---: | --- |
| 12_Vocals | -6.4 | 0.0 | False |
| MALE_LEAD_VOX_BUS | -0.2 | 0.0 | False |
| MUSIC_BUS | 2.2 | 0.0 | False |
| 04_Synth | -9.8 | 0.0 | False |
| 07_Keyboard | -10.5 | 0.0 | False |
| DRUM_BUS | -0.6 | 0.0 | False |
| BASS_808_BUS | -1.3 | 0.0 | False |
| FEMALE_BGV_BUS | -11.5 | 0.0 | False |
| VOCAL_FX_BUS | -11.5 | 0.0 | False |
| FX_BUS | -10.0 | 0.0 | False |
| SUNO_000000_CANDIDATE_BUS | -18.0 | 0.0 | True |

## Validation
PASS
- PASS05 render safety mute checks passed.
