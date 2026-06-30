# Manual Test Plan Prompt49 Processing Policy Audit

## Purpose

Verify that chain plans are blocked before application or final delivery when
they violate conservative AutoMix policy.

## Unit Test

```sh
python3 -m pytest tests/test_prompt49_processing_policy_audit.py
```

Expected:

- conservative draft-only dynamic EQ plans pass;
- non-draft plans are blocked;
- original-master limiting is blocked;
- OTT-style processing is blocked by default;
- aggressive saturation and blind stereo widening are blocked;
- dry/wet values above the conservative cap are blocked;
- global QC blocks final delivery when policy audit fails.

## CLI Smoke

```sh
python3 scripts/run_processing_policy_audit.py \
  --project-name project \
  --output-dir automix \
  --verbose
```

Expected files:

- `automix/eval_reports/processing_policy_audit.json`
- `automix/eval_reports/processing_policy_audit.md`

## Review Checklist

- The report says it does not apply FX or prove audio quality.
- Every chain plan is listed with blockers and warnings.
- Plans marked `safe_to_apply` do not require parameter discovery.
- No plan mutates original tracks or the original master.
- Final delivery remains blocked when policy blockers exist.
