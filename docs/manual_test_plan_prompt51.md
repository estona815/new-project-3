# Prompt51 Requirements Traceability Manual Test Plan

## Purpose

Verify that the project brief requirements can be traced to current code,
documentation, tests, and runtime reports.

## Commands

```sh
python3 scripts/run_fixture_coverage_audit.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_requirements_traceability_audit.py \
  --project-name project \
  --output-dir automix
```

## Expected Result

- `automix/eval_reports/requirements_traceability_audit.json` exists.
- `automix/eval_reports/requirements_traceability_audit.md` exists.
- `passed` is `true`.
- Each requirement ID from `REQ-01` through `REQ-14` is marked `satisfied`.

## Coverage Areas

- non-destructive original protection;
- conservative processing policy;
- Suno/AI artifact suppression language and gates;
- vocal-first mix strategy;
- user feedback revision loop;
- source intake and role classification;
- audio diagnosis metrics;
- intent classification with confidence/risk scores;
- plugin fallback and parameter clamp safety;
- dry-run, preview, A/B render, and rollback gates;
- mastering QC;
- REAPER-free fixture harness;
- professional docs and claim guard;
- delivery readiness evidence.

## Limits

Traceability proves that implementation evidence exists. It does not prove that
a particular render sounds better, meets a commercial loudness target, or has
been accepted by the user.
