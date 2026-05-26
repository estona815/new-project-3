# Current Pipeline One Song Report

- Date/time: 2026-05-27 00:44:34
- Pipeline: source stem analysis -> raw clip-safe automix -> QC -> final WAV copy -> optional AAC export
- Final WAV: `/Users/hantaeheuk/Documents/New project 3/renders/current_pipeline_one_song/0101_CURRENT_PIPELINE_CLIP_SAFE.wav`
- Final AAC/M4A: `/Users/hantaeheuk/Documents/New project 3/renders/current_pipeline_one_song/0101_CURRENT_PIPELINE_CLIP_SAFE.m4a`
- Source QC report: `/Users/hantaeheuk/Documents/New project 3/reports/0101_raw_clip_safe_v01/raw_clip_safe_report.md`

## QC Snapshot

- True peak 4x: -1.2000001645528333 dBFS
- Approx integrated loudness: -15.292477385332296 LUFS
- Sample peak: -1.2097029722675468 dBFS
- Clipped samples >= 0.999: 0
- Duration: 139.4409375 sec

## Steps

- Raw stem analysis + clip-safe automix: ok
  - Automix log: `{
  "final_wav": "/Users/hantaeheuk/Documents/New project 3/renders/0101_raw_clip_safe_v01/0101_RAW_CLIP_SAFE_v01.wav",
  "true_peak_dbfs_4x": -1.2000001645528333,
  "lufs_i_approx_no_gate": -15.292477385332296,
  "clipped_samples": 0,
  "included_count": 8,
  "excluded_count": 8
}`
- Final WAV copied: `/Users/hantaeheuk/Documents/New project 3/renders/current_pipeline_one_song/0101_CURRENT_PIPELINE_CLIP_SAFE.wav`
- AAC preview/export created: `/Users/hantaeheuk/Documents/New project 3/renders/current_pipeline_one_song/0101_CURRENT_PIPELINE_CLIP_SAFE.m4a`

## Notes

- Original raw stems were not overwritten.
- Composite/reference files were analyzed but not mixed to avoid double-counting.
- This version prioritizes no crackle/no clipping over loudness.
- Human A/B check is still needed for vocal emotion and AI vowel-tail texture.
