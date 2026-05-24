
# Master Settings

- Render `PREMASTER_24bit_48k.wav` before any aggressive limiter.
- Render `MASTER_24bit_48k.wav` with true peak ceiling -1.0 dBTP.
- Render `MASTER_320k.mp3` only after WAV master exists and ffmpeg is available.
- Avoid over-limiting, upper-mid buildup, clipped transients, buried vocal, and phasey side material.
- Use loudness/reference numbers as direction, not as a cloning target.
