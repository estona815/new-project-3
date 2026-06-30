# Final Export And Delivery

Prompt 37 adds the delivery layer for the AutoMix workflow. It runs after vocal
recovery, optional pitch correction, vocal placement, and premaster safety have
passed review. The goal is a clean client-grade delivery folder, not a random
render dump.

## Accepted Source Required

Final export must resolve one accepted source stage:

1. accepted premaster draft;
2. accepted vocal placement draft if no premaster was used;
3. accepted pitch/recovery integrated draft if no placement was used;
4. accepted recovery draft if no pitch, placement, or premaster was used;
5. original mix only when explicitly approved and all processing was skipped.

Rejected premaster, rejected placement, rejected recovery, unsafe pitch,
unresolved human review, missing A/B renders, master mutation, or rollback
validation failure blocks final export.

Before passing a user-provided WAV into final export packaging, run
`scripts/run_source_acceptance_gate.py`. The source acceptance gate requires a
readable WAV, a valid accepted stage, and explicit user listening acceptance. It
rejects full-mix/reference material as automatic processing input unless the
stage is `original_mix_explicitly_approved`.

Unresolved user feedback also blocks final export. If
`automix/review/user_feedback_revision_memory.json` contains pending unresolved
items, the final export state includes
`user_feedback_unresolved_for_final_delivery` even when an accepted premaster
source exists. Resolve the feedback with measured QC and human review before
creating a delivery package.

Feedback resolution also requires an existing evidence file and
loudness-matched A/B review. Incomplete resolution attempts are recorded but do
not clear the final export blocker.

## Why WAV Is Primary

WAV is the primary deliverable because it preserves the mix/master without lossy
encoding damage. MP3 is useful for review, sharing, and client preview, but
MP3-only final delivery is blocked. If an MP3 encoder is unavailable, the system
reports that limitation instead of pretending an MP3 was created.

## Human Approval

Final export requires explicit approval unless running in diagnostic mode.
Warnings must be acknowledged. Unsafe override can create only an
`UNSAFE_REVIEW_COPY`; it cannot create a file named `FINAL_SAFE`.

## A/B Preview

The A/B preview montage alternates original and final processed sections:

- original mix, 8 seconds;
- final processed, 8 seconds;
- original mix, 8 seconds;
- final processed, 8 seconds.

The preview is loudness matched when possible and its manifest labels every
segment so the review copy cannot be mislabeled.

## Approval Export Readiness

Run `scripts/run_approval_export_readiness.py` after the final export state,
render manifest, A/B preview manifest, project-state manifest, and human
approval file exist. This audit does not approve audio. It reports whether the
accepted export source, primary WAV render evidence, loudness-matched A/B
preview, original/master protection, feedback state, and explicit human
approval are ready for a final delivery request.

If all technical evidence is present but approval is still missing, the audit
returns `ready_for_human_approval_request` and writes
`automix/review/final_approval_request.md`. The user must still perform the
listening decision.

## Professional Readiness Evidence

When final delivery is requested, the professional readiness audit requires:

- `automix/export/final_render_manifest.json` with an existing primary WAV;
- `automix/eval_reports/final_render_evidence_gate.json` proving the primary
  WAV is a real, non-diagnostic render and not the selected source path itself;
- `automix/export/deliverable_package_manifest.json` with a created ZIP and no
  missing packaged files;
- `automix/eval_reports/deliverable_package_evidence_gate.json` proving the
  ZIP opens cleanly, manifest size matches the file on disk, required evidence
  files are present, and sensitive/raw source paths are not included by default;
- `automix/eval_reports/final_delivery_consistency_gate.json` proving render,
  QC, A/B, final approval, project-state, package, and rollback reports point to
  the same final audio, preview, source stage, and ZIP evidence;
- `automix/export/project_state_manifest.json` confirming original-track and
  master protection;
- `automix/export/plugin_mapping_summary.md` with recorded plugin limitations;
- `automix/eval_reports/final_qc_metrics.json` with measured file integrity,
  loudness, true peak proxy, translation, and artifact-risk metrics;
- `automix/eval_reports/final_qc_evidence_gate.json` proving the QC metrics
  passed and point to the same primary WAV accepted by render evidence;
- `automix/eval_reports/final_ab_preview_manifest.json` with a created
  loudness-matched A/B preview;
- `automix/eval_reports/ab_preview_evidence_gate.json` proving the A/B preview
  has real WAV paths, measured loudness-match evidence, and final-render linkage;
- `automix/eval_reports/final_approval_evidence_gate.json` proving recorded
  human approval references the loudness-matched A/B preview, final audio, and
  final QC evidence;
- `automix/eval_reports/user_feedback_qc_integration.json` when user feedback
  has been recorded;
- `automix/eval_reports/fixture_coverage_audit.json` proving required static
  fixture categories are represented;
- `automix/eval_reports/requirements_traceability_audit.json` mapping the
  project brief to current implementation evidence;
- `automix/eval_reports/open_risk_register.json` with no unresolved delivery
  blockers;
- `automix/eval_reports/risk_root_cause_rollup.json` grouping repeated open
  risks into root causes and next evidence actions when blockers remain;
- `automix/eval_reports/risk_remediation_plan.json` when open risks remain,
  documenting dry-run next actions and disallowed unsafe shortcuts;
- `automix/eval_reports/path_hygiene_audit.json` confirming source code does
  not contain hardcoded local user paths;
- `automix/eval_reports/intent_classification.json` documenting the safe work
  intent route;
- `automix/eval_reports/processing_policy_audit.json` with passing chain-plan
  policy validation;
- `automix/rollback/global_rollback_registry.json` with passing validation.
- `automix/eval_reports/rollback_evidence_gate.json` proving original-track and
  original-master protection plus rollback file integrity.

The rollback registry is treated as delivery evidence, not a cosmetic report.
If it is missing or fails validation, final delivery remains blocked.

The risk root-cause rollup sits between the open risk register and remediation
plan. It compresses repeated blockers into an ordered next root cause so the
operator can clear prerequisite evidence first. It does not approve audio or
replace the source reports.

## Loudness And Peak Verification

The final exported WAV is analyzed again after export. The QC report records
file integrity, sample rate, bit depth, duration, clipping, silence, loudness,
true peak proxy, LRA, phase, low-end stereo risk, vocal harshness, sibilance,
metallic artifact risk, and AI fizz risk. If true peak or loudness cannot be
measured, the limitation is visible and manual check is required.

Run `scripts/run_final_qc_evidence_gate.py` after final QC. The gate checks
that `final_qc_metrics.json` uses the expected schema, `qc_passed` is true,
failures are empty, file-integrity values match the final WAV, true peak stays
within the configured ceiling, and the final audio path matches the final render
evidence. It does not approve audio or replace A/B listening.

## Final Approval Evidence

Run `scripts/run_final_approval_evidence_gate.py` after the operator records
`automix/review/final_human_approval.json`. The approval evidence gate requires
the recorded approval to confirm matched-loudness A/B review, acceptance of the
final audio at matched loudness, the reviewed A/B preview path, the reviewed
final audio path, and final QC evidence review. It does not infer listening
approval from files or metrics.

## Deliverable Package Evidence

Run `scripts/run_deliverable_package_evidence_gate.py` after the final ZIP has
been created. The gate checks `automix/export/deliverable_package_manifest.json`,
opens the ZIP with Python's standard archive reader, verifies the declared
package size, checks required delivery evidence files, validates supporting
render/QC/A-B/approval/rollback gates, and blocks credential-like, raw-stem,
reference, or source-package paths by default. It validates package evidence
only; it does not approve audio or replace final QC, matched-loudness A/B
review, rollback evidence, or human approval.

## Final Delivery Consistency Evidence

Run `scripts/run_final_delivery_consistency_gate.py` after the render, final QC,
A/B preview, approval, rollback, package, and project-state evidence gates have
been generated. The consistency gate cross-checks the final audio path across
render manifest, render evidence, QC metrics, QC evidence, A/B preview, and
approval records; the preview path across A/B and approval evidence; the
approved source/stage against final export state; and the package ZIP/file list
against package evidence. It validates cross-report consistency only. It does
not approve audio or replace measured QC, matched-loudness listening, rollback,
or final human approval.

## Rollback And Chain Plans

Rollback metadata, chain plans, project state manifest, plugin mapping summary,
and prior reports are packaged with final delivery. This keeps the delivery
auditable and prevents false confidence about which plugins or parameters were
actually used.

## Plugin Mapping Summary

`automix/export/plugin_mapping_summary.md` lists plugins, adapter confidence,
semantic controls written, semantic controls skipped, unknown parameters, stock
fallbacks, and limitations. It does not claim MAutoPitch, Decapitator, Valhalla,
TDR Nova, or any third-party plugin was used unless a chain plan explicitly
mapped it.

## Final Recommendation Values

- `ready_for_delivery`: human-approved export, QC passed, package complete.
- `ready_for_review`: export exists but package or review is incomplete.
- `revise_mix`: mix-stage issue blocks final export.
- `revise_premaster`: final QC points to premaster damage or peak issue.
- `export_failed`: render, encoder, file, or QC failure.
- `unsafe_export_blocked`: source is rejected or unresolved.
- `manual_qc_required`: approval or measurable QC is incomplete.

## Running

Diagnostic package:

```sh
python3 scripts/run_final_export_packager.py \
  --project /path/to/project.rpp \
  --profile diagnostic_only \
  --diagnostic-only
```

Approved review/final package from an accepted premaster WAV:

```sh
python3 scripts/run_final_export_packager.py \
  --project /path/to/project.rpp \
  --source-stage accepted_premaster_draft \
  --source-audio /path/to/accepted_premaster.wav \
  --original-mix /path/to/original_mix.wav \
  --profile professional_master_delivery \
  --approve \
  --acknowledge-warnings \
  --render \
  --make-ab-preview \
  --qc \
  --zip
```

Do not mark ready for delivery unless final QC passes and human approval exists.
Run `scripts/run_deliverable_package_evidence_gate.py` after `--zip` and before
`scripts/run_final_delivery_consistency_gate.py`, then run the professional
readiness audit.
