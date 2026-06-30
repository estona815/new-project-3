# Prompt 44 Manual Test Plan

## A. Preconditions

- Missing Prompt 43 blocks review acceptance.
- Failed original protection blocks acceptance.
- Failed pitch block blocks acceptance.
- No drafts creates `no_recovery_drafts_to_review`.

## B. Review State

- Default decision is `needs_review`.
- `needs_review` blocks downstream.
- `accepted` allows placement.
- `accepted_light` marks source fragile and pitch-extra-cautious.
- `rejected` blocks downstream.
- `stem_required` creates a stem request.
- `manual_cleanup_required` blocks automated downstream use.

## C. A/B Policy

- A/B complete and evaluation passed allows normal acceptance.
- A/B missing allows only provisional acceptance when explicitly enabled.
- Evaluation failed blocks acceptance.
- Missing loudness-matched render warns.
- Missing difference render warns.

## D. Importer

- Valid JSON decisions are imported.
- Invalid decisions are rejected.
- Existing non-default decisions are not overwritten without `--update`.
- Warnings must be acknowledged.
- Notes are saved.

## E. Downstream Gate

- Placement uses only accepted sources.
- Pitch triage uses accepted sources with caution.
- Rejected draft is blocked from premaster.
- Final export blocks unreviewed drafts.
- Review package can include unaccepted drafts only as review-only.

## F. Reports

- Review form created.
- Review state JSON created.
- Accepted sources JSON created.
- Rejected drafts JSON created.
- Revision request created when needed.
- Recovery review report created.

