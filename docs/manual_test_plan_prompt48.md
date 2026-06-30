# Manual Test Plan Prompt48 Intent Classification

## Purpose

Verify that intent classification is report-only, conservative, and fail-closed
before any safe-draft or final-delivery workflow is trusted.

## Unit Test

```sh
python3 -m pytest tests/test_prompt48_intent_classification.py
```

Expected:

- safe vocal and plugin-ready evidence allows conservative dry-run intents;
- full-mix, missing-stem, or missing-plugin evidence routes to review/blockers;
- aggressive creative enhancement is blocked by default;
- CLI writes JSON and Markdown reports;
- orchestrator scan-only writes the intent classification stage.

## CLI Smoke

```sh
python3 scripts/run_intent_classifier.py \
  --project-name project \
  --output-dir automix \
  --target-profile digicore_hyperpop_hiphop_vocal_forward \
  --verbose
```

Expected files:

- `automix/eval_reports/intent_classification.json`
- `automix/eval_reports/intent_classification.md`

## Review Checklist

- The report says it does not apply FX or prove a listening result.
- Every intent includes confidence, source risk, vocal priority, artifact focus,
  overprocessing risk, dry-run state, and human-review state.
- Full-mix polish and aggressive creative routes do not become automatic
  processing routes.
- Suno artifact handling uses reduction/suppression language only.
- Master-only routes do not override unresolved mix, stem, or feedback blockers.
