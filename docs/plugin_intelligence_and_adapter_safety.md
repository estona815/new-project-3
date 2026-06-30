# Plugin Intelligence And Adapter Safety

Prompt39 adds a non-destructive plugin intelligence layer for the REAPER
AutoMix / Auto-FX Orchestrator.

This layer does not process audio, insert FX, render, load presets, or write
plugin parameters. Its job is to decide whether later automation is allowed to
touch a plugin at all.

## Workflow

1. Run the existing inventory scanner in REAPER when available:

   ```bash
   # inside REAPER: run automix/scan_reaper_plugin_inventory.lua
   ```

2. Run the Python audit:

   ```bash
   python3 scripts/run_plugin_intelligence_audit.py --scan --report --dry-run --output-dir automix
   ```

3. Optional adapter learning from a parameter list:

   ```bash
   python3 scripts/run_plugin_intelligence_audit.py --learn --plugin "Plugin Name" --parameters-json params.json --dry-run --output-dir automix
   ```

4. Validation remains fail-closed unless a later REAPER runtime harness proves
   plugin availability and semantic parameter response:

   ```bash
   python3 scripts/run_plugin_intelligence_audit.py --validate --all --dry-run --output-dir automix
   ```

5. Audit the resulting semantic validation reports before any parameter write:

   ```bash
   python3 scripts/run_plugin_semantic_validation_gate.py --project-name project --output-dir automix
   ```

   This writes `automix/eval_reports/plugin_semantic_validation_gate.json` and
   a request/template under `automix/review/`. A report must be `passed`,
   `safe_for_automix=true`, `no_fake_success=true`, and include at least one
   validated write-safe semantic control.

6. Convert remaining plugin blockers into plugin-level next actions:

   ```bash
   python3 scripts/run_plugin_validation_action_plan.py --project-name project --output-dir automix
   ```

   This writes `automix/eval_reports/plugin_validation_action_plan.json`,
   `.md`, and `automix/review/plugin_validation_action_request.md`. It keeps
   unavailable plugins, missing reports, and failed reports as blockers until
   observed validation evidence exists or the plugin is disabled.

7. For unavailable plugins, create an operator install/disable request:

   ```bash
   python3 scripts/run_plugin_availability_resolution_plan.py --project-name project --output-dir automix
   ```

   This writes `automix/eval_reports/plugin_availability_resolution_plan.json`,
   `.md`, `automix/review/plugin_availability_resolution_request.md`, and
   `automix/review/plugin_availability_disable_manifest_template.json`.
   Fallback suggestions are planning context only and require semantic
   validation before parameter writes.

8. Build the operator decision package:

   ```bash
   python3 scripts/run_plugin_availability_operator_decision_package.py --project-name project --output-dir automix
   ```

   This writes `automix/eval_reports/plugin_availability_operator_decision_package.json`,
   `.md`, `automix/review/plugin_availability_operator_decision_checklist.md`,
   and `automix/review/plugin_availability_disable_manifest_candidate.json`.
   The candidate manifest is not accepted evidence; it is only a draft for
   explicit operator acknowledgement.

9. After an operator writes the accepted disable manifest, validate it:

   ```bash
   python3 scripts/run_plugin_availability_decision_gate.py --project-name project --output-dir automix
   ```

   This reads `automix/review/plugin_availability_disable_manifest.json` and
   writes `automix/eval_reports/plugin_availability_decision_gate.json`, `.md`,
   and `automix/review/plugin_availability_decision_request.md`. The template
   manifest is not accepted evidence; fallback writes remain blocked until
   semantic validation reports pass.

10. Create the REAPER-observed semantic validation collection plan:

   ```bash
   python3 scripts/run_plugin_semantic_validation_collection_plan.py --project-name project --output-dir automix
   ```

   This writes `automix/eval_reports/plugin_semantic_validation_collection_plan.json`,
   `.md`, `automix/review/plugin_semantic_validation_collection_request.md`, and
   a collection manifest template. It translates missing or failed semantic
   validation into REAPER-observed report collection jobs without granting write
   safety.

11. Package collectable semantic validation jobs into a runtime queue:

   ```bash
   python3 scripts/run_plugin_semantic_validation_queue.py --project-name project --output-dir automix
   ```

   This writes `automix/eval_reports/plugin_semantic_validation_queue.json`,
   `.md`, `automix/review/plugin_semantic_validation_queue_request.md`, and
   `automix/review/plugin_semantic_validation_runtime_manifest_template.json`.
   Queue jobs must be run only in a saved test copy or temporary muted test
   context, and the resulting validation reports must be audited again.

12. Build the runtime collection package:

   ```bash
   python3 scripts/run_plugin_semantic_validation_runtime_collection_package.py --project-name project --output-dir automix
   ```

   This writes `automix/eval_reports/plugin_semantic_validation_runtime_collection_package.json`,
   `.md`, `automix/review/plugin_semantic_validation_runtime_collection_checklist.md`,
   `automix/review/plugin_semantic_validation_runtime_manifest_candidate.json`,
   and report templates under
   `automix/review/plugin_semantic_validation_runtime_report_templates/`. These
   templates are not passing validation evidence and must stay out of
   `automix/analysis_reports/` unless replaced by real REAPER-observed reports.

13. Build the REAPER-side raw observation collector:

   ```bash
   python3 scripts/run_plugin_semantic_validation_runtime_collector_package.py --project-name project --output-dir automix
   ```

   This writes `automix/eval_reports/plugin_semantic_validation_runtime_collector_package.json`,
   `.md`, `automix/reaper_scripts/collect_plugin_semantic_validation_runtime.lua`,
   `automix/reaper_scripts/plugin_semantic_validation_runtime_queue.json`, and
   `automix/review/plugin_semantic_validation_runtime_collector_operator_runbook.md`.
   The collector writes raw observations only; it does not create passing
   validation reports or grant write safety.

14. Validate raw runtime observations before manual report authoring:

   ```bash
   python3 scripts/run_plugin_semantic_validation_runtime_observation_gate.py --project-name project --output-dir automix
   ```

   This writes `automix/eval_reports/plugin_semantic_validation_runtime_observation_gate.json`,
   `.md`, `automix/review/plugin_semantic_validation_runtime_observation_request.md`,
   and `automix/review/plugin_semantic_validation_runtime_report_authoring_request.md`.
   It checks raw collector output only; it does not create validation reports or
   grant write safety.

15. Verify raw observation provenance before manual report authoring:

   ```bash
   python3 scripts/run_plugin_semantic_validation_runtime_observation_provenance_gate.py --project-name project --output-dir automix --require-packet-ready
   ```

   This writes `automix/eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json`
   and `.md`. Missing observations do not fail the prepared packet, but existing
   observations must match the current queue payload, collector script version,
   and optional artifact hashes before they can support manual report authoring.

16. Prepare review-only report authoring templates from accepted observations:

   ```bash
   python3 scripts/run_plugin_semantic_validation_runtime_report_authoring_package.py --project-name project --output-dir automix
   ```

   This writes `automix/eval_reports/plugin_semantic_validation_runtime_report_authoring_package.json`,
   `.md`, `automix/review/plugin_semantic_validation_runtime_report_authoring_checklist.md`,
   and templates under
   `automix/review/plugin_semantic_validation_runtime_report_authoring_templates/`.
   The templates are not validation evidence, are not written to
   `automix/analysis_reports/`, and do not grant write safety.

17. Validate review-only authored candidate reports before operator promotion:

   ```bash
   python3 scripts/run_plugin_semantic_validation_runtime_report_authoring_gate.py --project-name project --output-dir automix
   ```

   This checks candidates under
   `automix/review/plugin_semantic_validation_runtime_report_authoring_candidates/`
   and writes `automix/eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.json`,
   `.md`, `automix/review/plugin_semantic_validation_runtime_report_promotion_checklist.md`,
   and `automix/review/plugin_semantic_validation_runtime_manifest_candidate_from_authoring.json`.
   It does not promote candidates into `automix/analysis_reports/`, make them
   runtime evidence, or grant write safety.

18. Validate runtime evidence for the queued reports:

   ```bash
   python3 scripts/run_plugin_semantic_validation_runtime_evidence_gate.py --project-name project --output-dir automix
   ```

   This reads `automix/review/plugin_semantic_validation_runtime_manifest.json`,
   checks each queued validation report, and writes
   `automix/eval_reports/plugin_semantic_validation_runtime_evidence_gate.json`,
   `.md`, and `automix/review/plugin_semantic_validation_runtime_evidence_request.md`.
   It does not open REAPER and keeps automatic parameter writes blocked until a
   follow-up semantic validation gate pass confirms write-safe controls.

## Safety Rules

- A fuzzy plugin name match is inventory evidence only, not write permission.
- Third-party plugins are optional and never required.
- Missing commercial plugins are normal.
- Learned adapters are provisional and start with `write_allowed=false`.
- Unknown parameters are skipped.
- `do_not_touch` parameters such as bypass, preset, random, MIDI, license,
  oversampling, and quality controls are not written by the safe writer.
- Generated presets are saved only under
  `automix/plugins/generated_presets/`.
- User preset folders are never overwritten.

## Adapter States

- `unmapped`: plugin may be listed, but it is unsafe for automated control.
- `mapped_unvalidated`: an adapter exists, but validation did not pass.
- `validated_safe`: availability, semantic mapping, safe range, and write
  permission passed.

Only `validated_safe` adapters may be used by `safe_parameter_writer.py`.

## Gate Reason Codes

Common gate failures include:

- `PLUGIN_NOT_DETECTED`
- `ADAPTER_MISSING`
- `ADAPTER_CONFIDENCE_LOW`
- `VALIDATION_MISSING`
- `SEMANTIC_CONTROL_MISSING`
- `SEMANTIC_CONTROL_NOT_WRITE_ALLOWED`
- `THIRD_PARTY_POLICY_BLOCKED`
- `FALLBACK_REQUIRED`

These codes are intentionally conservative. They should make the planner skip a
plugin or choose a stock/manual fallback instead of guessing.

## Current Limitation

This patch does not perform live REAPER parameter validation. If REAPER is not
available from the command line, validation reports must stay
`validation_unavailable`; that is the correct safe result, not a failure of the
safety layer.
