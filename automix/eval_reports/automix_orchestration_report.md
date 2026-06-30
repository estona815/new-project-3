# AutoMix Orchestration Report

## Summary

- Project: `project`
- Mode: `final_delivery`
- Target profile: `digicore_hyperpop_hiphop_vocal_forward`
- References: `0`
- Global status: `final_delivery_failed`
- Safe to export: `False`
- Drafts created: `0`
- Final package: `not created`

## Stage Results

| Stage | Status | Key output | Warnings | Required action |
|---|---|---|---|---|
| `plugin_intelligence` | `passed_with_warnings` | plugin inventory audit completed without applying FX | inventory_file_missing; no_validated_plugin_adapters_available | `` |
| `github_integration_smoke` | `passed_with_warnings` | GitHub MCP/reapy integration smoke completed in dry-run mode | github_integration_dry_run_only; not_a_live_reaper_bridge; not_safe_to_write_parameters | `` |
| `project_scan` | `passed_with_warnings` | 0 tracks, 0 media items | project_file_missing_or_not_provided; project_path_empty_report_only_context | `` |
| `track_role_detection` | `passed_with_warnings` | 0 tracks role-tagged | no_tracks_available_for_role_detection | `` |
| `source_classification` | `passed_with_warnings` | 0 vocal-like, 0 full-mix/reference, 0 unknown | audio_source_classification_not_run_no_track_audio | `` |
| `intent_classification` | `passed_with_warnings` | intent=conservative_cleanup next=validate_plugin_mappings | intent_blocker:aggressive_creative_enhancement_disabled_by_default; intent_blocker:artifact_signal_not_established; intent_blocker:explicit_rebeat_stems_and_arrangement_review_required | `` |
| `vocal_recovery_analysis` | `passed_with_warnings` | recovery analysis report-only | analysis_only_no_audio_recovery_rendered | `` |
| `vocal_recovery_draft` | `skipped` | final_delivery mode does not create recovery drafts | final_delivery mode does not create recovery drafts | `` |
| `vocal_recovery_eval` | `skipped` | no recovery draft was created; evaluation skipped | no recovery draft was created; evaluation skipped | `` |
| `recovery_review_gate` | `skipped` | recovery review gate not requested | recovery review gate not requested | `` |
| `final_vocal_space_finish` | `skipped` | final vocal space finish not requested | final vocal space finish not requested | `` |
| `final_placement_adapter_validation` | `skipped` | final placement adapter validation not requested | final placement adapter validation not requested | `` |
| `pitch_triage` | `passed_with_warnings` | pitch triage report-only | pitch_triage_report_only_no_audio | `` |
| `pitch_draft` | `skipped` | final_delivery mode does not create pitch drafts | final_delivery mode does not create pitch drafts | `` |
| `pitch_eval` | `skipped` | no pitch draft was created; evaluation skipped | no pitch draft was created; evaluation skipped | `` |
| `vocal_placement_analysis` | `passed_with_warnings` | placement analysis report-only | placement analysis report-only | `` |
| `vocal_placement_draft` | `skipped` | final_delivery mode does not create placement drafts | final_delivery mode does not create placement drafts | `` |
| `vocal_placement_eval` | `skipped` | no placement draft was created; evaluation skipped | no placement draft was created; evaluation skipped | `` |
| `reference_match_analysis` | `passed_with_warnings` | 0 references available | no_reference_audio_provided_target_profile_only | `` |
| `reference_match_draft` | `skipped` | final_delivery mode does not create reference-match drafts | final_delivery mode does not create reference-match drafts | `` |
| `reference_match_eval` | `skipped` | no reference-match draft was created; evaluation skipped | no reference-match draft was created; evaluation skipped | `` |
| `premaster_analysis` | `passed_with_warnings` | premaster analysis report-only | source_mix_not_supplied_report_only | `` |
| `premaster_draft` | `skipped` | final_delivery mode does not create premaster drafts | final_delivery mode does not create premaster drafts | `` |
| `premaster_eval` | `skipped` | no premaster draft was created; evaluation skipped | no premaster draft was created; evaluation skipped | `` |
| `translation_check` | `skipped` | no premaster draft; translation check skipped | no premaster draft; translation check skipped | `` |
| `final_export_state_resolver` | `requires_approval` | final export source resolution completed | no_accepted_export_source | `approve_human_review` |
| `final_export` | `blocked` | blocked by dependency graph |  | `` |
| `final_qc` | `blocked` | blocked by dependency graph |  | `` |
| `deliverable_package` | `blocked` | blocked by dependency graph |  | `` |
| `professional_readiness_audit` | `blocked` | professional readiness: review_required |  | `approve_human_review` |

## Plugin Safety

- Safe adapters: `0`
- Provisional adapters: `0`
- Unsafe/unmapped plugins: `0`
- Fallback strategy: `stock/JSFX or manual review only after adapter validation`

## Source / Track Summary

- Total tracks: `0`
- Vocal-like tracks: `0`
- Full-mix unsafe tracks: `0`
- Stem-required tracks: `0`
- Unknown tracks skipped: `0`

## Intent Classification

- Status: `review_required`
- Recommended primary intent: `conservative_cleanup`
- Safe next mode: `validate_plugin_mappings`
- Safe draft intents: `none`
- Dry-run only: `True`

## Vocal Recovery

- Tracks analyzed: `0`
- Drafts created: `0`
- Accepted: `0`
- Rejected: `0`
- Manual review required: `False`

## Pitch Correction

- Tracks triaged: `0`
- Pitch drafts created: `0`
- Skipped: `True`
- Full mix unsafe: `0`
- Already tuned skipped: `0`
- Stem required: `False`
- Manual tuning required: `False`

## Vocal Placement

- Placement drafts: `0`
- A/B status: `not rendered`
- Accepted: `0`
- Rejected: `0`
- Manual review required: `False`

## Final Vocal Space

- Finish stage: `skipped`
- Adapter validation: `skipped`
- Reaper application: `not run by orchestrator`
- Final export: `blocked until review and QC`

## Reference Matching

- Target profile: `digicore_hyperpop_hiphop_vocal_forward`
- References used: `0`
- Safe adjustments: `0`
- Blocked adjustments: `0`
- Draft status: `skipped`

## Premaster

- Premaster draft: `skipped`
- Loudness: `not measured`
- True peak: `not measured`
- Translation check: `skipped`
- Status: `passed_with_warnings`

## Final Export

- Export source: `none`
- Approval: `False`
- QC: `review_required`
- Package: `not created`
- Status: `blocked`

## Rollback

- Rollback registry: `automix/rollback/global_rollback_registry.json`
- Original tracks protected: `True`
- Original master protected: `True`
- Safe to rollback: `True`

## Next Required Actions

- Approve final export and acknowledge warnings before final delivery.

## Final Recommendation

`unsafe_to_continue`
