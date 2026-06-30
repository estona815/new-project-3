# Plugin Semantic Validation Runtime Collection Checklist

- Manifest candidate: `automix/review/plugin_semantic_validation_runtime_manifest_candidate.json`
- Report template directory: `automix/review/plugin_semantic_validation_runtime_report_templates`
- Safe to write parameters: `False`

Use only a saved test copy or temporary muted REAPER test context. Do not validate on the user's production mix path.

## Jobs

### semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx - Codex Vocal/vocal_ai_artifact_split_tamer.jsfx

- Target report: `automix/analysis_reports/plugin_parameter_validation_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_validation_report_template.json`
- Steps:
  - Open a saved test copy or temporary muted REAPER test context.
  - Insert or locate only the target plugin for this validation job.
  - Observe parameter names and semantic response without writing to the user's production mix.
  - Write the real validation report to the target_report_path using schema automix-plugin-parameter-validation-report-v1.
  - Rerun plugin_semantic_validation_gate.py and record report_reaudited_by_semantic_gate=true only after that gate sees the report.
- Acceptance criteria:
  - report schema is automix-plugin-parameter-validation-report-v1
  - status=passed
  - safe_for_automix=true
  - no_fake_success=true
  - at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name
- Disallowed actions:
  - do not mark a report passed from plugin availability alone
  - do not use fixed parameter indexes unless observed in the target REAPER runtime
  - do not validate on a production track without a saved test copy or temporary muted test context
  - do not write parameters to the user's mix from this queue

### semantic_validation_02_reaverbate_cockos - ReaVerbate (Cockos)

- Target report: `automix/analysis_reports/plugin_parameter_validation_reaverbate_cockos_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_02_reaverbate_cockos_validation_report_template.json`
- Steps:
  - Open a saved test copy or temporary muted REAPER test context.
  - Insert or locate only the target plugin for this validation job.
  - Observe parameter names and semantic response without writing to the user's production mix.
  - Write the real validation report to the target_report_path using schema automix-plugin-parameter-validation-report-v1.
  - Rerun plugin_semantic_validation_gate.py and record report_reaudited_by_semantic_gate=true only after that gate sees the report.
- Acceptance criteria:
  - report schema is automix-plugin-parameter-validation-report-v1
  - status=passed
  - safe_for_automix=true
  - no_fake_success=true
  - at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name
- Disallowed actions:
  - do not mark a report passed from plugin availability alone
  - do not use fixed parameter indexes unless observed in the target REAPER runtime
  - do not validate on a production track without a saved test copy or temporary muted test context
  - do not write parameters to the user's mix from this queue

### semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx - Vocal Clarity Repair/vocal_air_guard.jsfx

- Target report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_air_guard.jsfx_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx_validation_report_template.json`
- Steps:
  - Open a saved test copy or temporary muted REAPER test context.
  - Insert or locate only the target plugin for this validation job.
  - Observe parameter names and semantic response without writing to the user's production mix.
  - Write the real validation report to the target_report_path using schema automix-plugin-parameter-validation-report-v1.
  - Rerun plugin_semantic_validation_gate.py and record report_reaudited_by_semantic_gate=true only after that gate sees the report.
- Acceptance criteria:
  - report schema is automix-plugin-parameter-validation-report-v1
  - status=passed
  - safe_for_automix=true
  - no_fake_success=true
  - at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name
- Disallowed actions:
  - do not mark a report passed from plugin availability alone
  - do not use fixed parameter indexes unless observed in the target REAPER runtime
  - do not validate on a production track without a saved test copy or temporary muted test context
  - do not write parameters to the user's mix from this queue

### semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx - Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx

- Target report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_validation_report_template.json`
- Steps:
  - Open a saved test copy or temporary muted REAPER test context.
  - Insert or locate only the target plugin for this validation job.
  - Observe parameter names and semantic response without writing to the user's production mix.
  - Write the real validation report to the target_report_path using schema automix-plugin-parameter-validation-report-v1.
  - Rerun plugin_semantic_validation_gate.py and record report_reaudited_by_semantic_gate=true only after that gate sees the report.
- Acceptance criteria:
  - report schema is automix-plugin-parameter-validation-report-v1
  - status=passed
  - safe_for_automix=true
  - no_fake_success=true
  - at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name
- Disallowed actions:
  - do not mark a report passed from plugin availability alone
  - do not use fixed parameter indexes unless observed in the target REAPER runtime
  - do not validate on a production track without a saved test copy or temporary muted test context
  - do not write parameters to the user's mix from this queue

### semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx - Vocal Clarity Repair/vocal_output_guard.jsfx

- Target report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_output_guard.jsfx_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx_validation_report_template.json`
- Steps:
  - Open a saved test copy or temporary muted REAPER test context.
  - Insert or locate only the target plugin for this validation job.
  - Observe parameter names and semantic response without writing to the user's production mix.
  - Write the real validation report to the target_report_path using schema automix-plugin-parameter-validation-report-v1.
  - Rerun plugin_semantic_validation_gate.py and record report_reaudited_by_semantic_gate=true only after that gate sees the report.
- Acceptance criteria:
  - report schema is automix-plugin-parameter-validation-report-v1
  - status=passed
  - safe_for_automix=true
  - no_fake_success=true
  - at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name
- Disallowed actions:
  - do not mark a report passed from plugin availability alone
  - do not use fixed parameter indexes unless observed in the target REAPER runtime
  - do not validate on a production track without a saved test copy or temporary muted test context
  - do not write parameters to the user's mix from this queue

### semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx - Vocal Clarity Repair/vocal_presence_enhancer.jsfx

- Target report: `automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_presence_enhancer.jsfx_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx_validation_report_template.json`
- Steps:
  - Open a saved test copy or temporary muted REAPER test context.
  - Insert or locate only the target plugin for this validation job.
  - Observe parameter names and semantic response without writing to the user's production mix.
  - Write the real validation report to the target_report_path using schema automix-plugin-parameter-validation-report-v1.
  - Rerun plugin_semantic_validation_gate.py and record report_reaudited_by_semantic_gate=true only after that gate sees the report.
- Acceptance criteria:
  - report schema is automix-plugin-parameter-validation-report-v1
  - status=passed
  - safe_for_automix=true
  - no_fake_success=true
  - at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name
- Disallowed actions:
  - do not mark a report passed from plugin availability alone
  - do not use fixed parameter indexes unless observed in the target REAPER runtime
  - do not validate on a production track without a saved test copy or temporary muted test context
  - do not write parameters to the user's mix from this queue

### semantic_validation_07_reacomp_cockos - ReaComp (Cockos)

- Target report: `automix/analysis_reports/plugin_parameter_validation_reacomp_cockos_rerun_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_07_reacomp_cockos_validation_report_template.json`
- Steps:
  - Open a saved test copy or temporary muted REAPER test context.
  - Insert or locate only the target plugin for this validation job.
  - Observe parameter names and semantic response without writing to the user's production mix.
  - Write the real validation report to the target_report_path using schema automix-plugin-parameter-validation-report-v1.
  - Rerun plugin_semantic_validation_gate.py and record report_reaudited_by_semantic_gate=true only after that gate sees the report.
- Acceptance criteria:
  - report schema is automix-plugin-parameter-validation-report-v1
  - status=passed
  - safe_for_automix=true
  - no_fake_success=true
  - at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name
- Disallowed actions:
  - do not mark a report passed from plugin availability alone
  - do not use fixed parameter indexes unless observed in the target REAPER runtime
  - do not validate on a production track without a saved test copy or temporary muted test context
  - do not write parameters to the user's mix from this queue

### semantic_validation_08_readelay_cockos - ReaDelay (Cockos)

- Target report: `automix/analysis_reports/plugin_parameter_validation_readelay_cockos_rerun_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_08_readelay_cockos_validation_report_template.json`
- Steps:
  - Open a saved test copy or temporary muted REAPER test context.
  - Insert or locate only the target plugin for this validation job.
  - Observe parameter names and semantic response without writing to the user's production mix.
  - Write the real validation report to the target_report_path using schema automix-plugin-parameter-validation-report-v1.
  - Rerun plugin_semantic_validation_gate.py and record report_reaudited_by_semantic_gate=true only after that gate sees the report.
- Acceptance criteria:
  - report schema is automix-plugin-parameter-validation-report-v1
  - status=passed
  - safe_for_automix=true
  - no_fake_success=true
  - at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name
- Disallowed actions:
  - do not mark a report passed from plugin availability alone
  - do not use fixed parameter indexes unless observed in the target REAPER runtime
  - do not validate on a production track without a saved test copy or temporary muted test context
  - do not write parameters to the user's mix from this queue

### semantic_validation_09_reaeq_cockos - ReaEQ (Cockos)

- Target report: `automix/analysis_reports/plugin_parameter_validation_reaeq_cockos_rerun_reaper_observed.json`
- Template: `automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_09_reaeq_cockos_validation_report_template.json`
- Steps:
  - Open a saved test copy or temporary muted REAPER test context.
  - Insert or locate only the target plugin for this validation job.
  - Observe parameter names and semantic response without writing to the user's production mix.
  - Write the real validation report to the target_report_path using schema automix-plugin-parameter-validation-report-v1.
  - Rerun plugin_semantic_validation_gate.py and record report_reaudited_by_semantic_gate=true only after that gate sees the report.
- Acceptance criteria:
  - report schema is automix-plugin-parameter-validation-report-v1
  - status=passed
  - safe_for_automix=true
  - no_fake_success=true
  - at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name
- Disallowed actions:
  - do not mark a report passed from plugin availability alone
  - do not use fixed parameter indexes unless observed in the target REAPER runtime
  - do not validate on a production track without a saved test copy or temporary muted test context
  - do not write parameters to the user's mix from this queue

## After Collection

1. Copy or write real validation reports into the listed target report paths.
2. Rerun `python3 scripts/run_plugin_semantic_validation_gate.py --project-name project --output-dir automix`.
3. Fill `automix/review/plugin_semantic_validation_runtime_manifest.json` only after the semantic gate reaudit observes the reports.
4. Rerun `python3 scripts/run_plugin_semantic_validation_runtime_evidence_gate.py --project-name project --output-dir automix`.
