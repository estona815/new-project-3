# Fixture Coverage Audit

- Project: `project`
- Created UTC: `2026-06-05T10:46:34Z`
- Passed: `True`
- Fixture root: `/Users/hantaeheuk/Documents/New project 3/tests/automix_validation/fixtures`
- Audio fixtures checked: `14`
- Analysis fixtures checked: `16`
- Categories covered: `17/17`

This report audits fixture coverage only. It does not prove audio quality, render quality, or user acceptance.

## Blockers

- none

## Warnings

- `fixture_coverage_complete_static_only`

## Missing Categories

- none

## Category Evidence

### clean_vocal

- Description: `clean vocal baseline`
- `audio` `raw_vocal_like_mono.wav`
- `audio` `clean_vocal_fixture.wav`

### buried_vocal

- Description: `vocal buried by instrumental masking`
- `audio` `vocal_buried_mix.wav`

### muddy_vocal

- Description: `low-mid/boxy vocal cleanup target`
- `audio` `muddy_vocal_fixture.wav`

### harsh_vocal

- Description: `harsh vocal tone`
- `audio` `harsh_sibilant_vocal.wav`

### sibilant_vocal

- Description: `sibilance guard`
- `audio` `harsh_sibilant_vocal.wav`

### suno_high_fizz

- Description: `AI/Suno-like high fizz`
- `audio` `already_tuned_ai_like_vocal.wav`
- `audio` `fragile_thin_ai_vocal.wav`
- `analysis` `already tuned 0.90`
- `analysis` `feedback mapping`

### watery_smear

- Description: `source-separated watery smear`
- `audio` `source_separated_watery_vocal.wav`

### fake_stereo_halo

- Description: `fake stereo halo or wide AI smear`
- `audio` `source_separated_watery_vocal.wav`
- `audio` `fake_stereo_halo_vocal.wav`

### over_limited_master

- Description: `over-limited master-like fixture`
- `audio` `over_limited_master.wav`

### low_end_buildup

- Description: `low-end buildup`
- `audio` `low_end_buildup_mix.wav`

### phase_issue

- Description: `phase or mono-compatibility issue`
- `audio` `fake_stereo_halo_vocal.wav`
- `audio` `phase_issue_stereo.wav`

### missing_plugin

- Description: `missing or uncertain plugin mapping`
- `analysis` `low adapter confidence`
- `analysis` `missing required semantic control`

### corrupted_config

- Description: `corrupted configuration/error fixture`
- `analysis` `corrupted config`

### dry_run

- Description: `dry-run only behavior`
- `analysis` `dry-run required`
- `analysis` `feedback mapping`
- `analysis` `safe draft pass`

### rollback

- Description: `rollback metadata requirement`
- `analysis` `rollback registry required`

### render_failure

- Description: `render failure handling`
- `analysis` `render failure`

### feedback_mapping

- Description: `user feedback to safe action mapping`
- `analysis` `feedback mapping`
- `analysis` `rejected placement`
- `analysis` `rejected premaster`
- `analysis` `rejected recovery`
