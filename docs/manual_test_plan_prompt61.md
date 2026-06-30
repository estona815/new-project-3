# Prompt 61 Manual Test Plan - Artifact Evidence Gate

## Purpose

Verify that artifact-focused work has usable evidence before processing, and
that report-only placeholder metrics are not treated as measured artifact
metrics.

## Command

```sh
python3 scripts/run_artifact_evidence_gate.py \
  --project-name project \
  --output-dir automix
```

Use `--require-measured` when measured artifact metrics are required:

```sh
python3 scripts/run_artifact_evidence_gate.py \
  --project-name project \
  --output-dir automix \
  --require-measured
```

## Expected Outputs

- `automix/eval_reports/artifact_evidence_gate.json`
- `automix/eval_reports/artifact_evidence_gate.md`
- `automix/review/artifact_evidence_manifest_template.json`
- `automix/review/artifact_evidence_request.md`

## Pass Conditions

- Missing source, metric, and feedback evidence reports
  `artifact_evidence_not_established`.
- Missing measured artifact metrics reports `measured_artifact_metrics_missing`.
- High values in report-only or missing-render reports do not count as measured
  metrics.
- Actual user feedback can establish artifact evidence, but measured metrics
  remain required before acceptance.
- Source classification can establish planning evidence, but it does not prove
  cleanup or final quality.

## Safety Limits

This check does not process audio, reduce artifacts, approve a candidate, or
claim cleanup. Source, plugin, A/B, QC, and human approval gates still apply.
