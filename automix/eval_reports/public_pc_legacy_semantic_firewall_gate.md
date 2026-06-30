# Public PC Legacy Semantic Firewall Gate

- Project: `project`
- Created UTC: `2026-06-05T12:16:52Z`
- Status: `legacy_semantic_firewall_clear`
- Passed: `True`
- Legacy records: `26`
- Negative records: `5`
- Semantic reports scanned: `7`

## Readiness

- `legacy_fixtures_firewalled_from_semantic_validation`: `True`
- `legacy_fixtures_count_as_validation_evidence`: `False`
- `semantic_validation_inputs_clean`: `True`
- `safe_to_merge_legacy_runtime_code`: `False`
- `safe_to_execute_legacy_lua_in_user_project`: `False`
- `safe_to_write_parameters`: `False`
- `safe_to_claim_final_audio_or_delivery`: `False`
- `report_only`: `True`

## Coverage

- Legacy semantic references: `0`
- Hash conflicts in analysis reports: `0`
- Parameter-write legacy records: `['scripts/fx_chain_builder.lua', 'scripts/plugin_registry.lua']`
- Project-mutation legacy records: `['scripts/render_setup.lua', 'scripts/routing_builder.lua', 'scripts/utils.lua']`
- Missing semantic reports: `0`


## Semantic Reports

- `plugin_semantic_validation_gate.json` exists `True` valid `True` legacy refs `0`
- `plugin_semantic_validation_runtime_evidence_gate.json` exists `True` valid `True` legacy refs `0`
- `plugin_semantic_validation_runtime_report_authoring_gate.json` exists `True` valid `True` legacy refs `0`
- `plugin_semantic_validation_queue.json` exists `True` valid `True` legacy refs `0`
- `plugin_semantic_validation_runtime_collection_package.json` exists `True` valid `True` legacy refs `0`
- `plugin_semantic_validation_runtime_collector_package.json` exists `True` valid `True` legacy refs `0`
- `plugin_semantic_validation_runtime_observation_gate.json` exists `True` valid `True` legacy refs `0`

## Blockers

- none

## Warnings

- `legacy_negative_safety_fixture_records:5`
- `legacy_parameter_write_records:2`
- `legacy_project_mutation_records:3`

## Limits

- This gate does not execute legacy Lua, open REAPER, write parameters, render, or approve audio.
- Public-PC legacy files may be used as read-only or negative safety fixtures only.
- Legacy fixture paths or hashes must not appear as accepted semantic validation evidence.
- Passing this firewall does not make plugin semantic validation ready.
