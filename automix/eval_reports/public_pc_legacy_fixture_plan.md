# Public PC Legacy Fixture Plan

- Project: `project`
- Created UTC: `2026-06-05T12:16:41Z`
- Status: `legacy_fixture_plan_ready`
- Passed: `True`
- REAPER AutoMix root: `/Users/hantaeheuk/Downloads/REAPER_2222_FULL_PROJECT_20260605-152350/source_workspaces/tttt/reaper-auto-mix`

## Summary

- Fixture groups: `4`
- Files reviewed: `26`
- Eligible read-only fixture files: `26`
- Lua files with disallowed calls: `5`
- Unique disallowed REAPER calls: `['GetSetProjectInfo', 'GetSetProjectInfo_String', 'GetSetProjectNotes', 'InsertMedia', 'SetTrackSendInfo_Value', 'TrackFX_SetEQBandEnabled', 'TrackFX_SetEQParam', 'TrackFX_SetNamedConfigParm', 'TrackFX_SetParam']`

## Readiness

- `ready_to_materialize_read_only_fixtures`: `True`
- `safe_to_merge_legacy_runtime_code`: `False`
- `safe_to_execute_legacy_lua_in_user_project`: `False`
- `safe_to_write_parameters`: `False`
- `safe_to_render_or_save`: `False`
- `safe_to_claim_final_audio_or_delivery`: `False`
- `report_only`: `True`

## Groups

### legacy_reaper_lua_safety_fixtures

- Ready: `True`
- Role: `reaper_api_safety_regression`
- Eligible files: `9`
- Missing files: `[]`

- `scripts/plugin_registry.lua` eligible `True` merge `False` sha `4151b31e6bc6`
  - disallowed calls: `['TrackFX_SetNamedConfigParm', 'TrackFX_SetParam']`
- `scripts/apply_mix_recipe.lua` eligible `True` merge `False` sha `b8fe4a5140f6`
- `scripts/fx_chain_builder.lua` eligible `True` merge `False` sha `a0776edeea52`
  - disallowed calls: `['TrackFX_SetEQBandEnabled', 'TrackFX_SetEQParam']`
- `scripts/render_setup.lua` eligible `True` merge `False` sha `bb22b8cebcf9`
  - disallowed calls: `['GetSetProjectInfo', 'GetSetProjectInfo_String']`
- `scripts/routing_builder.lua` eligible `True` merge `False` sha `42ef82e17220`
  - disallowed calls: `['SetTrackSendInfo_Value']`
- `scripts/utils.lua` eligible `True` merge `False` sha `75ab6c0bb918`
  - disallowed calls: `['GetSetProjectNotes', 'InsertMedia']`
- `scripts/validate_project_routing.lua` eligible `True` merge `False` sha `56171073979f`
- `scripts/import_and_mix_stems.lua` eligible `True` merge `False` sha `6d7e3c0181b9`
- `scripts/apply_revision_actions.lua` eligible `True` merge `False` sha `1b2209d7cb25`

### legacy_recipe_schema_fixtures

- Ready: `True`
- Role: `recipe_schema_regression`
- Eligible files: `6`
- Missing files: `[]`

- `recipes/schemas/mix_recipe.schema.json` eligible `True` merge `False` sha `fec35f3efa51`
- `recipes/schemas/qc_actions.schema.json` eligible `True` merge `False` sha `197a693bf65e`
- `recipes/schemas/arrangement_recipe.schema.json` eligible `True` merge `False` sha `47423dc7a4e0`
- `recipes/json/target_mix_recipe.json` eligible `True` merge `False` sha `24f3e34ca245`
- `recipes/json/default_target_arrangement_recipe.json` eligible `True` merge `False` sha `ba76b899d0d5`
- `recipes/lua/target_mix_recipe.lua` eligible `True` merge `False` sha `75dc63a06b03`

### legacy_review_evidence_fixtures

- Ready: `True`
- Role: `historical_red_team_regression`
- Eligible files: `5`
- Missing files: `[]`

- `review/handoff_validation_actual_targets_20260605.json` eligible `True` merge `False` sha `d8dd6f7e920b`
- `review/handoff_validation_20260605.json` eligible `True` merge `False` sha `313fc209899f`
- `review/red_team_report.md` eligible `True` merge `False` sha `a90f62fef971`
- `review/mix_risk_report.md` eligible `True` merge `False` sha `b91eb15e3997`
- `review/api_risk_report.md` eligible `True` merge `False` sha `4ff8868c6a53`

### legacy_handoff_doc_fixtures

- Ready: `True`
- Role: `intent_and_restore_context`
- Eligible files: `6`
- Missing files: `[]`

- `HANDOFF.md` eligible `True` merge `False` sha `2168be926e3f`
- `PROJECT_STATE.md` eligible `True` merge `False` sha `61f947aa9693`
- `NEXT_CODEX_PROMPT.md` eligible `True` merge `False` sha `ffcf4b08fde1`
- `RESTORE_ON_OTHER_COMPUTER.md` eligible `True` merge `False` sha `add738eee43b`
- `PACKAGE_WARNINGS.md` eligible `True` merge `False` sha `c099a2124d35`
- `FINAL_DECISIONS.md` eligible `True` merge `False` sha `133031f0e6fd`

## Blockers

- none

## Warnings

- `legacy_lua_disallowed_calls_detected:9`
- `low_confidence_secret_words_for_review:6`

## Limits

- This plan does not copy or execute public-PC code.
- Eligible files may be used only as read-only regression fixtures or manual-review evidence.
- Legacy Lua with REAPER mutation calls is useful as a negative safety fixture, not as approved runtime automation.
- Current fail-closed plugin semantic validation gates remain authoritative.
