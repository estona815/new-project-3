# Manual Test Plan Prompt40

## Mode Tests

- `scan_only` modifies nothing and writes manifest/report/index/QC summary.
- `safe_draft` creates drafts only when gates pass.
- `diagnostic_continue` continues analysis only after a blocker.
- `final_delivery` blocks without approval.
- `final_delivery` blocks on QC failure.
- professional readiness audit runs in `scan_only` and `final_delivery`.
- professional readiness audit blocks final delivery when evidence or review is
  incomplete.

## Dependency Tests

- pitch cannot run before classification.
- pitch draft cannot run before safety gate approval.
- premaster cannot run from rejected placement.
- final export cannot run from rejected premaster.
- accepted reference-match changes require premaster rerun.

## Safety Controller Tests

- full-mix pitch attempt blocks.
- low plugin confidence blocks.
- missing A/B render blocks final export.
- original track modification blocks workflow.
- rollback validation failure blocks workflow.

## Rollback Tests

- global rollback registry is created.
- every applied stage has rollback.
- original tracks are protected.
- original master is protected.
- missing rollback causes a blocker.

## Report Tests

- orchestration manifest is created.
- orchestration report is created.
- report index is created.
- global QC summary is created.
- professional readiness audit report is created.
- skipped stages are visible.
- warnings are visible.

## Resume Tests

- previous reports are detected.
- stale reports are marked stale when project changes.
- accepted drafts are not overwritten.
- conflicting reports require manual review.

## CLI Tests

- default mode is `scan_only`.
- `--dry-run` prevents modifications.
- `--no-pitch` blocks pitch stage.
- `--approve-final` does not override QC failure.
- `--diagnostic-continue` cannot apply processing.
