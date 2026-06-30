# Plugin Validation Action Request

- Project: `project`
- Status: `plugin_validation_actions_open`

Collect or repair this evidence before automatic parameter writes:

## OTT (Xfer Records)

- Action: `install_or_disable_unavailable_plugin`
- Expected report glob: `automix/analysis_reports/plugin_parameter_validation_ott_xfer_records*.json`
- Next action: Install the plugin, map a validated substitute, or disable this plugin for automatic drafts.
- Required evidence:
  - plugin availability evidence from plugin_validation_preflight
  - REAPER-observed semantic parameter validation report
  - status=passed, safe_for_automix=true, no_fake_success=true
  - at least one validated write_allowed semantic control with confidence>=0.85 and safe bounds

## TDR Nova (Tokyo Dawn Labs)

- Action: `install_or_disable_unavailable_plugin`
- Expected report glob: `automix/analysis_reports/plugin_parameter_validation_tdr_nova_tokyo_dawn_labs*.json`
- Next action: Install the plugin, map a validated substitute, or disable this plugin for automatic drafts.
- Required evidence:
  - plugin availability evidence from plugin_validation_preflight
  - REAPER-observed semantic parameter validation report
  - status=passed, safe_for_automix=true, no_fake_success=true
  - at least one validated write_allowed semantic control with confidence>=0.85 and safe bounds

## Codex Vocal/vocal_ai_artifact_split_tamer.jsfx

- Action: `collect_reaper_observed_semantic_validation`
- Expected report glob: `automix/analysis_reports/plugin_parameter_validation_codex_vocal_vocal_ai_artifact_split_tamer.jsfx*.json`
- Next action: Collect a REAPER-observed parameter validation report before allowing parameter writes.
- Required evidence:
  - plugin availability evidence from plugin_validation_preflight
  - REAPER-observed semantic parameter validation report
  - status=passed, safe_for_automix=true, no_fake_success=true
  - at least one validated write_allowed semantic control with confidence>=0.85 and safe bounds

## ReaVerbate (Cockos)

- Action: `collect_reaper_observed_semantic_validation`
- Expected report glob: `automix/analysis_reports/plugin_parameter_validation_reaverbate_cockos*.json`
- Next action: Collect a REAPER-observed parameter validation report before allowing parameter writes.
- Required evidence:
  - plugin availability evidence from plugin_validation_preflight
  - REAPER-observed semantic parameter validation report
  - status=passed, safe_for_automix=true, no_fake_success=true
  - at least one validated write_allowed semantic control with confidence>=0.85 and safe bounds

## Vocal Clarity Repair/vocal_air_guard.jsfx

- Action: `collect_reaper_observed_semantic_validation`
- Expected report glob: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_air_guard.jsfx*.json`
- Next action: Collect a REAPER-observed parameter validation report before allowing parameter writes.
- Required evidence:
  - plugin availability evidence from plugin_validation_preflight
  - REAPER-observed semantic parameter validation report
  - status=passed, safe_for_automix=true, no_fake_success=true
  - at least one validated write_allowed semantic control with confidence>=0.85 and safe bounds

## Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx

- Action: `collect_reaper_observed_semantic_validation`
- Expected report glob: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx*.json`
- Next action: Collect a REAPER-observed parameter validation report before allowing parameter writes.
- Required evidence:
  - plugin availability evidence from plugin_validation_preflight
  - REAPER-observed semantic parameter validation report
  - status=passed, safe_for_automix=true, no_fake_success=true
  - at least one validated write_allowed semantic control with confidence>=0.85 and safe bounds

## Vocal Clarity Repair/vocal_output_guard.jsfx

- Action: `collect_reaper_observed_semantic_validation`
- Expected report glob: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_output_guard.jsfx*.json`
- Next action: Collect a REAPER-observed parameter validation report before allowing parameter writes.
- Required evidence:
  - plugin availability evidence from plugin_validation_preflight
  - REAPER-observed semantic parameter validation report
  - status=passed, safe_for_automix=true, no_fake_success=true
  - at least one validated write_allowed semantic control with confidence>=0.85 and safe bounds

## Vocal Clarity Repair/vocal_presence_enhancer.jsfx

- Action: `collect_reaper_observed_semantic_validation`
- Expected report glob: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_presence_enhancer.jsfx*.json`
- Next action: Collect a REAPER-observed parameter validation report before allowing parameter writes.
- Required evidence:
  - plugin availability evidence from plugin_validation_preflight
  - REAPER-observed semantic parameter validation report
  - status=passed, safe_for_automix=true, no_fake_success=true
  - at least one validated write_allowed semantic control with confidence>=0.85 and safe bounds

## ReaComp (Cockos)

- Action: `rerun_or_keep_plugin_read_only`
- Expected report glob: `automix/analysis_reports/plugin_parameter_validation_reacomp_cockos*.json`
- Next action: Rerun semantic validation with observed parameter response, or keep this plugin read-only/manual-review only.
- Required evidence:
  - plugin availability evidence from plugin_validation_preflight
  - REAPER-observed semantic parameter validation report
  - status=passed, safe_for_automix=true, no_fake_success=true
  - at least one validated write_allowed semantic control with confidence>=0.85 and safe bounds

## ReaDelay (Cockos)

- Action: `rerun_or_keep_plugin_read_only`
- Expected report glob: `automix/analysis_reports/plugin_parameter_validation_readelay_cockos*.json`
- Next action: Rerun semantic validation with observed parameter response, or keep this plugin read-only/manual-review only.
- Required evidence:
  - plugin availability evidence from plugin_validation_preflight
  - REAPER-observed semantic parameter validation report
  - status=passed, safe_for_automix=true, no_fake_success=true
  - at least one validated write_allowed semantic control with confidence>=0.85 and safe bounds

## ReaEQ (Cockos)

- Action: `rerun_or_keep_plugin_read_only`
- Expected report glob: `automix/analysis_reports/plugin_parameter_validation_reaeq_cockos*.json`
- Next action: Rerun semantic validation with observed parameter response, or keep this plugin read-only/manual-review only.
- Required evidence:
  - plugin availability evidence from plugin_validation_preflight
  - REAPER-observed semantic parameter validation report
  - status=passed, safe_for_automix=true, no_fake_success=true
  - at least one validated write_allowed semantic control with confidence>=0.85 and safe bounds
