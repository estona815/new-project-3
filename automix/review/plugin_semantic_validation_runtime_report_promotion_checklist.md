# Plugin Semantic Validation Runtime Report Promotion Checklist

- Ready for operator promotion: `False`
- Candidate dir: `automix/review/plugin_semantic_validation_runtime_report_authoring_candidates`
- Manifest candidate: `automix/review/plugin_semantic_validation_runtime_manifest_candidate_from_authoring.json`
- Safe to write parameters: `False`

## Required Promotion Steps

1. Review every accepted candidate report manually.
2. Copy or author the accepted report into its target `automix/analysis_reports/` path.
3. Rerun `scripts/run_plugin_semantic_validation_gate.py`.
4. Fill `automix/review/plugin_semantic_validation_runtime_manifest.json` only after semantic validation sees the promoted reports.
5. Rerun `scripts/run_plugin_semantic_validation_runtime_evidence_gate.py`.

## Candidate Jobs

- none
