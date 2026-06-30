# Recovery Draft Human Review

Prompt 44 prevents recovery drafts from becoming trusted sources just because
they were created. A recovery draft must be explicitly reviewed and marked
`accepted` or `accepted_light` before later stages can use it.

## Why Drafts Are Not Auto-Accepted

AI/Suno vocal cleanup can make a vocal quieter, darker, duller, lispy, phasey,
or less emotional while still looking safer in metrics. Evaluation metrics can
support review, but they do not replace human listening.

## Review Flow

1. Run the recovery-only pilot.
2. Generate the review form.
3. Listen to original, recovery draft, loudness-matched A/B, and difference.
4. Accept only drafts that are better at matched loudness.
5. Use `accepted_light` for fragile AI vocals.
6. Reject drafts that are dull, thin, phasey, lispy, smeared, or less emotional.
7. Request stems if source quality blocks cleanup.
8. Proceed to vocal placement scan only after the review gate allows it.

## Commands

Generate form:

```sh
python3 scripts/run_recovery_review_gate.py \
  --project "/path/to/project.rpp" \
  --generate-form
```

Import JSON decisions:

```sh
python3 scripts/run_recovery_review_gate.py \
  --project "/path/to/project.rpp" \
  --input-decisions automix/review/recovery_review_decisions_input.json \
  --acknowledge-warnings
```

Accept one draft lightly:

```sh
python3 scripts/run_recovery_review_gate.py \
  --project "/path/to/project.rpp" \
  --accept-draft "Lead Vocal_RECOVERY_DRAFT_v01" \
  --decision accepted_light \
  --notes "Cleaner but fragile; placement only, pitch with caution." \
  --acknowledge-warnings \
  --allow-provisional-without-ab
```

## Accepted vs Accepted Light

`accepted` means the draft may feed placement analysis and pitch triage, but
pitch still requires the Prompt 31/32 safety gates.

`accepted_light` marks the source fragile. Downstream processing must stay more
conservative, pitch triage uses extra caution, and final export remains blocked
until later gates pass.

## A/B Policy

If A/B renders and evaluation passed, normal acceptance is allowed.

If A/B renders are missing, acceptance can only be provisional and only when
explicitly allowed. Provisional acceptance can feed placement analysis, but final
export remains blocked.

If evaluation failed, acceptance is blocked unless a future explicit unsafe
override mode exists; this implementation keeps final export blocked.

## Rejected Drafts

Rejected drafts are not deleted automatically. They remain review-only, keep
rollback metadata, and are blocked from placement, pitch, premaster, and final
export.

## Outputs

- `automix/review/recovery_review_form.md`
- `automix/review/recovery_review_state.json`
- `automix/review/accepted_recovery_sources.json`
- `automix/review/recovery_ab_review_status.json`
- `automix/review/rejected_recovery_drafts.json`
- `automix/review/recovery_revision_request.md`
- `automix/orchestrator/downstream_recovery_gate.json`
- `automix/eval_reports/recovery_review_report.md`

