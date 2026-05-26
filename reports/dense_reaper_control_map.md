# Dense REAPER Control Map

This map contains many measured control points. They are target ranges for automation, not proof of exact plugin settings.

- Source files: 8
- Dense EQ/M-S/dynamic points: 230
- Resonance watch points: 43

## Example Control Points
- 25.0 Hz: target -24.72 dB share, side-mid -30.77 dB, MonoSub/M-S low control
- 35.36 Hz: target -13.58 dB share, side-mid -38.05 dB, MonoSub/M-S low control
- 50.0 Hz: target -11.31 dB share, side-mid -31.15 dB, MonoSub/M-S low control
- 70.71 Hz: target -14.96 dB share, side-mid -23.54 dB, MonoSub/M-S low control
- 100.0 Hz: target -19.98 dB share, side-mid -16.66 dB, MonoSub/M-S low control
- 141.42 Hz: target -24.12 dB share, side-mid -13.33 dB, ReaEQ/ReaXcomp mud control
- 200.0 Hz: target -27.13 dB share, side-mid -11.67 dB, ReaEQ/ReaXcomp mud control
- 282.84 Hz: target -27.27 dB share, side-mid -8.48 dB, ReaEQ/ReaXcomp mud control
- 400.0 Hz: target -26.01 dB share, side-mid -7.69 dB, ReaEQ broad tonal control
- 565.69 Hz: target -26.78 dB share, side-mid -9.48 dB, ReaEQ broad tonal control
- 800.0 Hz: target -29.69 dB share, side-mid -5.70 dB, ReaEQ broad tonal control
- 1131.37 Hz: target -28.79 dB share, side-mid -7.19 dB, ReaEQ broad tonal control
- 1600.0 Hz: target -28.79 dB share, side-mid -7.74 dB, ReaEQ broad tonal control
- 2262.74 Hz: target -29.65 dB share, side-mid -7.77 dB, ReaXcomp presence/harsh dynamic EQ
- 3200.0 Hz: target -31.44 dB share, side-mid -6.34 dB, ReaXcomp presence/harsh dynamic EQ
- 4525.48 Hz: target -32.42 dB share, side-mid -6.81 dB, ReaXcomp presence/harsh dynamic EQ
- 6400.0 Hz: target -31.10 dB share, side-mid -7.99 dB, ReaXcomp presence/harsh dynamic EQ
- 9050.97 Hz: target -31.90 dB share, side-mid -8.62 dB, Air/hash smoothing
- 12800.0 Hz: target -35.48 dB share, side-mid -8.46 dB, Air/hash smoothing
- 18101.93 Hz: target -43.22 dB share, side-mid -6.59 dB, Air/hash smoothing

## Strongest Resonance Watch Points
- 126.0 Hz: local prominence 6.03 dB, target level -16.62 dB
- 106.0 Hz: local prominence 4.82 dB, target level -15.98 dB
- 733.6 Hz: local prominence 4.73 dB, target level -22.53 dB
- 86.5 Hz: local prominence 4.42 dB, target level -14.95 dB
- 94.4 Hz: local prominence 4.39 dB, target level -15.19 dB
- 436.2 Hz: local prominence 4.05 dB, target level -21.96 dB
- 244.8 Hz: local prominence 4.02 dB, target level -22.45 dB
- 979.2 Hz: local prominence 3.80 dB, target level -24.67 dB
- 81.7 Hz: local prominence 3.66 dB, target level -15.72 dB
- 872.4 Hz: local prominence 3.56 dB, target level -24.91 dB
- 489.6 Hz: local prominence 3.53 dB, target level -22.46 dB
- 218.1 Hz: local prominence 3.50 dB, target level -22.01 dB
- 388.6 Hz: local prominence 3.46 dB, target level -23.71 dB
- 653.6 Hz: local prominence 3.39 dB, target level -22.34 dB
- 336.4 Hz: local prominence 2.96 dB, target level -24.73 dB
- 1467.2 Hz: local prominence 2.51 dB, target level -25.48 dB
- 1099.2 Hz: local prominence 2.49 dB, target level -25.27 dB
- 2198.3 Hz: local prominence 2.46 dB, target level -26.63 dB
- 2934.4 Hz: local prominence 2.19 dB, target level -27.86 dB
- 149.8 Hz: local prominence 2.08 dB, target level -22.47 dB
- 1958.5 Hz: local prominence 2.03 dB, target level -26.78 dB
- 194.3 Hz: local prominence 1.91 dB, target level -22.29 dB
- 57.8 Hz: local prominence 1.77 dB, target level -11.41 dB
- 1307.1 Hz: local prominence 1.72 dB, target level -25.37 dB
- 70.7 Hz: local prominence 1.66 dB, target level -14.96 dB
- 291.1 Hz: local prominence 1.57 dB, target level -25.70 dB
- 1744.8 Hz: local prominence 1.51 dB, target level -26.34 dB
- 178.2 Hz: local prominence 1.47 dB, target level -23.31 dB
- 582.3 Hz: local prominence 1.42 dB, target level -24.57 dB
- 549.6 Hz: local prominence 1.37 dB, target level -24.61 dB

## How To Use
- When `current_mix.wav` exists, compare its dense map to this reference map.
- Only automate bands with meaningful deltas, grouped into a small number of musical moves.
- Do not instantiate hundreds of ReaEQ bands blindly; use this as a measurement grid.
