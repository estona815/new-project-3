# Prompt 58 Manual Test Plan - Approval Export Readiness

## Purpose

Verify that approval export readiness reports accepted source, render, A/B
preview, project-state, feedback, and explicit human approval gates without
creating or inferring approval.

## Commands

```sh
python3 scripts/run_approval_export_readiness.py \
  --project-name project \
  --output-dir automix
```

Use `--require-ready` when a nonzero exit code should block a delivery request:

```sh
python3 scripts/run_approval_export_readiness.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

## Expected Outputs

- `automix/eval_reports/approval_export_readiness.json`
- `automix/eval_reports/approval_export_readiness.md`
- `automix/review/final_approval_request.md`

## Pass Conditions

- Missing accepted source reports `accepted_export_source_missing`.
- Missing or unmatched A/B preview reports
  `ab_preview_missing_or_not_loudness_matched`.
- Missing explicit approval reports `final_human_approval_missing`.
- If every technical gate is present except approval, status is
  `ready_for_human_approval_request`, not `ready_for_delivery_request`.
- Human approval is never fabricated from report status, QC, or A/B evidence.

## Safety Limits

This check does not listen to audio, apply FX, render audio, package delivery,
or approve a final. User listening review remains required.
