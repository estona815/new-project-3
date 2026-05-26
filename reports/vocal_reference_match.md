# Vocal Reference Match

## Estimated Key / Scale
- Estimated key: C# major (confidence proxy 4.111).

## Vocal Profiles
| label | rms_dbfs | body_centroid_hz | formant_centroid_hz | presence_centroid_hz | air_centroid_hz | body_150_400_pct | nasal_formant_700_1400_pct | presence_harsh_2500_5500_pct | sibilance_5500_9000_pct | glass_ai_air_9000_12000_pct | top_air_12000_16000_pct | mid_harmonic_density | sibilance_to_mid_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| target_raw_male_lead | -24.02 | 284.8 | 971.5 | 3497.8 | 10568.7 | 24.036 | 45.019 | 12.876 | 8.075 | 7.767 | 2.226 | 1.8725 | 0.2746 |
| reference_vocal_proxy | -20.2 | 226.0 | 1002.4 | 3767.9 | 10432.1 | 54.134 | 18.26 | 16.698 | 8.308 | 2.285 | 0.314 | 1.8351 | 0.2859 |
| processed_male_lead | -17.15 | 295.4 | 984.9 | 3391.6 | 10674.5 | 29.43 | 41.169 | 21.603 | 3.2 | 3.415 | 1.184 | 1.5355 | 0.1568 |

## Applied Direction
- Matched toward the reference vocal tone, not the reference master loudness.
- Added a formant-preserving parallel tune edge: verse equivalent 22-35 ms, hook equivalent 10-18 ms, humanize proxy 58%, formant shift 0.
- Added Decapitator-style density: main drive 2.6 / mix 13%, parallel bus drive 5.2 with HPF 150 Hz and LPF 6.8 kHz, blended low.
- Dynamic EQ controlled 720 Hz-1.45 kHz formant, 2.5-5.5 kHz harshness, 5.5-9.2 kHz sibilance, and 9-12 kHz glassy AI air.
- Female adlibs/backing remain wider and wetter than the lead, sidechain-ducked under the male vocal.

## Limitation
- Real Auto-Tune/Melodyne note correction was not available, so tune is an engineered impression layer rather than note-by-note pitch editing.
- Reference vocal stem is a proxy, not clean Demucs extraction; exact singer identity is not cloned.
