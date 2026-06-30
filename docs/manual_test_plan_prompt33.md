# Manual Test Plan Prompt 33

Use a saved copy of any REAPER project. This prompt is project triage only; do
not apply pitch correction to the original session during this test.

## Offline Scan

1. Run `python3 scripts/run_batch_pitch_triage.py --project SESSION.rpp --dry-run`.
2. Confirm `automix/analysis_reports/project_track_role_map.json` exists.
3. Confirm every project track has a role and a per-track triage JSON file.
4. Confirm masters, full-mix references, drums, bass, instruments, FX, and
   unknown tracks are skipped.

## Stem Requirement

1. Include at least one full-mix reference or source-separated vocal track.
2. Confirm it is not assigned to normal AutoTune.
3. Confirm a `{track_name}_stem_required_report.md` file is written.
4. Confirm the report asks for an isolated lead vocal stem.

## Draft Planning

1. Run scan mode first and verify no draft is created.
2. Run `conservative_apply_drafts` without `--apply-drafts` and confirm the CLI
   refuses the run.
3. Run `conservative_apply_drafts --apply-drafts --dry-run` only after reviewing
   the matrix.
4. Confirm `automix/rollback/project_pitch_rollback_index.json` is written and
   marks draft creation as pending REAPER runtime.

## Render Plan

1. Confirm scan-only mode has `render_required=false`.
2. Confirm applied draft plans add original, processed, loudness-matched, and
   difference renders to `project_pitch_render_plan.json`.
3. Confirm skipped tracks remain visible under `tracks_skipped_from_render`.

## Human Review

Do not accept a draft because it is more in tune. Reject it if the vocal becomes
more robotic, metallic, cloudy, smeared, phasey, or AI-like.
