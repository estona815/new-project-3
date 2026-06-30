# Prompt 42 Manual Test Plan

Use this plan when REAPER is available and a real `.rpp` project can be opened
or inspected locally. The pilot must remain scan-only.

## A. Read-Only Guard Tests

- No changes: run scan, confirm `safe: true` and `modified: false`.
- Track FX count changes: intentionally compare against a copied/edited project
  snapshot and confirm modification detection.
- Routing changes: compare snapshots with changed send/receive counts.
- Master FX changes: compare snapshots with changed master FX count.
- Media item count changes: compare snapshots with changed item count.

## B. Prompt 41 Preconditions

- Prompt 41 missing: scan continues, warning is visible, safe_draft not ready.
- Prompt 41 FAIL: scan continues, safe_draft is not ready.
- Prompt 41 PASS: status is included in readiness scoring.

## C. Real Project Audit

- `automix/analysis_reports/real_project_track_audit.json` is created.
- `automix/eval_reports/real_project_source_safety_map.json` is created.
- `automix/eval_reports/real_project_plugin_readiness.json` is created.
- `automix/chain_plans/real_project_dry_run_chain_proposals.json` is created.
- `automix/eval_reports/real_project_stem_request_plan.md` is created.
- `automix/eval_reports/real_project_scan_only_report.md` is created.

## D. Safety

- Full mix tracks block pitch correction.
- Already tuned AI vocal tracks block strong correction.
- Unknown tracks are skipped.
- Unmapped plugins block processing proposals.
- No project modification occurs.

## E. Readiness

- Missing plugin mappings lower readiness.
- Stem-required tracks lower readiness.
- Read-only failure sets `ready: false`.
- Report completeness increases readiness.
- `recommended_next_mode` is one of the allowed enum values.

## F. CLI

- Defaults are strict read-only and dry-run.
- `--dry-run` prevents modifications.
- No final export is created.
- No draft tracks are created.
- No plugin is inserted.

