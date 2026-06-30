# Plugin Availability Resolution Plan

- Project: `project`
- Created UTC: `2026-06-05T11:07:45Z`
- Status: `operator_resolution_required`
- Unavailable plugins: `2`
- Disable manifest plugins: `2`

This report resolves unavailable plugin choices only. It does not approve fallback parameter writes.

## Blockers

- none

## Resolutions

### OTT (Xfer Records)

- Severity: `review`
- Recommended resolution: `disable_for_automatic_drafts`
- Fallback candidate: `ReaXcomp`
- Fallback requires validation: `True`
- Automatic parameter writes allowed: `False`
- Rationale: Optional third-party plugins are not required for safe automation; disable them unless the user installs and validates them.

### TDR Nova (Tokyo Dawn Labs)

- Severity: `review`
- Recommended resolution: `disable_for_automatic_drafts`
- Fallback candidate: `ReaEQ plus ReaXcomp`
- Fallback requires validation: `True`
- Automatic parameter writes allowed: `False`
- Rationale: Optional third-party plugins are not required for safe automation; disable them unless the user installs and validates them.
