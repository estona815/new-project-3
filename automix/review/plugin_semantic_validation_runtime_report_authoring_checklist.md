# Plugin Semantic Validation Runtime Report Authoring Checklist

- Package ready: `False`
- Safe to write parameters: `False`
- Templates directory: `automix/review/plugin_semantic_validation_runtime_report_authoring_templates`

## Required Checks

- Confirm every source observation came from the raw runtime collector.
- Confirm each template status is `authoring_template_not_validation_evidence`.
- Keep templates under `automix/review/`; do not copy them into `automix/analysis_reports/` as passing reports.
- Manually author real `automix-plugin-parameter-validation-report-v1` reports only after mapping semantic controls, confidence, and safe bounds.
- Rerun runtime evidence and semantic validation gates after real reports exist.

## Template Jobs

- none
