# Plugin Validation Action Plan

- Project: `project`
- Created UTC: `2026-06-05T11:07:42Z`
- Status: `plugin_validation_actions_open`
- Safe to write parameters: `False`
- Required plugins: `11`
- Plugin actions: `11`
- Plugins with safe controls: `0`

This report sequences plugin validation evidence. It does not approve plugin parameter writes from availability alone.

## Blockers

- `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx:collect_reaper_observed_semantic_validation`
- `OTT (Xfer Records):install_or_disable_unavailable_plugin`
- `ReaComp (Cockos):rerun_or_keep_plugin_read_only`
- `ReaDelay (Cockos):rerun_or_keep_plugin_read_only`
- `ReaEQ (Cockos):rerun_or_keep_plugin_read_only`
- `ReaVerbate (Cockos):collect_reaper_observed_semantic_validation`
- `TDR Nova (Tokyo Dawn Labs):install_or_disable_unavailable_plugin`
- `Vocal Clarity Repair/vocal_air_guard.jsfx:collect_reaper_observed_semantic_validation`
- `Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx:collect_reaper_observed_semantic_validation`
- `Vocal Clarity Repair/vocal_output_guard.jsfx:collect_reaper_observed_semantic_validation`
- `Vocal Clarity Repair/vocal_presence_enhancer.jsfx:collect_reaper_observed_semantic_validation`

## Next Plugin Action

- `OTT (Xfer Records)` `install_or_disable_unavailable_plugin`: Install the plugin, map a validated substitute, or disable this plugin for automatic drafts.

## Plugin Actions

### OTT (Xfer Records)

- Severity: `blocker`
- Action: `install_or_disable_unavailable_plugin`
- Available: `False`
- Matching reports: `0`
- Passed reports: `0`
- Safe controls: `0`
- Expected report: `automix/analysis_reports/plugin_parameter_validation_ott_xfer_records*.json`
- Recommended next action: Install the plugin, map a validated substitute, or disable this plugin for automatic drafts.

### TDR Nova (Tokyo Dawn Labs)

- Severity: `blocker`
- Action: `install_or_disable_unavailable_plugin`
- Available: `False`
- Matching reports: `0`
- Passed reports: `0`
- Safe controls: `0`
- Expected report: `automix/analysis_reports/plugin_parameter_validation_tdr_nova_tokyo_dawn_labs*.json`
- Recommended next action: Install the plugin, map a validated substitute, or disable this plugin for automatic drafts.

### Codex Vocal/vocal_ai_artifact_split_tamer.jsfx

- Severity: `blocker`
- Action: `collect_reaper_observed_semantic_validation`
- Available: `True`
- Matching reports: `0`
- Passed reports: `0`
- Safe controls: `0`
- Expected report: `automix/analysis_reports/plugin_parameter_validation_codex_vocal_vocal_ai_artifact_split_tamer.jsfx*.json`
- Recommended next action: Collect a REAPER-observed parameter validation report before allowing parameter writes.

### ReaVerbate (Cockos)

- Severity: `blocker`
- Action: `collect_reaper_observed_semantic_validation`
- Available: `True`
- Matching reports: `0`
- Passed reports: `0`
- Safe controls: `0`
- Expected report: `automix/analysis_reports/plugin_parameter_validation_reaverbate_cockos*.json`
- Recommended next action: Collect a REAPER-observed parameter validation report before allowing parameter writes.

### Vocal Clarity Repair/vocal_air_guard.jsfx

- Severity: `blocker`
- Action: `collect_reaper_observed_semantic_validation`
- Available: `True`
- Matching reports: `0`
- Passed reports: `0`
- Safe controls: `0`
- Expected report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_air_guard.jsfx*.json`
- Recommended next action: Collect a REAPER-observed parameter validation report before allowing parameter writes.

### Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx

- Severity: `blocker`
- Action: `collect_reaper_observed_semantic_validation`
- Available: `True`
- Matching reports: `0`
- Passed reports: `0`
- Safe controls: `0`
- Expected report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx*.json`
- Recommended next action: Collect a REAPER-observed parameter validation report before allowing parameter writes.

### Vocal Clarity Repair/vocal_output_guard.jsfx

- Severity: `blocker`
- Action: `collect_reaper_observed_semantic_validation`
- Available: `True`
- Matching reports: `0`
- Passed reports: `0`
- Safe controls: `0`
- Expected report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_output_guard.jsfx*.json`
- Recommended next action: Collect a REAPER-observed parameter validation report before allowing parameter writes.

### Vocal Clarity Repair/vocal_presence_enhancer.jsfx

- Severity: `blocker`
- Action: `collect_reaper_observed_semantic_validation`
- Available: `True`
- Matching reports: `0`
- Passed reports: `0`
- Safe controls: `0`
- Expected report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_presence_enhancer.jsfx*.json`
- Recommended next action: Collect a REAPER-observed parameter validation report before allowing parameter writes.

### ReaComp (Cockos)

- Severity: `blocker`
- Action: `rerun_or_keep_plugin_read_only`
- Available: `True`
- Matching reports: `1`
- Passed reports: `0`
- Safe controls: `0`
- Expected report: `automix/analysis_reports/plugin_parameter_validation_reacomp_cockos*.json`
- Recommended next action: Rerun semantic validation with observed parameter response, or keep this plugin read-only/manual-review only.

### ReaDelay (Cockos)

- Severity: `blocker`
- Action: `rerun_or_keep_plugin_read_only`
- Available: `True`
- Matching reports: `1`
- Passed reports: `0`
- Safe controls: `0`
- Expected report: `automix/analysis_reports/plugin_parameter_validation_readelay_cockos*.json`
- Recommended next action: Rerun semantic validation with observed parameter response, or keep this plugin read-only/manual-review only.

### ReaEQ (Cockos)

- Severity: `blocker`
- Action: `rerun_or_keep_plugin_read_only`
- Available: `True`
- Matching reports: `1`
- Passed reports: `0`
- Safe controls: `0`
- Expected report: `automix/analysis_reports/plugin_parameter_validation_reaeq_cockos*.json`
- Recommended next action: Rerun semantic validation with observed parameter response, or keep this plugin read-only/manual-review only.
