# Manual Test Plan Prompt 37

Use a saved copy of a project and user-owned renders. Do not package rejected
drafts as final audio.

## State Resolver Tests

1. Accepted premaster draft is selected before placement, pitch/recovery, or
   recovery drafts.
2. Rejected premaster blocks final export.
3. Accepted placement is used only if no premaster exists.
4. Original mix is used only when explicitly approved.
5. Unresolved human review or missing A/B render blocks export.
6. Unresolved user feedback blocks export even with an accepted premaster
   source.
7. Resolved user feedback no longer blocks export when the resolution record has
   existing evidence, measured QC, loudness-matched A/B review, and human
   review.

## Approval Tests

1. Default approval is false.
2. Final export is blocked without approval.
3. Warnings require acknowledgment.
4. Unsafe override creates `UNSAFE_REVIEW_COPY`, never `FINAL_SAFE`.
5. Diagnostic-only mode can produce reports without approval.

## Naming Tests

1. Project names are sanitized.
2. Existing files trigger version increment.
3. Date, stage, sample rate, bit depth, or bitrate are present.
4. Unsafe exports include `UNSAFE_REVIEW_COPY`.

## Render Tests

1. WAV is the primary deliverable.
2. MP3-only final delivery is rejected.
3. Missing MP3 encoder creates a visible warning.
4. Zero-byte renders fail.
5. Missing loudness or true-peak data requires manual check.
6. No normalization or hidden limiter is added.

## A/B Preview Tests

1. Montage alternates original and final segments.
2. Segment labels are correct in the manifest.
3. Loudness-matching limitations are warned.
4. Rejected drafts cannot create a preview.

## QC Tests

1. Missing file fails.
2. Clipping fails.
3. Wrong sample rate fails.
4. Unexpected silence fails.
5. Rejected source fails.
6. True peak above ceiling fails if measurable.
7. Unresolved user feedback appears in final export state blockers and global
   QC blockers.

## Packaging Tests

1. Deliverables folder is created.
2. ZIP is created only when requested.
3. Manifest lists included and missing files.
4. Reports are included.
5. Rollback metadata is included.
6. Unapproved drafts are not included as final audio.

## Documentation Tests

1. `README_DELIVERY.md` exists.
2. `final_qc_report.md` exists.
3. `plugin_mapping_summary.md` exists.
4. `project_state_manifest.json` exists.

## Human Review

Mark `ready_for_delivery` only after the final WAV passes QC, warnings are
acknowledged, and the accepted source stage is approved.
