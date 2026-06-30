# Prompt52 Open Risk Register Manual Test Plan

## Purpose

Verify that current AutoMix reports can be summarized into a single operator
risk register with blockers, warnings, review items, and safe next actions.

## Command

```sh
python3 scripts/run_open_risk_register.py \
  --project-name project \
  --output-dir automix
```

## Expected Result

- `automix/eval_reports/open_risk_register.json` exists.
- `automix/eval_reports/open_risk_register.md` exists.
- Source, plugin, final export, readiness, and report warnings are represented
  as explicit risk entries when present.
- Each risk has a severity, category, source report, code, summary, and
  recommended next action.

## Review Notes

- Existing source risks should point to stem requests or manual review.
- Plugin readiness risks should point to adapter validation.
- Final export risks should point to accepted source, render, QC, A/B, approval,
  rollback, and package evidence.
- A clean risk register does not prove that the audio sounds good.

## Limits

This register summarizes report evidence. It does not listen to audio, replace
human approval, or override the professional readiness audit.
