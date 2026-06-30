# Prompt53 Risk Remediation Plan Manual Test Plan

## Purpose

Verify that the open risk register can be converted into a safe, dry-run
remediation plan with commands, required evidence, acceptance criteria, and
disallowed unsafe shortcuts.

## Commands

```sh
python3 scripts/run_open_risk_register.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_risk_remediation_plan.py \
  --project-name project \
  --output-dir automix
```

## Expected Result

- `automix/eval_reports/risk_remediation_plan.json` exists.
- `automix/eval_reports/risk_remediation_plan.md` exists.
- Every action is `dry_run_only`.
- Every action is non-destructive.
- Plugin risks map to plugin inventory/adapter validation steps.
- Source risks map to stem/manual-review steps.
- Final export risks map to accepted-source, render, QC, A/B, approval,
  rollback, and readiness evidence.

## Limits

The remediation plan does not apply FX, approve audio, or clear blockers by
itself. Commands with placeholder project/audio paths must be filled in by the
operator before use.
