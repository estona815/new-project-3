# Plugin Fallbacks

Plugin automation is confidence-gated. A detected plugin name is not enough to
write parameters.

## Required Checks

- inventory scan exists;
- local availability preflight separates plugin file presence from write
  safety;
- adapter mapping exists;
- semantic controls are validated;
- confidence meets threshold;
- unknown parameters are skipped;
- safe min/max bounds exist;
- parameter writes are logged;
- rollback metadata exists for applied drafts.

## Fallback Rules

Fallbacks may support generic EQ, dynamics, or utility planning when mappings
are safe. They must not be used as proof that a specific developed plugin
loaded.

Low-confidence plugin mappings must not write parameters. They may only produce
diagnostic notes, mapping requests, or dry-run fallback plans.

For Suno/AI vocal rescue, the required first-slot developed artifact plugin is
not replaceable by a generic EQ, multiband compressor, or de-esser. If the exact
plugin trace is missing, stop and fix plugin loading before final claims.

## Unsafe Plugin Responses

Do not hard-code uncertain parameter indexes. Do not write to low-confidence
controls. Do not infer third-party plugin usage from a chain plan unless the
actual plugin trace proves it.

## Reports

Review:

- `automix/analysis_reports/plugin_inventory_audit.json`
- `automix/eval_reports/plugin_validation_preflight.json`
- `automix/eval_reports/plugin_capability_report.md`
- `automix/export/plugin_mapping_summary.md`

Availability preflight may confirm that stock plugins or JSFX files exist on
disk. It must not be used as permission to write parameters until semantic
controls are validated.

`scripts/run_plugin_semantic_validation_collection_plan.py` turns missing or
failed semantic validation into explicit REAPER-observed report collection jobs.
It is still planning evidence only; the generated reports must pass
`scripts/run_plugin_semantic_validation_gate.py` before any automated parameter
write.

`scripts/run_plugin_semantic_validation_queue.py` packages those collectable
jobs into a runtime queue for a saved test copy or temporary muted test context.
It does not open REAPER and does not grant write permission.

`scripts/run_plugin_semantic_validation_runtime_collection_package.py` builds the
operator collection checklist, runtime manifest candidate, and report templates
for those queued jobs. The generated templates live under `automix/review/` and
are not validation evidence; only real REAPER-observed reports under
`automix/analysis_reports/` can be audited by the semantic validation gate.

`scripts/run_plugin_semantic_validation_runtime_collector_package.py` builds a
REAPER-side Lua collector and queue payload for raw observations. The collector
uses a temporary muted probe track and writes parameter-name observations only;
it does not create passing validation reports or make any parameter write safe.

`scripts/run_plugin_semantic_validation_runtime_observation_gate.py` checks those
raw observation files before manual report authoring. It can confirm that raw
observations are complete enough to review, but it still does not create
validation reports or make any parameter write safe.

`scripts/run_plugin_semantic_validation_runtime_report_authoring_package.py`
turns accepted raw observations into review-only authoring templates under
`automix/review/`. It does not write `automix/analysis_reports/`, create
passing validation reports, or make any parameter write safe.

`scripts/run_plugin_semantic_validation_runtime_report_authoring_gate.py` checks
human-authored candidate reports under
`automix/review/plugin_semantic_validation_runtime_report_authoring_candidates/`.
Passing this gate means the candidates are ready for operator promotion only; it
does not copy them into `automix/analysis_reports/`, make them runtime evidence,
or make any parameter write safe.

After the queue is run, `scripts/run_plugin_semantic_validation_runtime_evidence_gate.py`
checks `automix/review/plugin_semantic_validation_runtime_manifest.json` and the
queued validation reports. This gate still keeps `safe_to_write_parameters=false`;
it only confirms that runtime evidence is ready for another semantic validation
gate pass.

Unavailable third-party plugins may be planned for disablement through
`automix/review/plugin_availability_disable_manifest_template.json`, but the
template is not accepted evidence. The operator-approved file must be written to
`automix/review/plugin_availability_disable_manifest.json` and validated by
`scripts/run_plugin_availability_decision_gate.py`.

`scripts/run_plugin_availability_operator_decision_package.py` creates a
candidate manifest and checklist for those operator choices. The candidate schema
is intentionally not accepted by the decision gate; it is only a draft until a
human explicitly acknowledges each unavailable plugin decision.

That decision does not make any fallback write-safe; fallback plugins still need
semantic validation reports before parameter writes.
