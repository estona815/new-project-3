# Prompt65 Manual Test Plan - Final QC Evidence Gate

## Purpose

Validate that final QC metrics are usable delivery evidence only when they
match the real primary WAV render and contain passing measured QC results.

## Steps

1. Produce or place an accepted final WAV render and run:

```sh
python3 scripts/run_final_render_evidence_gate.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

2. Run final QC through the final export packager with `--qc`, or provide an
existing `automix/eval_reports/final_qc_metrics.json`.

3. Validate final QC evidence:

```sh
python3 scripts/run_final_qc_evidence_gate.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

4. Inspect:

- `automix/eval_reports/final_qc_evidence_gate.json`
- `automix/eval_reports/final_qc_evidence_gate.md`
- `automix/review/final_qc_evidence_manifest_template.json`
- `automix/review/final_qc_evidence_request.md`

## Expected Pass State

- `ready_for_delivery_qc` is true.
- `ready_for_approval_readiness` is true.
- `final_audio_path` matches `final_render_evidence_gate.primary_wav_path`.
- `qc_summary.qc_passed` is true.
- `qc_summary.failures` is empty.
- `render_link_summary.final_audio_in_render_manifest` is true.

## Expected Blockers

- Missing metrics produce `final_qc_metrics_missing_or_invalid`.
- Failed QC produces `final_qc_not_passed` and `final_qc_has_failures`.
- True peak above the ceiling produces `final_qc_true_peak_above_ceiling`.
- Path mismatch produces `final_audio_path_mismatch_render_evidence_primary_wav`.

## Limits

This gate validates evidence only. It does not approve audio, replace
loudness-matched A/B review, or replace human listening approval.
