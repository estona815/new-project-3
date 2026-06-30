# Manual Test Plan Prompt81

## Scope

Validate that review-only authored plugin validation report candidates are
checked before operator promotion without writing `automix/analysis_reports/`
or granting parameter write safety.

## Preconditions

- Run `scripts/run_plugin_semantic_validation_runtime_report_authoring_package.py`.
- If accepted raw observations exist, write candidate reports under
  `automix/review/plugin_semantic_validation_runtime_report_authoring_candidates/`.
- Candidate reports must use schema
  `automix-plugin-parameter-validation-report-v1`.

## Command

```sh
python3 scripts/run_plugin_semantic_validation_runtime_report_authoring_gate.py \
  --project-name project \
  --output-dir automix
```

Use `--require-ready` when at least one candidate report is expected.

## Expected Blocked State

- If the authoring package is not ready, status is
  `runtime_report_authoring_package_not_ready`.
- If candidate reports are missing, status is
  `runtime_report_authoring_candidates_missing`.
- `safe_to_write_parameters=false`.
- `writes_analysis_reports=false`.
- `candidate_reports_are_validation_evidence=false`.

## Expected Candidate-Ready State

- Candidate reports contain `status=passed`, `safe_for_automix=true`,
  `no_fake_success=true`, and at least one control with `validated=true`,
  `write_allowed=true`, `confidence>=0.85`, `target_name`, `safe_min`, and
  `safe_max`.
- Gate status is
  `runtime_report_authoring_candidates_ready_for_operator_promotion`.
- No candidate is copied into `automix/analysis_reports/` by this gate.

## Follow-Up

Operator promotion requires manually copying or authoring accepted reports into
their target analysis report paths, rerunning the semantic validation gate, then
filling `automix/review/plugin_semantic_validation_runtime_manifest.json` before
the runtime evidence gate can pass.
