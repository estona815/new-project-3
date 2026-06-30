# Plugin Availability Decision Request

- Project: `project`
- Required decisions: `2`
- Accepted manifest path: `automix/review/plugin_availability_disable_manifest.json`

Create an accepted manifest at the path above with schema `automix-plugin-availability-disable-manifest-v1`.
Each unavailable plugin needs `operator_acknowledged=true`, `automatic_parameter_writes_allowed=false`, and fallback validation still required when a fallback candidate is listed.

## Required Plugins

- `OTT (Xfer Records)`
- `TDR Nova (Tokyo Dawn Labs)`

## Current Blockers

- `operator_decision_missing:OTT (Xfer Records)`
- `operator_decision_missing:TDR Nova (Tokyo Dawn Labs)`
- `plugin_availability_decision_manifest_missing`
