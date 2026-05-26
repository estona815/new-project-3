# Vocal Artifact Analysis

Source analyzed: `12 Vocals.wav` as the natural male lead. The original full mix stayed muted/reference-only in the REAPER session.

## Detected Artifacts

- Raw vocal sibilance share: 5.106% vs processed vocal stem 2.651%.
- Raw vocal air/hash share: 1.453% vs processed vocal stem 1.011%.
- Most fixable: sandy sibilance, harsh attack bursts, low-mid buildup, and exposed high fizz in gaps.
- Reducible only: unstable formant/vowel-tail texture and some baked-in AI warble, because fully removing it would damage melody and phrasing.

## Severity Ranking

1. Sandy/metallic sibilance around 5.5-8 kHz: high.
2. Digital fizz around 8-12 kHz: medium-high.
3. Harsh AI consonant/attack energy around 2.5-5 kHz: medium.
4. Mud/body buildup around 180-350 Hz: medium.
5. Plastic/nasal formant buildup around 700 Hz-1.2 kHz: medium.
6. Vowel-tail warble: medium, best hidden by blend and ambience rather than surgical removal.

### Low-Mid Mud

- Suspected range: 180-350 Hz

| timestamp | severity | measured cue |
| --- | --- | ---: |
| 0:13.27 | high | -0.33 |
| 0:20.50 | high | -0.7 |
| 0:30.49 | high | -0.33 |
| 0:35.16 | high | -0.23 |
| 1:01.06 | high | -0.61 |
| 1:14.22 | high | -0.62 |
| 1:58.12 | high | -0.44 |
| 2:02.75 | high | -0.66 |

### Plastic/Nasal Tone

- Suspected range: 700 Hz-1.2 kHz

| timestamp | severity | measured cue |
| --- | --- | ---: |
| 0:27.07 | high | -0.48 |
| 0:45.76 | high | -0.66 |
| 1:02.59 | high | -0.65 |
| 1:16.97 | high | -0.53 |
| 1:20.15 | high | -0.53 |
| 1:52.90 | high | -0.48 |
| 2:05.21 | high | -0.57 |
| 2:08.04 | high | -0.35 |

### Harsh AI Attack

- Suspected range: 2.5-5 kHz

| timestamp | severity | measured cue |
| --- | --- | ---: |
| 0:05.74 | high | -0.65 |
| 0:07.77 | high | -0.77 |
| 0:41.07 | high | -0.99 |
| 1:28.51 | high | -0.7 |
| 1:40.20 | high | -1.04 |
| 1:47.11 | high | -1.0 |
| 1:51.06 | high | -0.87 |
| 2:03.01 | high | -0.81 |

### Sandy Sibilance

- Suspected range: 5.5-8 kHz

| timestamp | severity | measured cue |
| --- | --- | ---: |
| 0:09.75 | high | 8.74 |
| 0:19.20 | high | 8.51 |
| 0:22.19 | high | 5.93 |
| 0:42.84 | high | 7.72 |
| 0:47.17 | high | 5.94 |
| 1:01.38 | high | 6.15 |
| 1:30.24 | high | 5.54 |
| 1:35.85 | high | 10.94 |

### Digital Fizz

- Suspected range: 8-12 kHz

| timestamp | severity | measured cue |
| --- | --- | ---: |
| 0:09.75 | high | 11.65 |
| 0:13.99 | high | 9.91 |
| 0:19.20 | high | 9.16 |
| 0:22.19 | high | 13.4 |
| 0:47.17 | high | 11.27 |
| 1:29.77 | high | 10.41 |
| 1:35.85 | high | 13.32 |
| 1:50.12 | high | 9.6 |

### Unstable Vowel Tails

- Suspected range: phrase endings / tail texture

| timestamp | severity | measured cue |
| --- | --- | ---: |
| 0:02.96 | high | tail centroid variance 2088 Hz, high-band variance 9.2 dB |
| 0:08.47 | high | tail centroid variance 1927 Hz, high-band variance 9.2 dB |
| 0:09.71 | high | tail centroid variance 2830 Hz, high-band variance 8.0 dB |
| 0:11.14 | medium | tail centroid variance 398 Hz, high-band variance 7.6 dB |
| 0:13.25 | high | tail centroid variance 1044 Hz, high-band variance 9.7 dB |
| 0:14.74 | medium | tail centroid variance 416 Hz, high-band variance 10.6 dB |
| 0:17.81 | medium | tail centroid variance 882 Hz, high-band variance 5.3 dB |
| 0:19.22 | high | tail centroid variance 2079 Hz, high-band variance 6.8 dB |
| 0:20.76 | high | tail centroid variance 591 Hz, high-band variance 16.3 dB |
| 0:26.64 | high | tail centroid variance 2946 Hz, high-band variance 5.6 dB |

## Fixability

- Fixed/reduced: broad top glare, sandy S/T texture, low-mid vocal thickness, and detached vocal level.
- Hidden/reduced: robotic vowel tails by quieter vocal placement, density layer, and darker top-end control.
- Not chased: complete source artifact removal, because the chain is intentionally conservative.
