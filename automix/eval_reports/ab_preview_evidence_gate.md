# A/B Preview Evidence Gate

- Project: `project`
- Created UTC: `2026-06-02T15:52:52Z`
- Ready for human A/B review: `False`
- Ready for final approval request: `False`
- Human A/B review recorded: `False`
- Loudness metrics present: `False`
- Loudness delta after match: `None`
- Tolerance dB: `0.25`
- Final source linked to render manifest: `False`

This gate does not approve audio. It only checks that the A/B preview evidence is reviewable.

## Blockers

- `ab_preview_final_segment_missing`
- `ab_preview_loudness_match_metrics_missing`
- `ab_preview_manifest_has_warnings`
- `ab_preview_not_created`
- `ab_preview_not_loudness_matched`
- `ab_preview_original_segment_missing`
- `ab_preview_segments_missing`
- `ab_preview_too_few_segments`
- `preview_output_path_missing`
- `source_final_path_missing`
- `source_original_path_missing`

## Warnings

- `final_render_manifest_missing_ab_link_unverified`
- `manifest:ab_preview_not_requested_or_missing_sources`

## Audio Files

- `source_original` path=`` valid_wav=`False` failures=`['source_original_path_missing']`
- `source_final` path=`` valid_wav=`False` failures=`['source_final_path_missing']`
- `preview_output` path=`` valid_wav=`False` failures=`['preview_output_path_missing']`
