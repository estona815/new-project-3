# Failure Modes

## Audio Quality

- Over-denoise: vocal loses identity, breath, room, or emotion.
- Watery artifacts: separation/denoise produces bubbling modulation.
- Metallic artifacts: high-frequency ringing or robotic sheen.
- Vocal thinning: body around low-mid/midrange is removed.
- Phase smear: stereo or stem processing blurs timing and image.
- Stem bleed: instrumental leaks into vocal stem or vocal leaks into instrumental.
- Broken consonants: S, T, K, P, CH, and breath attacks are damaged.

## Tooling

- Plugin scan failure.
- Missing REAPER extension.
- ReaPack repository unavailable.
- js_ReaScriptAPI not installed.
- ReaImGui not installed.
- FFmpeg missing.
- Demucs/UVR model missing or too large.
- Python package mismatch.

## Public PC Contamination Risk

- Personal login cached in browser or CLI.
- License files accidentally copied.
- Private audio added to repo.
- Install script accidentally run.
- Real generated reports expose filenames or artist material.

## Response

- Stop.
- Do not continue processing.
- Preserve source files.
- Write a failure note.
- Re-run safety checks.

