# User Feedback Revision Loop

Detailed workflow: [docs/user_feedback_revision_loop.md](docs/user_feedback_revision_loop.md).

## Purpose

User listening notes are first-class evidence. They are classified, mapped to
safe diagnostic actions, stored in revision memory, and carried into final
export gates.

## Flow

1. Initialize a no-feedback baseline with `--initialize-baseline` when no
   listening notes exist yet.
2. Record actual feedback with `scripts/run_feedback_revision_loop.py`.
3. Generate a dry-run action plan.
4. Run the relevant diagnostic or draft pass.
5. Review loudness-matched A/B.
6. Run measured QC.
7. Generate the feedback-QC integration report.
8. Resolve the feedback ID only with evidence and human review.
9. Final export remains blocked while unresolved feedback exists.

The baseline is only an audit marker. It must not be treated as user listening
approval or fabricated feedback.

## Resolution Requirements

To clear a feedback blocker, the resolution record must include:

- feedback ID;
- existing evidence file path;
- measured QC pass flag;
- loudness-matched A/B review flag;
- human review flag;
- resolution notes.

Incomplete resolution attempts are recorded but do not clear blockers.

## Feedback-QC Integration

`automix/eval_reports/user_feedback_qc_integration.json` and `.md` connect each
feedback item to cause hypotheses, planned dry-run actions, QC metric snapshots,
A/B review state, resolution records, and remaining risks. This report is
required for final delivery when feedback has been recorded.

## Recorded Approval Baselines

`mwolla_v14_no_chop_max_clarity_hook_reprise_master` is the current approved
`mwolla` baseline. The user stated that this current version is the favorite and
asked for it to be recorded in the pipeline and harness.

- Manifest: `reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/approved_baseline_manifest.json`
- Approval report: `reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/approved_pipeline_harness_update.md`
- Verify command: `python3 tools/mwolla_current_approved_master.py --verify-existing`

Future `mwolla` feedback should treat this baseline as the rollback/reference
point unless the user explicitly selects a different approved version.

## Common Mappings

- Cloudy vocal: mud, intelligibility, reverb distance, masking.
- Vocal too far back: dynamic music-bus carving and send ducking.
- Suno fizz: conservative artifact suppression and first-slot rescue trace.
- Flat master: limiter pressure, crest factor, LRA, true peak, A/B review.
- Phase or mono collapse: correlation, mono fold-down, M/S cleanup.
