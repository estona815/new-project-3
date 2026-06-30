# Plugin Availability Operator Decision Firewall Gate

- Project: `project`
- Created UTC: `2026-06-05T12:32:36Z`
- Status: `operator_decision_candidate_firewalled_pending_acknowledgement`
- Passed: `True`
- Candidate firewalled: `True`
- Accepted manifest ready: `False`
- Safe to write parameters: `False`

This report checks that operator decision candidates do not become accepted evidence without acknowledgement.

## Counts

- `required_decisions_total`: `2`
- `candidate_decisions_total`: `2`
- `accepted_decisions_total`: `0`
- `missing_accepted_decisions_total`: `2`

## Blockers

- none

## Warnings

- `accepted_operator_decision_manifest_missing:2`

## Candidate Entries

### OTT (Xfer Records)

- Status: `candidate_safe`
- Resolution: `disable_for_automatic_drafts`
- Operator acknowledged: `False`
- Automatic writes allowed: `False`
- Fallback requires validation: `True`
- Blockers: `[]`

### TDR Nova (Tokyo Dawn Labs)

- Status: `candidate_safe`
- Resolution: `disable_for_automatic_drafts`
- Operator acknowledged: `False`
- Automatic writes allowed: `False`
- Fallback requires validation: `True`
- Blockers: `[]`

## Accepted Entries

- none
## Limits

- This gate does not install plugins, open REAPER, write parameters, render, or approve audio.
- Candidate manifests are operator drafts only and must not count as accepted decisions.
- Accepted disable manifests still do not grant fallback parameter write safety.
- Fallback writes remain blocked until semantic validation reports pass.
