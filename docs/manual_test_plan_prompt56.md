# Manual Test Plan: Prompt56 Source Handoff Readiness

## Purpose

Confirm that current source-file presence is not treated as accepted export
source evidence or isolated stem evidence.

## Static Test

```sh
python3 -m pytest tests/test_prompt56_source_handoff_readiness.py
```

Expected:

- stem-required tracks remain blocked even when the current source file exists;
- accepted source evidence is tracked separately from source file presence;
- the handoff request lists required stems and manual-review tracks;
- `--require-ready` returns non-zero while blockers remain.

## Current Project Handoff

```sh
python3 scripts/run_source_handoff_readiness.py \
  --project-name project \
  --output-dir automix
```

Review:

- `automix/eval_reports/source_handoff_readiness.json`
- `automix/eval_reports/source_handoff_readiness.md`
- `automix/review/source_stem_handoff_request.md`

Acceptance for automatic processing requires actual accepted source evidence,
clear stem requests, and human review. Existing full-mix or reference files are
not enough.
