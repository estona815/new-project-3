# Manual Test Plan Prompt69 Risk Root Cause Rollup

## Purpose

Verify that open risk register entries are grouped into deterministic root
causes before remediation planning. This report is evidence triage only; it does
not approve audio, apply FX, or replace source reports.

## Steps

1. Run the open risk register.

```sh
python3 scripts/run_open_risk_register.py \
  --project-name project \
  --output-dir automix
```

2. Run the root-cause rollup.

```sh
python3 scripts/run_risk_root_cause_rollup.py \
  --project-name project \
  --output-dir automix
```

3. Confirm `automix/eval_reports/risk_root_cause_rollup.json` and `.md` exist.
4. Confirm repeated plugin/source/render/QC/package blockers are grouped under
   root causes and `next_root_cause` points to the earliest unresolved phase.
5. Run the remediation plan and confirm it references
   `risk_root_cause_rollup.json`.

```sh
python3 scripts/run_risk_remediation_plan.py \
  --project-name project \
  --output-dir automix
```

## Expected Result

- `root_cause_total` is lower than or equal to `open_risk_total`.
- `next_root_cause` names the first blocker phase to resolve.
- The markdown report states that the rollup does not approve audio.
