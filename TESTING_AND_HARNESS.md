# Testing And Harness

The harness separates static/unit validation from REAPER integration.

## REAPER-Free Tests

Focused harness checks after changing routing, plugin policy, or JSFX:

```sh
python3 -m pytest \
  tests/test_plugin_trace_schema.py \
  tests/test_routing_rules.py \
  tests/test_no_raw_full_mix_active.py \
  tests/test_reference_not_in_master.py \
  tests/test_install_reaper_jsfx.py \
  tests/test_vocal_ai_artifact_split_tamer_jsfx.py
```

## Current Approved Mwolla Harness

The current user-approved `mwolla` baseline is
`mwolla_v14_no_chop_max_clarity_hook_reprise_master`. It is recorded as a
pipeline/harness fixture rather than a generic target preset because the user's
approval applies to this exact source, arrangement, render, and QC evidence.

Verify the approved files and gates without rerendering:

```sh
python3 tools/mwolla_current_approved_master.py --verify-existing
```

Rerender the approved baseline from the deterministic v14 script:

```sh
python3 tools/mwolla_current_approved_master.py --render
```

Required evidence files:

- `reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/approved_baseline_manifest.json`
- `reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/qc_summary.json`
- `reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/no_chop_timestamp_qc.json`
- `reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/hook_reprise_qc.json`
- `reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/actual_reaper_plugin_trace.json`

The approved regression guards are no phrase chop, no PREMASTER loudness push,
hook reprise preserved at `54.0-70.0s`, first-slot
`JS: Codex Vocal AI Artifact Split Tamer` on `10 MAIN_VOCAL_CENTER`, muted full
mix/reference routing, and `MAIN_VOCAL_BUS -> MUSIC_BUS` sidechain as `1/2 ->
3/4`.

Run focused tests:

```sh
python3 -m pytest \
  tests/test_prompt37_final_export_packaging.py \
  tests/test_prompt40_automix_orchestrator.py \
  tests/test_prompt45_user_feedback_revision_loop.py \
  tests/test_prompt46_professional_docs.py \
  tests/test_prompt47_professional_readiness_audit.py \
  tests/test_prompt48_intent_classification.py \
  tests/test_prompt49_processing_policy_audit.py \
  tests/test_prompt50_fixture_coverage_audit.py \
  tests/test_prompt51_requirements_traceability_audit.py \
  tests/test_prompt52_open_risk_register.py \
  tests/test_prompt53_risk_remediation_plan.py \
  tests/test_prompt54_path_hygiene_audit.py \
  tests/test_prompt55_plugin_validation_preflight.py \
  tests/test_prompt56_source_handoff_readiness.py \
  tests/test_prompt57_artifact_signal_audit.py \
  tests/test_prompt58_approval_export_readiness.py \
  tests/test_prompt59_source_acceptance_gate.py \
  tests/test_prompt60_plugin_semantic_validation_gate.py \
  tests/test_prompt61_artifact_evidence_gate.py \
  tests/test_prompt62_ab_preview_evidence_gate.py \
  tests/test_prompt63_final_render_evidence_gate.py \
  tests/test_prompt64_rollback_evidence_gate.py \
  tests/test_prompt65_final_qc_evidence_gate.py \
  tests/test_prompt66_final_approval_evidence_gate.py \
  tests/test_prompt67_deliverable_package_evidence_gate.py \
  tests/test_prompt68_final_delivery_consistency_gate.py \
  tests/test_prompt69_risk_root_cause_rollup.py \
  tests/test_prompt70_plugin_validation_action_plan.py \
  tests/test_prompt71_plugin_availability_resolution_plan.py \
  tests/test_prompt77_plugin_availability_operator_decision_package.py \
  tests/test_prompt83_plugin_availability_operator_decision_firewall_gate.py \
  tests/test_prompt72_plugin_availability_decision_gate.py \
  tests/test_prompt73_plugin_semantic_validation_collection_plan.py \
  tests/test_prompt74_plugin_semantic_validation_queue.py \
  tests/test_prompt75_plugin_semantic_validation_runtime_evidence_gate.py \
  tests/test_prompt76_plugin_semantic_validation_runtime_collection_package.py \
  tests/test_prompt78_plugin_semantic_validation_runtime_collector_package.py \
  tests/test_prompt79_plugin_semantic_validation_runtime_observation_gate.py \
  tests/test_prompt84_plugin_semantic_validation_runtime_observation_provenance_gate.py \
  tests/test_prompt80_plugin_semantic_validation_runtime_report_authoring_package.py \
  tests/test_prompt81_plugin_semantic_validation_runtime_report_authoring_gate.py \
  tests/test_prompt82_plugin_semantic_validation_runtime_handoff_packet_gate.py \
  tests/test_public_pc_handoff_package_audit.py \
  tests/test_public_pc_legacy_semantic_firewall_gate.py \
  tests/automix_validation/test_prompt41_export_blocking.py
```

Prompt 41 validation:

```sh
python3 scripts/run_prompt41_smoke_validation.py \
  --generate-fixtures \
  --run-tests \
  --mock-render \
  --output-dir automix
```

Fixture coverage audit:

```sh
python3 scripts/run_fixture_coverage_audit.py \
  --project-name project \
  --output-dir automix
```

Local device QC:

```sh
python3 scripts/run_local_device_qc.py \
  --project-name project \
  --output-dir automix \
  --require-local-ready
```

REAPER runtime collector safety audit:

```sh
python3 scripts/run_reaper_runtime_collector_safety_audit.py \
  --project-name project \
  --output-dir automix \
  --require-passed
```

`run_plugin_semantic_validation_runtime_collector_package.py` also writes this
safety audit by default after regenerating the Lua collector; rerun the command
above whenever the collector or queue is edited manually.

REAPER runtime collection operator readiness:

```sh
python3 scripts/run_reaper_runtime_collection_operator_readiness_gate.py \
  --project-name project \
  --output-dir automix \
  --require-partial-ready
```

Plugin semantic validation runtime handoff packet:

```sh
python3 scripts/run_plugin_semantic_validation_runtime_handoff_packet_gate.py \
  --project-name project \
  --output-dir automix \
  --require-partial-ready
```

Mix/master quality harness from the extracted REAPER handoff package:

```sh
python3 scripts/run_mix_master_quality_harness.py \
  --project-name project \
  --output-dir automix \
  --handoff-root "$REAPER_AUTOMIX_HANDOFF_ROOT"
```

Public-PC handoff package audit:

```sh
python3 scripts/run_public_pc_handoff_package_audit.py \
  --project-name project \
  --output-dir automix \
  --bundle-path "$PUBLIC_PC_HANDOFF_BUNDLE" \
  --require-ready
```

Public-PC legacy fixture plan:

```sh
python3 scripts/run_public_pc_legacy_fixture_plan.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

Public-PC legacy API regression gate:

```sh
python3 scripts/run_public_pc_legacy_api_regression_gate.py \
  --project-name project \
  --output-dir automix \
  --require-passed
```

Public-PC legacy semantic firewall gate:

```sh
python3 scripts/run_public_pc_legacy_semantic_firewall_gate.py \
  --project-name project \
  --output-dir automix \
  --require-passed
```

Requirements traceability audit:

```sh
python3 scripts/run_requirements_traceability_audit.py \
  --project-name project \
  --output-dir automix
```

Open risk register:

```sh
python3 scripts/run_open_risk_register.py \
  --project-name project \
  --output-dir automix
```

Risk remediation plan:

```sh
python3 scripts/run_risk_root_cause_rollup.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_risk_remediation_plan.py \
  --project-name project \
  --output-dir automix
```

Path hygiene audit:

```sh
python3 scripts/run_path_hygiene_audit.py \
  --project-name project \
  --output-dir automix
```

Plugin validation preflight:

```sh
python3 scripts/run_plugin_validation_preflight.py \
  --project-name project \
  --output-dir automix
```

Plugin semantic validation gate:

```sh
python3 scripts/run_plugin_semantic_validation_gate.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_validation_action_plan.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_availability_resolution_plan.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_availability_operator_decision_package.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_availability_operator_decision_firewall_gate.py \
  --project-name project \
  --output-dir automix \
  --require-passed

python3 scripts/run_plugin_availability_decision_gate.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_semantic_validation_collection_plan.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_semantic_validation_queue.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_semantic_validation_runtime_collection_package.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_semantic_validation_runtime_collector_package.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_semantic_validation_runtime_observation_gate.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_semantic_validation_runtime_observation_provenance_gate.py \
  --project-name project \
  --output-dir automix \
  --require-packet-ready

python3 scripts/run_plugin_semantic_validation_runtime_report_authoring_package.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_semantic_validation_runtime_report_authoring_gate.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_plugin_semantic_validation_runtime_evidence_gate.py \
  --project-name project \
  --output-dir automix
```

Source handoff readiness:

```sh
python3 scripts/run_source_handoff_readiness.py \
  --project-name project \
  --output-dir automix
```

Source acceptance gate:

```sh
python3 scripts/run_source_acceptance_gate.py \
  --project-name project \
  --output-dir automix
```

Artifact signal audit:

```sh
python3 scripts/run_artifact_evidence_gate.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_artifact_signal_audit.py \
  --project-name project \
  --output-dir automix
```

A/B preview evidence gate:

```sh
python3 scripts/run_final_render_evidence_gate.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_final_qc_evidence_gate.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_ab_preview_evidence_gate.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_final_approval_evidence_gate.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_deliverable_package_evidence_gate.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_final_delivery_consistency_gate.py \
  --project-name project \
  --output-dir automix

python3 scripts/run_rollback_evidence_gate.py \
  --project-name project \
  --output-dir automix
```

Approval export readiness:

```sh
python3 scripts/run_approval_export_readiness.py \
  --project-name project \
  --output-dir automix
```

## What Static Tests Cover

- crash-free planning;
- no original overwrite in scan-only paths;
- full-mix pitch blocking;
- plugin mapping fail-closed behavior;
- fixture coverage for clean/buried/muddy/harsh/sibilant vocals, Suno fizz,
  watery smear, fake stereo halo, over-limited master, low-end buildup, phase
  issue, missing plugin, corrupted config, dry-run, rollback, render failure,
  and feedback mapping;
- requirements traceability for non-destructive safety, conservative
  processing, Suno/AI artifact strategy, vocal-first policy, feedback loop,
  source intake, diagnosis, intent, plugin safety, A/B render, mastering QC,
  documentation, and delivery readiness evidence;
- open risk register consolidation of blockers, warnings, review items, source
  risks, plugin mapping risks, final-export blockers, and safe next actions;
- risk remediation planning that turns open risks into dry-run commands,
  required evidence, acceptance criteria, and disallowed unsafe actions;
- risk root-cause rollup that compresses repeated open-risk blockers into
  ordered root causes and next evidence actions without approving audio;
- path hygiene scanning for hardcoded local paths in source code, fixture
  manifests, and generated runtime reports;
- local device QC that checks REAPER, stock FX, required JSFX, audio-QC command
  availability, REAPER app metadata, local file fingerprints, render inventory,
  and existing gate readiness without opening REAPER or writing parameters;
- REAPER runtime collector safety auditing that statically rejects generated
  Lua collectors with parameter-write, save, render, or broad mutation APIs
  while documenting the allowed temporary muted probe-track mutation model;
- REAPER runtime collection operator readiness gating that separates partial
  collectable-job readiness from complete readiness blocked by unavailable
  plugin decisions, without opening REAPER or granting write safety;
- plugin semantic validation runtime handoff packet gating that checks the Lua
  collector, queue payload, observation template, report templates, manifest
  candidate, runbook, local QC, and safety audit before operator collection;
- public-PC handoff package auditing that treats older shared-computer REAPER
  code, recipes, docs, and validation notes as targeted development evidence
  while blocking direct code merge, runtime audio QC, and delivery claims;
- public-PC legacy fixture planning that fingerprints older Lua/recipe/review
  files, separates read-only regression fixture use from direct merge or
  execution, and flags legacy REAPER mutation calls as review evidence;
- public-PC legacy API regression gating that checks older REAPER Lua mutation
  calls against the current disallowed API policy so historical risks become
  negative safety fixtures instead of executable automation;
- public-PC legacy semantic firewall gating that checks legacy paths and hashes
  cannot be counted as plugin semantic validation evidence or analysis reports;
- plugin validation preflight that separates local plugin availability from
  semantic parameter write safety;
- plugin semantic validation gate checks that parameter validation reports are
  passed, no-fake-success, and include observed write-safe controls;
- plugin validation action planning that turns availability and semantic
  validation blockers into plugin-level install, disable, or validation-report
  requests without approving parameter writes;
- plugin availability resolution planning that writes operator install/disable
  requests and a disable-manifest template for unavailable plugins without
  treating fallback text as validation;
- plugin availability operator decision firewall gating that verifies candidate
  manifests cannot count as accepted operator evidence before acknowledgement;
- plugin runtime report authoring packaging that turns accepted raw
  observations into review-only templates without writing analysis reports or
  approving parameter writes;
- plugin runtime report authoring gate validation that checks review-only
  candidate reports before operator promotion without writing analysis reports
  or granting write safety;
- source handoff readiness that separates current source-file presence from
  accepted export source or isolated stem evidence;
- source acceptance gate validation that requires explicit user acceptance and
  rejects full-mix/reference material as automatic processing input;
- artifact evidence gate validation that rejects report-only metrics and keeps
  source/feedback evidence separate from measured render/QC metrics;
- artifact signal audit that treats missing or zero metrics as insufficient
  evidence instead of proof that artifacts are absent;
- final render evidence gate validation that rejects diagnostic/report-only
  manifests, missing primary WAV files, hidden limiter/normalization flags, and
  render paths that point back to the selected source;
- final QC evidence gate validation that requires passing measured QC metrics,
  true-peak ceiling evidence, file-integrity checks, and primary-WAV render
  linkage before approval readiness;
- A/B preview evidence gate validation that requires real preview/source/final
  WAV paths, measured loudness-match metrics, and final-render linkage before
  approval readiness;
- final approval evidence gate validation that requires the recorded human
  approval to reference matched-loudness A/B review, final audio, and final QC
  evidence before delivery request;
- deliverable package evidence gate validation that requires a readable ZIP,
  matching package size, no missing packaged files, required evidence files,
  ready supporting gates, original/master protection, and no credential/raw
  source paths in the package manifest;
- final delivery consistency gate validation that cross-checks selected source,
  render, QC, A/B preview, final approval, package, project-state, and rollback
  evidence paths before professional delivery readiness;
- rollback evidence gate validation that requires original-track/master
  protection, passed rollback validation, existing rollback files, and safe
  rollback entries before delivery readiness;
- approval export readiness that checks accepted source, render, A/B preview,
  project-state, feedback, and explicit human approval evidence without
  inventing approval;
- intent classification fail-closed routing;
- processing policy audit blockers for unsafe chain plans;
- rollback metadata expectations;
- final export approval and QC blocking;
- final render, ZIP package, project-state, A/B preview, plugin summary, and
  rollback evidence blockers;
- unresolved feedback blocking;
- evidence-gated feedback resolution;
- feedback-QC integration report coverage for cause hypotheses, planned
  actions, metric snapshots, A/B state, and remaining risks;
- no-feedback baseline initialization that writes explicit audit evidence
  without fabricating a listening review;
- professional readiness audit blockers and pass conditions;
- unsafe claim-language detection in delivery reports.

## REAPER Integration Tests

REAPER integration must run only on saved project copies. Runtime applicators
must verify original track state after changes and write rollback metadata.

## Manual Review

No test replaces user listening. A/B review must be loudness matched wherever
possible, and limitations must be reported.
