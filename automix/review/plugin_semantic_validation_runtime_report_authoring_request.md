# Plugin Semantic Validation Runtime Report Authoring Request

- Ready for manual report authoring: `False`
- Creates validation reports: `False`
- Safe to write parameters: `False`

Only accepted raw observations may be used as source material for manually authored `automix-plugin-parameter-validation-report-v1` reports.

## Accepted Observations

- none

## Required Follow-Up

- Manually map semantic controls by observed parameter name and safe bounds.
- Write real validation reports only after review.
- Update `automix/review/plugin_semantic_validation_runtime_manifest.json` after reports exist.
- Rerun runtime evidence gate and then semantic validation gate before any write-safety decision.
