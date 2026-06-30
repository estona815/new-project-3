# Prompt 59 Manual Test Plan - Source Acceptance Gate

## Purpose

Verify that accepted source or isolated stem evidence is validated before final
export packaging, without modifying final export state or inventing user
acceptance.

## Commands

Create the request/template from current source handoff evidence:

```sh
python3 scripts/run_source_acceptance_gate.py \
  --project-name project \
  --output-dir automix
```

Validate one reviewed premaster candidate:

```sh
python3 scripts/run_source_acceptance_gate.py \
  --project-name project \
  --output-dir automix \
  --source-audio /path/to/accepted_premaster.wav \
  --source-stage accepted_premaster_draft \
  --source-role premaster \
  --source-classification accepted_premaster_render \
  --human-accepted \
  --require-ready
```

## Expected Outputs

- `automix/eval_reports/source_acceptance_gate.json`
- `automix/eval_reports/source_acceptance_gate.md`
- `automix/review/source_acceptance_manifest_template.json`
- `automix/review/source_acceptance_request.md`

## Pass Conditions

- No candidates reports `source_acceptance_candidates_missing`.
- Missing user acceptance reports `explicit_source_acceptance_missing`.
- Full-mix/reference candidates are rejected for automatic processing.
- A reviewed readable WAV with a valid accepted export stage can be marked
  `accepted_export_source_ready`.
- The gate does not write `final_export_state.json` or approve final delivery.

## Safety Limits

This check does not listen to audio, apply FX, render audio, update project
state, or approve a final. User A/B acceptance remains required.
