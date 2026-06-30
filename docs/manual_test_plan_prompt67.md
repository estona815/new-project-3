# Prompt67 Manual Test Plan

## Scope

Validate the deliverable package evidence gate after final export packaging.
This plan checks ZIP and manifest evidence only; it does not approve audio.

## Steps

1. Run final export packaging with a real accepted WAV, original WAV, `--render`,
   `--make-ab-preview`, `--qc`, and `--zip`.
2. Record final human approval only after matched-loudness listening review.
3. Run:

```sh
python3 scripts/run_deliverable_package_evidence_gate.py \
  --project-name project \
  --output-dir automix \
  --require-ready
```

4. Confirm these files exist:

- `automix/eval_reports/deliverable_package_evidence_gate.json`
- `automix/eval_reports/deliverable_package_evidence_gate.md`
- `automix/review/deliverable_package_evidence_manifest_template.json`
- `automix/review/deliverable_package_evidence_request.md`

## Expected Pass Conditions

- `ready_for_delivery_package` is `true`.
- The ZIP path exists, opens cleanly, and has at least one file.
- Declared package size matches the ZIP size on disk.
- `files_missing` is empty.
- Required render, QC, A/B, approval, rollback, project-state, and plugin
  evidence files are present.
- No package path contains credential-like, raw-stem, reference, or source
  package markers.

## Expected Fail Conditions

- Missing or invalid package manifest.
- `package_created` false, missing ZIP path, unreadable ZIP, or size mismatch.
- Missing included files or required evidence files.
- Supporting render/QC/A-B/approval/rollback evidence gate is not ready.
- Unsafe review copy naming conflicts with `FINAL_SAFE`.
- Credential-like or raw/reference/source-package paths appear in
  `files_included`.
