# Intent Classification Report

- Project: `project`
- Created UTC: `2026-06-05T11:41:25Z`
- Target profile: `digicore_hyperpop_hiphop_vocal_forward`
- Status: `review_required`
- Recommended primary intent: `conservative_cleanup`
- Safe next mode: `validate_plugin_mappings`

This report classifies intended work modes from available evidence. It does not apply FX, render audio, or prove a listening result.

## Intent Matrix

| Intent | Status | Confidence | Source risk | Vocal priority | Artifact focus | Overprocessing risk | Dry/wet cap | Next action |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `vocal_rescue` | `blocked_or_review_only` | 0.35 | 0.0 | 0.95 | 0.25 | 0.35 | 0.5 | `run_vocal_recovery_or_placement_dry_run` |
| `suno_artifact_suppression` | `blocked_or_review_only` | 0.2 | 0.25 | 0.9 | 0.35 | 0.7 | 0.3 | `run_conservative_artifact_suppression_dry_run` |
| `conservative_cleanup` | `blocked_or_review_only` | 0.45 | 0.0 | 0.8 | 0.25 | 0.3 | 0.45 | `create_conservative_cleanup_plan` |
| `stem_mix` | `blocked_or_review_only` | 0.0 | 0.0 | 0.9 | 0.0 | 0.45 | 0.45 | `run_stem_mix_dry_run` |
| `full_mix_polish` | `manual_review_only` | 0.0 | 0.35 | 0.7 | 0.0 | 0.8 | 0.25 | `request_stems_or_run_report_only_full_mix_qc` |
| `master_only` | `blocked_or_review_only` | 0.2 | 0.3 | 0.65 | 0.0 | 0.65 | 0.2 | `run_premaster_safety_scan` |
| `active_rebeat_mix` | `blocked_or_review_only` | 0.15 | 0.45 | 0.85 | 0.0 | 0.6 | 0.4 | `collect_rebeat_stems_and_manual_arrangement_intent` |
| `reels_preview_master` | `manual_review_only` | 0.2 | 0.5 | 0.8 | 0.0 | 0.7 | 0.2 | `run_loud_preview_only_after_final_qc` |
| `streaming_master` | `blocked_or_review_only` | 0.25 | 0.25 | 0.8 | 0.0 | 0.5 | 0.2 | `run_conservative_streaming_premaster_scan` |
| `aggressive_creative_enhancement` | `blocked` | 0.05 | 0.9 | 0.3 | 0.2 | 0.95 | 0.0 | `manual_review_only` |

## Blockers

- `aggressive_creative_enhancement_disabled_by_default`
- `artifact_signal_not_established`
- `explicit_rebeat_stems_and_arrangement_review_required`
- `explicit_user_approval_and_preview_required`
- `no_safe_vocal_candidate`
- `stems_not_ready`
- `validated_plugin_mapping_required`

## Warnings

- `no_validated_safe_plugin_adapters`

## Safety Notes

- `dry_run_only`: true
- `preview_only_until_ab_review`: true
- Aggressive creative enhancement is blocked by default.
- Artifact handling is described as reduction or suppression, not total cleanup.
- Mastering intent does not override unresolved mix, stem, or feedback blockers.
