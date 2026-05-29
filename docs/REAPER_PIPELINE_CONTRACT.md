# REAPER Pipeline Contract

This contract defines the minimum structure required before this repository can make production claims.

## Required Input Folders

| Folder | Purpose |
| --- | --- |
| `input_stems/<song_slug>/` | User-owned stems for new work. |
| `audio_work/<song_slug>/` | Prepared side assets, repairs, prints, and analysis intermediates. |
| `references/<reference_set>/` | User-provided lawful references. Advisory only. |
| `reaper/<song_slug>/` | Versioned REAPER session folder. |
| `renders/<song_slug>/` | Candidate and final WAV/preview renders. |
| `reports/<song_slug>/` | JSON/Markdown QC, source manifest, user feedback, and decision reports. |
| `presets/mix_profiles/` | JSON production profiles used by the harness and ReaScripts. |

## Output Folders

- Candidate renders: `renders/<song_slug>/<candidate_id>.wav`
- Candidate reports: `reports/<song_slug>/<candidate_id>.json` and `.md`
- REAPER projects: `reaper/<song_slug>/<song_slug>_<candidate_id>.rpp`
- Pipeline harness reports: `reports/music_pipeline_report.json` and `reports/music_pipeline_report.md`
- WARN+ user prompt: `reports/WARN_PLUS_PROMPT.md`

## Naming Conventions

- Song slugs are lowercase snake case.
- Candidate IDs are deterministic: `A_safe`, `B_more_deai`, `C_punch_preserve`, `D_reference_match`.
- Never overwrite an older candidate render. If a file exists, create a new versioned session folder or stop with WARN/FAIL.
- Reference/fullmix files must include reference/fullmix role language in reports and must stay out of active premaster routing unless the classification is `fullmix_rescue` or `master_only`.

## REAPER Project Requirements

The contract track set is:

1. `01_REF_ORIGINAL`
2. `02_DRUMS`
3. `03_BASS`
4. `04_MUSIC`
5. `05_VOCAL`
6. `06_FX`
7. `07_PARALLEL_COMP`
8. `08_DEAI_BUS`
9. `09_MIX_BUS`
10. `10_MASTER_PRINT`

Rules:

- Missing stems must be reported. Empty tracks must not be treated as stem evidence.
- `01_REF_ORIGINAL` is muted/reference-only unless the classification is explicitly `fullmix_rescue` or `master_only`.
- True rebeat requires drum, bass, and music timeline evidence plus MIDI or placed reconstructed audio items.
- FX insertions must be logged with loaded/missing status. Missing required custom plugins are WARN or BLOCKER depending on mode.
- Custom JSFX must pass smoke checks before use.

## Render Requirements

Each candidate render must have:

- A unique WAV path.
- A matching JSON report.
- The source project path.
- Classification.
- Render bounds or source duration.
- REAPER command used or blocking reason.
- QC command to rerun.

Candidate intent:

- `A_safe`: conservative cleanup/master guard.
- `B_more_deai`: stronger artifact reduction, only valid if brightness/transient guards pass.
- `C_punch_preserve`: lower cleanup intensity, transient-first guard.
- `D_reference_match`: advisory reference translation only; cannot override clipping, phase, dullness, or musical intent.

## QC Report Requirements

The harness must report at minimum:

- Duration, sample rate, channels.
- Integrated loudness when available, or WARN when the dependency is missing.
- Peak level and approximate true peak.
- RMS and crest factor.
- Spectral centroid.
- Low band, low-mid mud, vocal presence, harshness, sibilance, air/fizz bands.
- Side/mid ratio.
- Transient proxy.
- Silence/noise-floor proxy.
- Before/after deltas.
- PASS/INFO/WARN/FAIL/BLOCKER findings.

Any WARN+ finding blocks final-success language and must print the exact next patch and rerun command.

