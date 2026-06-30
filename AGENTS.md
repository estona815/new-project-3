# Project Operating Instructions

This project is a REAPER mix/master automation harness, not a one-off mix.

## Evidence Rules

- All work must be reproducible from source files, configs, scripts, traces, logs, and reports.
- Never claim listening results.
- Never claim "sounds good," "matches reference," or "finished master" unless measured evidence and user review explicitly support it.
- Always verify render and QC file existence before claiming delivery status.
- Every significant change must update reports or docs.

## Routing Rules

- Never place the raw full mix or reference in the active master path.
- The full mix/reference track must be named `SOURCE full mix reference muted - not in master`.
- The full mix/reference track must be muted.
- The full mix/reference track must have master send disabled.
- The full mix/reference track must not send to `MUSIC_BUS`, `VOCAL_BUS`, `MUSIC BUS`, `VOX BUS`, `MIX BUS`, `PREMASTER`, `PRINT MASTER`, `MASTER`, premaster, or any audible active bus.
- Residual rescue may use the full mix only as source material for a newly written processed asset.

## Plugin And Trace Rules

- Always create `work/traces/plugin_trace.json` after plugin insertion or planned insertion.
- Always validate that the first FX slot on `08 MALE_NONHOOK_CENTER` is exactly `JS: Codex Vocal AI Artifact Split Tamer`.
- External plugin parameters must not be hardcoded unless calibrated and documented.
- Parameter writes are allowed for native JSFX in this repo and verified Cockos mappings. External plugin writes require calibration evidence.
- Missing plugins must be logged as missing. Do not claim they loaded.
- Prefer the user's available plugin list and REAPER/Cockos stock processors. Do not require new paid plugins.
- Plugin overlap must be justified by role. If two processors do dynamic EQ, compression, clipping, widening, or saturation in one chain, document why both are needed.

## Digicore / Suno AI Audio Rules

- The goal is audible quality improvement, not AI detector evasion.
- Reduce Suno/AI artifacts such as metallic high end, harsh sibilance, smear, phase instability, and over-compressed pumping.
- Preserve intentional digicore, hip-hop, and hyperpop texture: autotune feel, clipping, glitch, blown-out vocal, sharp 808, and frequent hats are not automatically defects.
- Fix vocals, 808/bass, and drums before compensating on the master bus.
- Master-bus processing that sustains more than 2 dB of gain reduction is a warning to return to the mix, source buses, or stem cleanup.
- Every chain must be gain-matched for A/B review before claiming an improvement.

## Build Rules

- Prefer testable Python, Lua, and JSFX code over undocumented manual steps.
- Keep male vocal as the center lead when available.
- Keep female vocals as side, shadow, emotional width, or hook-lift support layers unless explicitly directed otherwise.
- "Done" means traces exist, renders exist, QC exists, gates pass or fail explicitly, and the delivery package exists.
- If REAPER, plugins, encoders, source stems, reference audio, or render outputs are missing, mark the runtime result as blocked or unverified.
