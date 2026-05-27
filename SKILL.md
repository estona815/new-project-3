# Codex Skill: Suno Vocal Repair REAPER Harness

Use this skill to prepare, operate, and audit a REAPER-based Suno vocal repair workflow on a trusted local production computer. On public/shared computers, operate in documentation-only and dry-run mode.

## Prime Directive

Do not over-denoise. Preserve vocal identity, phrasing, consonants, breath shape, and emotional contour. Prefer A/B/C candidate workflows over destructive single-pass processing.

## Operating Principles

- Always keep the original vocal or full mix untouched.
- Generate multiple conservative cleanup candidates:
  - Candidate A: minimal repair
  - Candidate B: balanced cleanup
  - Candidate C: stronger artifact control
  - Candidate D: emergency salvage only
- Compare candidates against the source before final selection.
- Use stem separation and denoise tools as assistants, not final truth.
- Favor reversible REAPER routing, muted reference tracks, and printed candidate renders.
- Never claim plugin, REAPER extension, stem separation, denoise, render, or QC success until verified on disk.

## Public PC Behavior

Allowed:

- Write docs and templates.
- Create dry-run scripts.
- Create REAPER Lua stubs.
- Create QC script stubs.
- Run no-audio and no-secret verification.

Banned:

- Installing REAPER extensions.
- Installing plugins.
- Downloading AI models.
- Logging into accounts.
- Processing real audio.
- Storing private music.

## Future Local Workflow

1. Verify trusted local machine.
2. Install REAPER extensions after dry-run review.
3. Install audio tools after dry-run review.
4. Build REAPER project template.
5. Test with dummy audio.
6. Import real source only after safety checks pass.
7. Generate cleanup candidates.
8. Render and compare.
9. Write QC report.
10. Export final only after listening and metrics agree.

