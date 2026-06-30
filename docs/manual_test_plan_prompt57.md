# Manual Test Plan: Prompt57 Artifact Signal Audit

## Purpose

Confirm artifact-focused processing is not enabled from assumptions, zero
metrics, or unsupported cleanup claims.

## Static Test

```sh
python3 -m pytest tests/test_prompt57_artifact_signal_audit.py
```

Expected:

- missing or zero artifact metrics do not prove artifact absence;
- user feedback mentioning Suno fizz or watery smear can establish an artifact
  signal for planning;
- AI/source-separated source classification can establish a planning signal;
- `--require-established` returns non-zero while signal evidence is missing.

## Current Project Audit

```sh
python3 scripts/run_artifact_signal_audit.py \
  --project-name project \
  --output-dir automix
```

Review:

- `automix/eval_reports/artifact_signal_audit.json`
- `automix/eval_reports/artifact_signal_audit.md`

This audit does not claim artifact reduction or audio improvement. It only
checks whether source, metrics, or user feedback justify artifact-focused
dry-run planning.
