# Final Balance Audit

## Diagnosis

- The v12 preview was pushed to about -6 LUFS, which made center vocal midrange dominate the mix.
- The fix uses stems, not master-only processing: vocal presence is dynamically seated, instrumental side detail is lifted, and the master limiter/clipper is backed off.
- The target is balance first: balanced version around -9 to -8.5 LUFS and loud version around -8.3 to -7.8 LUFS.

## Current v12 Preview

- Integrated LUFS: -6.0
- True peak: -0.4 dBTP
- LRA: 2.1 LU
- Short-term median/max: -5.9 / -4.4 LUFS
- Side/Mid: -17.84 dB

## Output Metrics

| label | LUFS | TP | LRA | corr | side_mid |
| --- | --- | --- | --- | --- | --- |
| v13_balanced | -8.8 | -1.0 | 2.4 | 0.9754 | -19.05 |
| v13_loud | -8.1 | -1.0 | 2.3 | 0.9747 | -18.92 |
| v13_preview_mp3 | -8.8 | -0.9 | 2.4 | 0.9753 | -19.03 |

## Bus Balance

| bus | RMS dBFS | peak dBFS | side/mid dB |
| --- | --- | --- | --- |
| music_bus | -12.89 | 18.39 | -22.99 |
| vocal_bus | -19.18 | 6.28 | -19.87 |
| fx_bus | -34.2 | -17.05 | 0.31 |

## Main Moves

- Vocal-to-instrumental RMS ratio after balancing: -6.3 dB.
- Lead vocal was reduced with static gain plus envelope automation: base cut about 2.2 dB, loud phrase extra cut about 1.2 dB.
- Female/adlib layer was reduced further and moved more to side energy with center presence cut.
- Music M/S EQ: MID 1-2.5 kHz -0.45 dB, MID 2.5-5.5 kHz -0.75 dB, SIDE 3.4 kHz +1.15 dB, SIDE 6.8 kHz +0.85 dB, SIDE 9.8 kHz shelf +0.55 dB.
- Master M/S EQ: MID 1-5.5 kHz dynamic control, SIDE 4.2 kHz/9.5 kHz lift, low end kept mono below about 120 Hz.
- Limiter/clipper was reduced versus v12: v12 used target -6 LUFS; v13 balanced/loud use gains 23.75 dB and 24.2 dB with lighter drive.

- Phrase events used: 22
- Female layer coverage ratio: 0.854
