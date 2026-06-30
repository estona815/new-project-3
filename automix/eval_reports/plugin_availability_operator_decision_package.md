# Plugin Availability Operator Decision Package

- Project: `project`
- Created UTC: `2026-06-02T18:33:43Z`
- Status: `operator_decisions_ready_for_human_acknowledgement`
- Package ready: `True`
- Availability decisions ready: `False`
- Required decisions: `2`
- Accepted decisions: `0`
- Safe to write parameters: `False`

This package prepares operator plugin-availability decisions only. It does not accept decisions by itself.

## Blockers

- none

## Warnings

- `operator_disable_or_install_decision_required`

## Decisions

### OTT (Xfer Records)

- Recommended resolution: `disable_for_automatic_drafts`
- Current status: `blocked`
- Fallback candidate: `ReaXcomp`
- Fallback requires validation: `True`
- Automatic parameter writes allowed: `False`
- Current blockers: `['operator_decision_missing:OTT (Xfer Records)']`

### TDR Nova (Tokyo Dawn Labs)

- Recommended resolution: `disable_for_automatic_drafts`
- Current status: `blocked`
- Fallback candidate: `ReaEQ plus ReaXcomp`
- Fallback requires validation: `True`
- Automatic parameter writes allowed: `False`
- Current blockers: `['operator_decision_missing:TDR Nova (Tokyo Dawn Labs)']`
