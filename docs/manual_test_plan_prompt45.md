# Manual Test Plan: Prompt45 User Feedback Revision Loop

## Static Tests

Run:

```sh
python3 -m pytest tests/test_prompt45_user_feedback_revision_loop.py
```

Expected:

- Korean feedback is classified into vocal, AI artifact, and mastering issues.
- Action plans are dry-run only.
- Unsafe automatic responses are blocked.
- Revision memory persists entries.
- Repeated feedback categories are marked.
- Global QC blocks final delivery when unresolved feedback exists.
- Final export state resolution blocks delivery when unresolved feedback exists.
- Feedback resolution stays blocked when evidence, measured QC, A/B review, or
  human review is missing.
- Feedback resolution clears the blocker only with existing evidence and all
  review/QC flags.
- The CLI blocks empty feedback.

## CLI Smoke

Run:

```sh
python3 scripts/run_feedback_revision_loop.py \
  --output-dir /tmp/automix-feedback-smoke \
  --project-name smoke_project \
  --pass-id v01 \
  --feedback "보컬이 뿌옇고 마스터가 너무 납작하다."
```

Confirm these files exist:

- `/tmp/automix-feedback-smoke/review/user_feedback_revision_memory.json`
- `/tmp/automix-feedback-smoke/eval_reports/user_feedback_action_plan.json`
- `/tmp/automix-feedback-smoke/eval_reports/user_feedback_revision_report.md`

## Resolution Smoke

Get a feedback ID from `user_feedback_revision_memory.json`, then run:

```sh
python3 scripts/run_feedback_revision_loop.py \
  --output-dir /tmp/automix-feedback-smoke \
  --project-name smoke_project \
  --pass-id v02 \
  --resolve-feedback-id feedback_ID_HERE \
  --resolution-notes "Measured QC and loudness-matched A/B review passed." \
  --evidence-path /tmp/automix-feedback-smoke/eval_reports/final_qc_metrics.json \
  --human-reviewed \
  --measured-qc-passed \
  --loudness-matched-ab-reviewed
```

Expected:

- missing evidence returns `feedback_resolution_blocked`;
- complete evidence returns `feedback_resolution_accepted`;
- `pending_unresolved_count` reaches `0` only after complete evidence.

## Gate Check

After creating unresolved feedback, rebuild global QC in a final-delivery
context. Confirm `safe_to_export=false` and
`user_feedback_unresolved_for_final_delivery` appears in critical blockers.

Resolve final export state with an accepted premaster source and the same
`output-dir`. Confirm `safe_to_export=false`,
`required_reviews=["user_feedback_revision_loop"]`, and
`user_feedback_unresolved_for_final_delivery` appears in `blocked_reasons`.
After evidence-gated feedback resolution, confirm the same accepted source no
longer has the user-feedback blocker.

## Manual Listening Check

Use the generated action plan only to choose the next diagnostic pass. Do not
mark feedback resolved until a loudness-matched A/B and human review support the
claim.
