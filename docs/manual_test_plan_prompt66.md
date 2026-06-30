# Prompt66 Manual Test Plan - Final Approval Evidence Gate

## Purpose

Validate that final delivery cannot treat a human approval record as complete
unless it references the loudness-matched A/B preview, final audio, and final QC
evidence reviewed by the operator.

## Steps

1. Run render, final QC, A/B preview, and their evidence gates.
2. Record `automix/review/final_human_approval.json` only after listening to the
   matched-loudness A/B preview.
3. Run:

```sh
python3 scripts/run_final_approval_evidence_gate.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

4. Inspect:

- `automix/eval_reports/final_approval_evidence_gate.json`
- `automix/eval_reports/final_approval_evidence_gate.md`
- `automix/review/final_approval_evidence_manifest_template.json`
- `automix/review/final_approval_evidence_request.md`

## Expected Pass State

- `ready_for_delivery_request` is true.
- `approved` is true.
- `review_decision` is `accepted` or `accepted_with_limitations`.
- `loudness_matched_ab_reviewed` is true.
- `final_audio_accepted_at_matched_loudness` is true.
- `reviewed_ab_preview_path` matches the A/B preview evidence output path.
- `reviewed_final_audio_path` matches the final QC evidence audio path.

## Expected Blockers

- Missing approval produces `final_human_approval_missing_or_invalid` or
  `final_human_approval_missing`.
- Missing A/B review evidence produces `loudness_matched_ab_review_not_recorded`.
- Missing final acceptance produces `final_audio_not_accepted_at_matched_loudness`.
- Missing reviewed paths produce `reviewed_ab_preview_path_missing` or
  `reviewed_final_audio_path_missing`.

## Limits

This gate does not listen to audio, infer approval, or replace user judgment. It
only checks that the approval record is auditable and linked to the required
evidence.
