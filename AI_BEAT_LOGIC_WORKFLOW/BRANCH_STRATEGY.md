# Branch Strategy

Use small feature branches under the `codex/` prefix. Each branch should include narrow verification commands and a clean commit.

## Branches

1. `codex/ai-beat-workflow-scaffold`
   - Repository scaffold
   - README
   - CLI skeleton
   - Basic unit tests

2. `codex/ai-beat-audio-analysis`
   - Duration, sample rate, channels, peak, RMS, clipping, silence, and low-end heuristics
   - `analysis.json`
   - `analysis_summary.md`
   - Tests with generated WAV fixtures

3. `codex/ai-beat-processing-export`
   - Working WAV conversion
   - Gain staging, trim, fades, final WAV export
   - Output verification
   - Optional MP3 preview

4. `codex/ai-beat-logic-automation`
   - Logic Pro project creation/opening attempts where available
   - Fallback detection
   - Manual Logic edit instructions

5. `codex/ai-beat-qc-reporting`
   - Full QC report generation
   - Loudness/peak verification integration
   - Reels-friendly section notes

## Commit Discipline

- Commit only files related to the active branch.
- Do not stage unrelated workspace files.
- Include tests or a verification command in each branch.
- Never overwrite the original user-provided audio.

