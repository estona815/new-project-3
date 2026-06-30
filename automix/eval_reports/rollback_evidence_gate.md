# Rollback Evidence Gate

- Project: `project`
- Created UTC: `2026-06-02T16:12:43Z`
- Ready for delivery readiness: `True`
- Original tracks protected: `True`
- Original master protected: `True`
- Applied stages: `[]`
- Rollback entries: `3`
- Safe entries: `3`

This gate does not approve audio. It only checks rollback evidence.

## Blockers

- none

## Warnings

- `no_applied_stages_declared`
- `unknown:rollback_entry:rollback_entry_points_to_global_registry`
- `unknown:rollback_entry:rollback_stage_unknown`

## Entries

- `unknown` file=`automix/rollback/global_rollback_registry.json` safe=`True` blockers=`[]`
- `premaster` file=`automix/rollback/project_premaster_rollback.json` safe=`True` blockers=`[]`
- `reference_matching` file=`automix/rollback/project_reference_match_rollback.json` safe=`True` blockers=`[]`
