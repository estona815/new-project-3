# Suno DeAI Artifact Rules

Suno/AI artifact reduction must reduce artifacts without over-cleaning the song. It is a multi-objective repair problem, not a single noise score.

## Artifact Targets

- Metallic fizz
- Fake air
- Watery stereo side wash
- Unstable high-frequency shimmer
- Vocal grain
- Sibilant splatter
- Synthetic room smear
- Aliased or phasey edges
- Over-smoothed transients
- Harsh upper-mid shards

## SUNO-001: Multi-Objective Cleanup

- Use when artifacts are detected or user notes call out AI noise, fizz, harshness, or watery stereo.
- Do not optimize only harshness or noise floor.
- Risk: dull vocal, collapsed stereo, reduced punch, transient smear, pumping, or lost detail.
- Metric guard: brightness, transient, side/mid, vocal presence, and punch checks must all run.
- Report: artifact targets, intensity, plugin/chain used, and each guard result.

## SUNO-002: Intensity Tiers

- Mild: safest default, minimal tonal change.
- Medium: for clear artifacts, requires extra QC.
- Strong: only for severe artifacts, not default final.
- Extreme: testing only, never default final.
- Risk: stronger settings can score cleaner while sounding worse.
- Metric guard: strong/extreme candidates need brightness, transient, side/mid, vocal presence, and punch PASS/WARN detail.
- Report: why the intensity was chosen and why rejected candidates were rejected.

## SUNO-003: MP3 Source Limitation

- Decode MP3 to WAV only as a working format.
- Do not claim lossless restoration or original-resolution mastering from MP3.
- Risk: aggressive top-end reconstruction magnifies codec hash.
- Metric guard: high-frequency changes must be conservative and preview encoding should not repeat unnecessary lossy generations.
- Report exact language: `Source was lossy MP3. Output is improved processing/mastering, not true lossless restoration.`

## SUNO-004: Custom Plugin Audit

- Use custom Suno DeAI JSFX only after file existence and syntax/smoke checks where possible.
- Do not silently assume a repo plugin loaded in REAPER.
- Risk: render does not use the intended chain.
- Metric guard: missing required custom plugin is WARN, FAIL, or BLOCKER depending on mode.
- Report: JSFX filename, FXChain reference name, smoke result, fallback used.
