# Prompt50 Fixture Coverage Manual Test Plan

## Purpose

Verify that the REAPER-free validation harness contains explicit fixture
coverage for the required safety and failure scenarios.

## Commands

```sh
python3 tests/automix_validation/scripts/generate_synthetic_audio_fixtures.py
python3 tests/automix_validation/scripts/generate_mock_analysis_fixtures.py
python3 scripts/run_fixture_coverage_audit.py \
  --project-name project \
  --output-dir automix
```

## Expected Result

- `automix/eval_reports/fixture_coverage_audit.json` exists.
- `automix/eval_reports/fixture_coverage_audit.md` exists.
- `passed` is `true`.
- No `required_fixture_category_missing:*` blocker appears.

## Required Categories

`clean_vocal`, `buried_vocal`, `muddy_vocal`, `harsh_vocal`,
`sibilant_vocal`, `suno_high_fizz`, `watery_smear`, `fake_stereo_halo`,
`over_limited_master`, `low_end_buildup`, `phase_issue`, `missing_plugin`,
`corrupted_config`, `dry_run`, `rollback`, `render_failure`, and
`feedback_mapping`.

## Limits

Fixture coverage proves only that the harness has examples for these scenarios.
It does not prove audio quality, user acceptance, or commercial readiness.
