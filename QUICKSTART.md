# Quickstart

Run commands from the workspace root:

```sh
cd "/Users/hantaeheuk/Documents/New project 3"
```

## GitHub / New Computer Bootstrap

Before staging or pushing this workspace, run the source-handoff audit:

```sh
python3 scripts/run_github_upload_readiness.py --project-name reaper-automix --require-ready
```

On a newly cloned computer, use `prompts/new_computer_codex_bootstrap.md` as
the first Codex prompt, then run:

```sh
python3 scripts/run_github_integration_smoke.py --output-dir automix
python3 tools/detect_environment.py
python3 tools/install_reaper_jsfx.py
```

`tools/install_reaper_jsfx.py` is dry-run unless `--apply` is passed. After
copying JSFX files, restart or rescan REAPER.

If REAPER is available, run the inventory-only scanner from REAPER's Action
List with `automix/scan_reaper_plugin_inventory.lua`, then continue in the
shell:

```sh
python3 scripts/run_plugin_validation_preflight.py --project-name reaper-automix --output-dir automix
python3 tools/build_asset_manifest.py
python3 tools/run_reaper_pipeline.py --prepare
```

This bootstrap is trace-first and review-first. It can detect environment and
visible plugin families, but it does not treat plugin presence as proof of
semantic parameter write safety or finished audio quality.

## 0. Compact Context For Normal Mix Turns

Before a normal revision turn, refresh the compact context instead of pasting a
long goal prompt:

```sh
python3 scripts/run_compact_mix_context.py --project-name project
```

Then use `prompts/mix_master_compact_run_card.md` plus
`work/state/RUN_CONTEXT.compact.json` as the default run prompt. Open longer
runbooks only for the specific gate being touched.

## 1. Plugin Intelligence

Portable GitHub integration smoke check. The orchestrator runs this as a
dry-run QC/current-state stage, and it can also be run standalone. It does not
open REAPER, write parameters, render audio, or grant live bridge safety:

```sh
python3 scripts/run_github_integration_smoke.py --output-dir automix
```

Run the REAPER inventory first when a REAPER environment is available:

```sh
reaper automix/scan_reaper_plugin_inventory.lua
```

Then run the local audit:

```sh
python3 scripts/run_plugin_intelligence_audit.py \
  --scan \
  --report \
  --dry-run \
  --output-dir automix
```

Check local availability preconditions without opening REAPER or writing any
parameters:

```sh
python3 scripts/run_plugin_validation_preflight.py \
  --project-name project \
  --output-dir automix
```

Unknown or low-confidence plugin mappings must not write parameters.
Plugin files being present is not proof of semantic parameter write safety.

Then audit REAPER-observed semantic validation reports:

```sh
python3 scripts/run_plugin_semantic_validation_gate.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/plugin_semantic_validation_gate.json`, `.md`,
and `automix/review/plugin_semantic_validation_manifest_template.json`.
Validation reports must prove observed semantic parameter response; availability
alone is not enough.

Then convert plugin validation blockers into plugin-level next actions:

```sh
python3 scripts/run_plugin_validation_action_plan.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/plugin_validation_action_plan.json`, `.md`,
and `automix/review/plugin_validation_action_request.md`. It does not open
REAPER or approve parameter writes.

If unavailable plugins remain, create an operator resolution request:

```sh
python3 scripts/run_plugin_availability_resolution_plan.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/plugin_availability_resolution_plan.json`,
`.md`, `automix/review/plugin_availability_resolution_request.md`, and a
disable-manifest template. It does not install plugins or approve fallback
parameter writes.

Build the operator decision package:

```sh
python3 scripts/run_plugin_availability_operator_decision_package.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/plugin_availability_operator_decision_package.json`,
`.md`, `automix/review/plugin_availability_operator_decision_checklist.md`, and
`automix/review/plugin_availability_disable_manifest_candidate.json`. The
candidate manifest is not accepted evidence; it is a draft for explicit operator
acknowledgement.

After an operator creates the accepted disable manifest, validate the decision
evidence:

```sh
python3 scripts/run_plugin_availability_decision_gate.py \
  --project-name project \
  --output-dir automix
```

This reads `automix/review/plugin_availability_disable_manifest.json` and
writes `automix/eval_reports/plugin_availability_decision_gate.json`, `.md`,
and `automix/review/plugin_availability_decision_request.md`. A template is not
accepted evidence, and fallback writes remain blocked until semantic validation
passes.

Then create the REAPER-observed validation collection plan:

```sh
python3 scripts/run_plugin_semantic_validation_collection_plan.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/plugin_semantic_validation_collection_plan.json`,
`.md`, `automix/review/plugin_semantic_validation_collection_request.md`, and a
collection manifest template. It does not open REAPER, write parameters, or
approve audio.

Then package collectable validation jobs into a REAPER runtime queue:

```sh
python3 scripts/run_plugin_semantic_validation_queue.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/plugin_semantic_validation_queue.json`, `.md`,
`automix/review/plugin_semantic_validation_queue_request.md`, and a runtime
manifest template. It still does not open REAPER or grant write safety.

Then build the runtime collection package:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_collection_package.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/plugin_semantic_validation_runtime_collection_package.json`,
`.md`, `automix/review/plugin_semantic_validation_runtime_collection_checklist.md`,
`automix/review/plugin_semantic_validation_runtime_manifest_candidate.json`, and
job-specific report templates under
`automix/review/plugin_semantic_validation_runtime_report_templates/`. These are
not validation evidence and must not be copied into `analysis_reports` as passing
reports.

Then build the REAPER-side raw observation collector:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_collector_package.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/plugin_semantic_validation_runtime_collector_package.json`,
`.md`, `automix/reaper_scripts/collect_plugin_semantic_validation_runtime.lua`,
`automix/reaper_scripts/plugin_semantic_validation_runtime_queue.json`, and
`automix/review/plugin_semantic_validation_runtime_collector_operator_runbook.md`.
The Lua collector writes raw observations only; it does not create passing
validation reports or grant write safety.

Then validate raw runtime observations before report authoring:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_observation_gate.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/plugin_semantic_validation_runtime_observation_gate.json`,
`.md`, `automix/review/plugin_semantic_validation_runtime_observation_request.md`,
and `automix/review/plugin_semantic_validation_runtime_report_authoring_request.md`.
It checks raw collector output only; it does not create validation reports or
grant write safety.

Then verify observation provenance before report authoring:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_observation_provenance_gate.py \
  --project-name project \
  --output-dir automix \
  --require-packet-ready
```

This writes `automix/eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json`
and `.md`. Missing observations keep the gate in packet-ready/pending mode, but
existing observations must match the current queue payload, collector script
version, and optional artifact hashes before manual report authoring.

Then prepare review-only report authoring templates from accepted observations:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_report_authoring_package.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/plugin_semantic_validation_runtime_report_authoring_package.json`,
`.md`, `automix/review/plugin_semantic_validation_runtime_report_authoring_checklist.md`,
and review-only templates under
`automix/review/plugin_semantic_validation_runtime_report_authoring_templates/`.
It does not write `automix/analysis_reports/`, create validation reports, or
grant write safety.

Then validate review-only authored candidate reports before operator promotion:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_report_authoring_gate.py \
  --project-name project \
  --output-dir automix
```

This reads candidates under
`automix/review/plugin_semantic_validation_runtime_report_authoring_candidates/`
and writes `automix/eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.json`,
`.md`, `automix/review/plugin_semantic_validation_runtime_report_promotion_checklist.md`,
and `automix/review/plugin_semantic_validation_runtime_manifest_candidate_from_authoring.json`.
Candidate reports are review-only; this gate does not promote them into
`analysis_reports`, make them runtime evidence, or grant write safety.

Then validate runtime evidence after the queue has been run in REAPER:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_evidence_gate.py \
  --project-name project \
  --output-dir automix
```

This reads `automix/review/plugin_semantic_validation_runtime_manifest.json`,
checks queued `plugin_parameter_validation_*.json` reports, and writes
`automix/eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`,
`.md`, and `automix/review/plugin_semantic_validation_runtime_evidence_request.md`.
It still keeps `safe_to_write_parameters=false`; rerun the semantic validation
gate before any write-safety decision.

## 2. Smoke Validation

Before real project work:

```sh
python3 scripts/run_prompt41_smoke_validation.py \
  --generate-fixtures \
  --run-tests \
  --mock-render \
  --output-dir automix
```

## 3. Fixture Coverage Audit

Confirm that the synthetic audio and mock analysis fixtures cover the required
failure and safety scenarios:

```sh
python3 scripts/run_fixture_coverage_audit.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/fixture_coverage_audit.json` and `.md`.
It is a fixture coverage check only, not an audio-quality claim.

## 4. Requirements Traceability Audit

Map the project brief requirements to current code, docs, tests, and reports:

```sh
python3 scripts/run_requirements_traceability_audit.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/requirements_traceability_audit.json` and
`.md`. It proves implementation evidence exists, not that a rendered master has
been accepted by a listener.

## 5. Open Risk Register

Summarize open blockers, warnings, review items, and safe next actions:

```sh
python3 scripts/run_open_risk_register.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/open_risk_register.json` and `.md`.
It is an operator risk summary, not an audio-quality claim.

## 6. Risk Remediation Plan

Convert open risks into dry-run next actions and required evidence:

```sh
python3 scripts/run_risk_root_cause_rollup.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/risk_root_cause_rollup.json` and `.md`.
It compresses repeated blockers into root causes and does not approve audio.

```sh
python3 scripts/run_risk_remediation_plan.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/risk_remediation_plan.json` and `.md`.
It does not apply FX or accept a render.

## 7. Path Hygiene Audit

Check source code, fixtures, and generated reports for hardcoded local paths:

```sh
python3 scripts/run_path_hygiene_audit.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/path_hygiene_audit.json` and `.md`.
Source-code local paths are blockers; runtime report paths are audit evidence.

## 8. Scan Only

```sh
python3 scripts/run_automix_orchestrator.py \
  --mode scan_only \
  --output-dir automix \
  --dry-run
```

For a real REAPER project:

```sh
python3 scripts/run_real_project_scan_only.py \
  --project "/path/to/project.rpp" \
  --target-profile digicore_hyperpop_hiphop_vocal_forward \
  --check-prompt41 \
  --strict-read-only \
  --dry-run
```

Then build the source/stem handoff readiness report:

```sh
python3 scripts/run_source_handoff_readiness.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/source_handoff_readiness.json` and
`automix/review/source_stem_handoff_request.md`. Existing source files are not
treated as accepted export sources.

## 9. Source Acceptance Gate

After the user provides an accepted premaster/reviewed draft WAV or requested
isolated stems, validate the acceptance evidence before final export packaging:

```sh
python3 scripts/run_source_acceptance_gate.py \
  --project-name project \
  --output-dir automix
```

To check one reviewed premaster candidate:

```sh
python3 scripts/run_source_acceptance_gate.py \
  --project-name project \
  --output-dir automix \
  --source-audio /path/to/accepted_premaster.wav \
  --source-stage accepted_premaster_draft \
  --source-role premaster \
  --source-classification accepted_premaster_render \
  --human-accepted \
  --require-ready
```

This writes `automix/eval_reports/source_acceptance_gate.json`, `.md`, and
`automix/review/source_acceptance_manifest_template.json`. It does not update
final export state or invent user acceptance.

## 10. Intent Classification

After scan reports exist, classify the safe work intent:

```sh
python3 scripts/run_intent_classifier.py \
  --project-name project \
  --output-dir automix \
  --target-profile digicore_hyperpop_hiphop_vocal_forward
```

This writes `automix/eval_reports/intent_classification.json` and `.md`.
It is report-only and does not apply FX.

## 11. Artifact Evidence Gate

Before artifact-focused work, validate whether source, metric, or feedback
evidence is usable and whether measured artifact metrics come from real
render/QC reports:

```sh
python3 scripts/run_artifact_evidence_gate.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/artifact_evidence_gate.json`, `.md`, and
`automix/review/artifact_evidence_manifest_template.json`. It does not process
audio or claim cleanup.

## 12. Artifact Signal Audit

Check whether artifact-focused work has source, metric, or user-feedback
evidence:

```sh
python3 scripts/run_artifact_signal_audit.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/artifact_signal_audit.json` and `.md`.
Missing or zero metrics are insufficient evidence, not proof that artifacts are
absent.

## 13. Processing Policy Audit

After chain plans exist, audit them before any application:

```sh
python3 scripts/run_processing_policy_audit.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/processing_policy_audit.json` and `.md`.
It blocks unsafe plan shapes such as non-draft application, original-master
limiting, OTT-style processing, aggressive saturation, blind widening, or
dry/wet values above the conservative cap.

## 14. Recovery Review

Create recovery-only drafts only after plugin and source gates allow it:

```sh
python3 scripts/run_recovery_only_pilot.py \
  --project "/path/to/project.rpp" \
  --from-scan-report automix/eval_reports/real_project_scan_only_report.md \
  --dry-run
```

Then create the review form:

```sh
python3 scripts/run_recovery_review_gate.py \
  --project "/path/to/project.rpp" \
  --generate-form
```

## 15. Feedback Loop

Initialize the no-feedback baseline before handoff or readiness audits when no
listening notes have been recorded yet:

```sh
python3 scripts/run_feedback_revision_loop.py \
  --output-dir automix \
  --project-name project \
  --initialize-baseline
```

This creates an explicit audit marker only. It does not invent user feedback or
prove a listening review happened.

Record user feedback before the next pass:

```sh
python3 scripts/run_feedback_revision_loop.py \
  --output-dir automix \
  --project-name project \
  --pass-id v01 \
  --track-name "Lead Vocal" \
  --feedback "보컬이 뿌옇고 Suno fizz가 남아 있다."
```

Resolve a feedback blocker only with evidence:

```sh
python3 scripts/run_feedback_revision_loop.py \
  --output-dir automix \
  --project-name project \
  --pass-id v02 \
  --resolve-feedback-id feedback_ID_HERE \
  --resolution-notes "Measured QC and loudness-matched A/B review passed." \
  --evidence-path automix/eval_reports/final_qc_metrics.json \
  --human-reviewed \
  --measured-qc-passed \
  --loudness-matched-ab-reviewed
```

The feedback command also writes
`automix/eval_reports/user_feedback_qc_integration.json` and `.md`, linking the
feedback to planned actions, QC metric snapshots, A/B review status, and
remaining risks.

## 16. Final Render Evidence Gate

After a final render manifest exists, verify that the primary WAV is a real
non-diagnostic render before QC or approval readiness:

```sh
python3 scripts/run_final_render_evidence_gate.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/final_render_evidence_gate.json`, `.md`,
`automix/review/final_render_evidence_manifest_template.json`, and
`automix/review/final_render_evidence_request.md`. It does not approve audio or
replace final QC.

## 17. Final QC Evidence Gate

After `automix/eval_reports/final_qc_metrics.json` exists, verify that the
metrics are tied to the same primary WAV accepted by final render evidence:

```sh
python3 scripts/run_final_qc_evidence_gate.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/final_qc_evidence_gate.json`, `.md`,
`automix/review/final_qc_evidence_manifest_template.json`, and
`automix/review/final_qc_evidence_request.md`. It does not approve audio or
replace loudness-matched A/B review.

## 18. A/B Preview Evidence Gate

After creating a final A/B preview, verify that it is reviewable, loudness
matched with measured RMS evidence, and linked to the final render:

```sh
python3 scripts/run_ab_preview_evidence_gate.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/ab_preview_evidence_gate.json`, `.md`,
`automix/review/ab_preview_review_manifest_template.json`, and
`automix/review/ab_preview_review_request.md`. It does not record listening
approval.

## 19. Final Approval Evidence Gate

After the operator records final human approval, verify that the approval record
references the loudness-matched A/B preview, final audio, and final QC evidence:

```sh
python3 scripts/run_final_approval_evidence_gate.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/final_approval_evidence_gate.json`, `.md`,
`automix/review/final_approval_evidence_manifest_template.json`, and
`automix/review/final_approval_evidence_request.md`. It does not approve audio;
it only checks that recorded approval is auditable.

## 20. Approval Export Readiness

Before asking for final approval or delivery, validate rollback evidence:

```sh
python3 scripts/run_rollback_evidence_gate.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/rollback_evidence_gate.json`, `.md`,
`automix/review/rollback_evidence_manifest_template.json`, and
`automix/review/rollback_evidence_request.md`.

Then summarize accepted source, render, final QC, A/B preview, final approval,
rollback, project-state, feedback, and approval evidence:

```sh
python3 scripts/run_approval_export_readiness.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/approval_export_readiness.json`, `.md`, and
`automix/review/final_approval_request.md`. It does not approve audio or infer
user acceptance.

## 21. Final Export

Final export requires accepted source, approval, QC, and no unresolved feedback:

```sh
python3 scripts/run_final_export_packager.py \
  --project "/path/to/project.rpp" \
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

If any gate is incomplete, the correct result is a review or blocked state.

## 22. Deliverable Package Evidence Gate

After the delivery ZIP is created, verify that the package manifest, ZIP
integrity, required evidence files, project-state protection, and supporting
gates are auditable:

```sh
python3 scripts/run_deliverable_package_evidence_gate.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/deliverable_package_evidence_gate.json`,
`.md`, `automix/review/deliverable_package_evidence_manifest_template.json`,
and `automix/review/deliverable_package_evidence_request.md`. It does not
approve audio or replace final QC, A/B review, rollback evidence, or human
approval.

## 23. Final Delivery Consistency Gate

After render, QC, A/B, approval, rollback, and package evidence exist, verify
that they all point to the same final audio, preview, source, stage, and ZIP:

```sh
python3 scripts/run_final_delivery_consistency_gate.py \
  --project-name project \
  --output-dir automix
```

This writes `automix/eval_reports/final_delivery_consistency_gate.json`, `.md`,
`automix/review/final_delivery_consistency_manifest_template.json`, and
`automix/review/final_delivery_consistency_request.md`. It does not approve
audio or replace measured QC, matched-loudness A/B listening, rollback
evidence, final approval, or package evidence.

## 24. Professional Readiness Audit

Before treating a package as delivery-ready:

```sh
python3 scripts/run_professional_readiness_audit.py \
  --project-name project \
  --output-dir automix \
  --final-delivery-requested
```

The command returns nonzero when required evidence is missing or unsafe.
Required final-delivery evidence includes the primary WAV render, delivery ZIP,
deliverable package evidence gate, final delivery consistency gate, final render
evidence gate, project state manifest, plugin mapping summary, loudness-matched
A/B preview and A/B evidence gate, rollback registry and rollback evidence gate,
QC reports, approval, and resolved feedback memory. It also reads fixture
coverage, requirements traceability, open risk register, path hygiene, and risk
remediation evidence.
