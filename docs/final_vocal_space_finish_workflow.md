# Final Vocal Space Finish Workflow

This workflow connects a human-accepted recovery vocal draft to a conservative placement draft, optional safe premaster draft, and review-only package.

It replaces many small prompts with one fail-closed finishing pass:

- validate accepted recovery source
- resolve lead, instrumental, backing, melody, and send targets
- analyze vocal masking
- build a vocal-space carving plan
- block pitch correction and destructive mastering
- create A/B and protection reports
- create a human review form
- optionally create a review package

## Why Space Carving

For Suno or already-processed AI vocals, making the vocal louder can expose fizz, metallic tone, sibilance, watery artifacts, and phase smear. This workflow prefers carving space around the vocal:

- sidechain dynamic EQ on instrumental or melody targets
- gentle backing vocal ducking
- reverb/delay return ducking
- conservative low-mid cleanup
- M/S cleanup only when safely mapped

It does not brighten the vocal first.

## Accepted Recovery Input

The workflow requires:

- `automix/review/accepted_recovery_sources.json`
- `automix/eval_reports/recovery_review_report.md`
- recovery rollback and original-protection reports
- plugin readiness report
- real-project track audit

If no accepted recovery source exists, it writes the reports but blocks placement and premaster.

## Pitch Remains Blocked

Pitch correction, full-mix tuning, robotic AutoTune, and pitch parameter writes are hard-blocked in this stage. Pitch can be discussed later as a recommendation, but this script does not insert pitch plugins.

## Placement Draft

The placement draft is draft-only. It must not modify original tracks, the original master, original media, or the accepted recovery draft destructively.

Profiles:

- `fragile_ai_vocal_space`
- `vocal_forward_space_carve`
- `melody_and_vocal_balance`
- `minimal_space_fix`

The selected profile is written to:

- `automix/chain_plans/final_vocal_space_carving_chain_plan.json`

## Premaster Draft

Premaster is optional and draft-only. It requires accepted or accepted_light placement review. The workflow blocks loudness chasing, master widening, high-end boosts, and final export.

Accepted light placement uses `safety_only_premaster`.

## Review Package

The package is named:

`deliverables/{project_slug}_REVIEW_PACKAGE_vXX/`

It is not named FINAL and does not mark the project ready for delivery. It collects reports, manifests, rollback metadata, and any available A/B assets.

## After Listening

Use the review form to decide:

- accepted
- accepted_light
- rejected
- needs_revision
- manual_mix_required

Only after human review should a later prompt prepare final delivery.
