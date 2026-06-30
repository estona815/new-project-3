# Prompt54 Path Hygiene Manual Test Plan

## Purpose

Verify that source code does not contain hardcoded local user paths, and that
fixture/report paths are visible for handoff review.

## Commands

```sh
python3 tests/automix_validation/scripts/generate_synthetic_audio_fixtures.py
python3 tests/automix_validation/scripts/create_minimal_reaper_test_project.py
python3 scripts/run_path_hygiene_audit.py \
  --project-name project \
  --output-dir automix
```

## Expected Result

- `automix/eval_reports/path_hygiene_audit.json` exists.
- `automix/eval_reports/path_hygiene_audit.md` exists.
- `passed` is `true`.
- Source-code findings have zero blockers.
- Prompt41 fixture audio paths are relative, such as `audio/raw_vocal_like_mono.wav`.
- Prompt41 mock project media paths are relative, such as `../audio/raw_vocal_like_mono.wav`.

## Limits

Runtime reports may contain local evidence paths. That is informational for
handoff review, not proof of audio quality or delivery readiness.
