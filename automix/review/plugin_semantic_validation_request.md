# Plugin Semantic Validation Request

- Project: `project`
- Template: `automix/review/plugin_semantic_validation_manifest_template.json`

Required REAPER-side evidence for each plugin:

- Runtime plugin availability observed.
- Semantic parameter response observed, not guessed from index order.
- Safe min/max bounds recorded.
- `status=passed`, `safe_for_automix=true`, and `no_fake_success=true` only when at least one semantic control is validated and write-safe.

Current blockers:

- `ReaComp (Cockos):validation_report_has_no_write_safe_controls`
- `ReaComp (Cockos):validation_report_not_passed:validation_unavailable`
- `ReaComp (Cockos):validation_report_not_safe_for_automix`
- `ReaDelay (Cockos):validation_report_has_no_write_safe_controls`
- `ReaDelay (Cockos):validation_report_not_passed:validation_unavailable`
- `ReaDelay (Cockos):validation_report_not_safe_for_automix`
- `ReaEQ (Cockos):validation_report_has_no_write_safe_controls`
- `ReaEQ (Cockos):validation_report_not_passed:validation_unavailable`
- `ReaEQ (Cockos):validation_report_not_safe_for_automix`
- `no_passed_semantic_validation_report:ReaComp (Cockos)`
- `no_passed_semantic_validation_report:ReaDelay (Cockos)`
- `no_passed_semantic_validation_report:ReaEQ (Cockos)`
- `semantic_validation_passed_reports_missing`
- `validation_report_missing:Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- `validation_report_missing:OTT (Xfer Records)`
- `validation_report_missing:ReaVerbate (Cockos)`
- `validation_report_missing:TDR Nova (Tokyo Dawn Labs)`
- `validation_report_missing:Vocal Clarity Repair/vocal_air_guard.jsfx`
- `validation_report_missing:Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx`
- `validation_report_missing:Vocal Clarity Repair/vocal_output_guard.jsfx`
- `validation_report_missing:Vocal Clarity Repair/vocal_presence_enhancer.jsfx`
