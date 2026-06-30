# Plugin Availability Decision Gate

- Project: `project`
- Created UTC: `2026-06-05T11:07:50Z`
- Status: `operator_decision_manifest_missing`
- Availability decisions ready: `False`
- Safe to write parameters: `False`
- Decision manifest: `automix/review/plugin_availability_disable_manifest.json`

Fallback writes remain blocked until semantic validation reports pass.

## Blockers

- `operator_decision_missing:OTT (Xfer Records)`
- `operator_decision_missing:TDR Nova (Tokyo Dawn Labs)`
- `plugin_availability_decision_manifest_missing`

## Decisions

### OTT (Xfer Records)

- Status: `blocked`
- Operator resolution: ``
- Operator acknowledged: `False`
- Automatic parameter writes allowed: `False`
- Fallback candidate: `ReaXcomp`
- Fallback requires validation: `False`
- Blockers: `['operator_decision_missing:OTT (Xfer Records)']`

### TDR Nova (Tokyo Dawn Labs)

- Status: `blocked`
- Operator resolution: ``
- Operator acknowledged: `False`
- Automatic parameter writes allowed: `False`
- Fallback candidate: `ReaEQ plus ReaXcomp`
- Fallback requires validation: `False`
- Blockers: `['operator_decision_missing:TDR Nova (Tokyo Dawn Labs)']`
