# Install Plan

## Phase 0: Public PC Harness Creation

- Create docs, stubs, templates, and dry-run installers.
- Run no-audio and no-secret checks.
- Do not install anything.
- Do not log into accounts.

## Phase 1: Local Machine Safety Check

- Clone repo on trusted main computer.
- Confirm no private files are in repo.
- Run dry-run scripts.
- Confirm REAPER and plugin paths.

## Phase 2: REAPER Extension Installation

- Install SWS.
- Install ReaPack.
- Import ReaTeam repositories.
- Install js_ReaScriptAPI and ReaImGui only from verified sources.
- Restart REAPER and verify action availability.

## Phase 3: Audio Tool Installation

- Install FFmpeg first.
- Install Python QC packages in a virtual environment.
- Install Demucs only if machine has enough disk/GPU/CPU.
- Install UVR only if GUI workflow is desired.
- Install DeepFilterNet/RNNoise candidates only after reviewing model/storage impact.

## Phase 4: REAPER Template Setup

- Create source, separated stems, cleanup candidates, FX buses, render print, and reference tracks.
- Add markers and render regions.
- Keep source tracks muted/protected.

## Phase 5: Test With Dummy Audio

- Use synthetic dummy audio only.
- Validate routing, render filenames, and QC report creation.
- Do not use real Suno or artist material yet.

## Phase 6: Real Suno Vocal Workflow

- Import real material only on trusted machine.
- Generate A/B/C/D cleanup candidates.
- Compare listening and QC metrics.
- Export selected final only after manual approval.

