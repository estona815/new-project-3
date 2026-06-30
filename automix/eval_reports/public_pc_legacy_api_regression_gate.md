# Public PC Legacy API Regression Gate

- Project: `project`
- Created UTC: `2026-06-05T12:16:41Z`
- Status: `legacy_api_regression_covered`
- Passed: `True`
- Records reviewed: `26`

## Readiness

- `legacy_api_regression_covered`: `True`
- `ready_to_use_negative_safety_fixtures`: `True`
- `safe_to_merge_legacy_runtime_code`: `False`
- `safe_to_execute_legacy_lua_in_user_project`: `False`
- `safe_to_write_parameters`: `False`
- `safe_to_render_or_save`: `False`
- `safe_to_claim_final_audio_or_delivery`: `False`
- `report_only`: `True`

## Policy Coverage

- Plan disallowed calls: `['GetSetProjectInfo', 'GetSetProjectInfo_String', 'GetSetProjectNotes', 'InsertMedia', 'SetTrackSendInfo_Value', 'TrackFX_SetEQBandEnabled', 'TrackFX_SetEQParam', 'TrackFX_SetNamedConfigParm', 'TrackFX_SetParam']`
- Uncovered policy calls: `[]`
- Required direct-merge blockers: `['current_fail_closed_gates_must_remain_authoritative', 'legacy_runtime_code_requires_manual_review']`

## Risk Records

- Disallowed API records: `5`
- Parameter write records: `['scripts/fx_chain_builder.lua', 'scripts/plugin_registry.lua']`
- Project mutation records: `['scripts/render_setup.lua', 'scripts/routing_builder.lua', 'scripts/utils.lua']`
- Unsafe runtime records: `[]`
- Unsafe merge records: `[]`

- `scripts/plugin_registry.lua` calls `['TrackFX_SetNamedConfigParm', 'TrackFX_SetParam']`
- `scripts/fx_chain_builder.lua` calls `['TrackFX_SetEQBandEnabled', 'TrackFX_SetEQParam']`
- `scripts/render_setup.lua` calls `['GetSetProjectInfo', 'GetSetProjectInfo_String']`
- `scripts/routing_builder.lua` calls `['SetTrackSendInfo_Value']`
- `scripts/utils.lua` calls `['GetSetProjectNotes', 'InsertMedia']`

## Blockers

- none

## Warnings

- `legacy_disallowed_reaper_api_records:5`
- `legacy_parameter_write_records:2`
- `legacy_project_mutation_records:3`

## Limits

- This gate proves only static regression coverage for legacy public-PC APIs.
- It does not execute legacy Lua, approve parameter writes, render audio, or validate sonic quality.
- Legacy files with disallowed REAPER calls are negative fixtures for safety gates, not approved automation code.
