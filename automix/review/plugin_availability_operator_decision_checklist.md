# Plugin Availability Operator Decision Checklist

- Candidate manifest: `automix/review/plugin_availability_disable_manifest_candidate.json`
- Accepted manifest path: `automix/review/plugin_availability_disable_manifest.json`
- Safe to write parameters: `False`

The candidate manifest is not accepted evidence. Use it as a draft only.

## Required Decisions

### OTT (Xfer Records)

- Recommended resolution: `disable_for_automatic_drafts`
- Allowed resolutions: `['disable_for_automatic_drafts', 'manual_review_only', 'keep_unavailable_blocked', 'install_and_rerun_preflight']`
- Fallback candidate: `ReaXcomp`
- Steps:
  - Choose install, disable for automatic drafts, manual-review only, or keep unavailable blocked.
  - If choosing install_and_rerun_preflight, install the plugin and rerun plugin_validation_preflight before treating it as resolved.
  - If choosing disable or manual-review only, create plugin_availability_disable_manifest.json with accepted schema and operator_acknowledged=true.
  - Keep automatic_parameter_writes_allowed=false for unavailable plugins and fallback candidates.
  - Rerun plugin_availability_decision_gate.py after writing the accepted operator manifest.
- Disallowed actions:
  - claim this plugin was used while unavailable
  - replace it with a fallback without semantic validation evidence
  - write parameters to any substitute based on catalog fallback text alone

### TDR Nova (Tokyo Dawn Labs)

- Recommended resolution: `disable_for_automatic_drafts`
- Allowed resolutions: `['disable_for_automatic_drafts', 'manual_review_only', 'keep_unavailable_blocked', 'install_and_rerun_preflight']`
- Fallback candidate: `ReaEQ plus ReaXcomp`
- Steps:
  - Choose install, disable for automatic drafts, manual-review only, or keep unavailable blocked.
  - If choosing install_and_rerun_preflight, install the plugin and rerun plugin_validation_preflight before treating it as resolved.
  - If choosing disable or manual-review only, create plugin_availability_disable_manifest.json with accepted schema and operator_acknowledged=true.
  - Keep automatic_parameter_writes_allowed=false for unavailable plugins and fallback candidates.
  - Rerun plugin_availability_decision_gate.py after writing the accepted operator manifest.
- Disallowed actions:
  - claim this plugin was used while unavailable
  - replace it with a fallback without semantic validation evidence
  - write parameters to any substitute based on catalog fallback text alone

## After Operator Acknowledgement

1. Write `automix/review/plugin_availability_disable_manifest.json` with schema `automix-plugin-availability-disable-manifest-v1`.
2. Set `operator_acknowledged=true` only for explicit operator decisions.
3. Keep `automatic_parameter_writes_allowed=false`.
4. Rerun `python3 scripts/run_plugin_availability_decision_gate.py --project-name project --output-dir automix`.
5. Rerun collection and semantic validation planning after the decision gate is ready.
