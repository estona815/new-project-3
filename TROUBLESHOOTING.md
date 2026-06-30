# Troubleshooting

## Final Export Is Blocked

Check:

- `automix/export/final_export_state.json`
- `automix/export/final_render_manifest.json`
- `automix/export/deliverable_package_manifest.json`
- `automix/export/project_state_manifest.json`
- `automix/export/plugin_mapping_summary.md`
- `automix/eval_reports/final_ab_preview_manifest.json`
- `automix/eval_reports/intent_classification.json`
- `automix/eval_reports/processing_policy_audit.json`
- `automix/eval_reports/global_qc_summary.json`
- `automix/review/final_human_approval.json`
- `automix/review/user_feedback_revision_memory.json`
- `automix/eval_reports/user_feedback_qc_integration.json`
- `automix/eval_reports/final_qc_metrics.json`
- `automix/rollback/global_rollback_registry.json`

Common blockers:

- no accepted export source;
- approval missing;
- warnings not acknowledged;
- final QC missing or failed;
- final render manifest missing, failed, or missing primary WAV;
- delivery ZIP missing, empty, or package manifest has missing files;
- project state does not confirm original-track protection;
- A/B preview missing or not loudness matched;
- plugin mapping summary missing or empty;
- intent classification missing or routed to review-only;
- processing policy audit failed;
- unresolved user feedback;
- feedback-QC integration report missing when feedback has been recorded;
- unsafe claim language in generated reports;
- selected source file missing;
- rollback validation failed.

## Feedback Will Not Resolve

A feedback ID requires existing evidence, measured QC, loudness-matched A/B
review, and human review. Missing any one of those keeps the blocker active.
After recording or resolving feedback, rerun the feedback command or global QC
so `user_feedback_qc_integration.json` is refreshed.

## Plugin Mapping Is Blocked

Run plugin inventory and audit. Confirm adapter validation status before any
parameter write. Ambiguous plugin matches require manual review.

## Intent Classification Is Review-Only

Open `automix/eval_reports/intent_classification.md`. Common causes are full-mix
sources, missing stems, missing validated plugin mappings, unresolved feedback,
or a requested aggressive creative route that requires manual review.

## Processing Policy Audit Failed

Open `automix/eval_reports/processing_policy_audit.md`. Common causes are
non-draft chain plans, original-master limiting, OTT-style processing, aggressive
saturation, blind stereo widening, unsafe dry/wet values, or parameter discovery
on a plan marked safe to apply.

## Vocal Gets Worse

Stop stacking processing. Compare raw or selected cleanup stem against the
processed vocal. Check for tuning artifacts, saturation artifacts, layer smear,
reverb distance, masking, and phase instability.

## Master Sounds Loud But Weak

Audit limiter pressure, crest factor, LRA, low-end mono compatibility, and
transient loss. If the mix has vocal or low-end problems, return to mix revision
instead of pushing the limiter.

## Report Is Missing

Run scan-only or the relevant prompt script again with `--output-dir automix`.
Do not treat missing reports as success.
