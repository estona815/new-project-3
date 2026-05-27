# Failure Modes

## Audio Quality

- Over-denoise: vocal loses identity, breath, room, or emotion.
- Watery artifacts: separation/denoise produces bubbling modulation.
- Metallic artifacts: high-frequency ringing or robotic sheen.
- Vocal thinning: body around low-mid/midrange is removed.
- Phase smear: stereo or stem processing blurs timing and image.
- Stem bleed: instrumental leaks into vocal stem or vocal leaks into instrumental.
- Broken consonants: S, T, K, P, CH, and breath attacks are damaged.
- Pitch correction changes vocal identity.
- Saturation exaggerates AI fizz.
- Reverb hides repair artifacts instead of fixing them.
- Metering is mistaken for tone improvement.
- Limiting hides balance problems.

## Tooling

- Plugin scan failure.
- Missing REAPER extension.
- ReaPack repository unavailable.
- js_ReaScriptAPI not installed.
- ReaImGui not installed.
- FFmpeg missing.
- Demucs/UVR model missing or too large.
- Python package mismatch.
- Safety gate false positive.
- Manifest schema drift.
- Runner mode accidentally attempts real execution.
- Dummy fixture accidentally written outside `local_only/`.

## Public PC Contamination Risk

- Personal login cached in browser or CLI.
- License files accidentally copied.
- Private audio added to repo.
- Install script accidentally run.
- Real generated reports expose filenames or artist material.
- `local_only/` content accidentally staged.

## Response

- Stop.
- Do not continue processing.
- Preserve source files.
- Write a failure note.
- Re-run safety checks.
