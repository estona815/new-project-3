# Prompt41 Smoke Validation

Prompt41 creates a synthetic and mock-project validation suite for the REAPER
AutoMix / Auto-FX Orchestrator before it is used on an important real project.

The suite uses generated audio and mock metadata so it does not require
copyrighted material, paid plugins, or a user's real REAPER session.

## Why Synthetic Fixtures

Synthetic fixtures let the safety layer exercise known edge cases:

- raw mono vocal-like material
- already tuned AI-like vocal material
- watery source-separated vocal material
- dense full-mix material
- fragile thin AI vocal material
- harsh sibilant vocal material
- clean instrumental bus material
- buried vocal mix material

The goal is not to prove mix quality. The goal is to prove that unsafe actions
are blocked and that reports are written even when processing is skipped.

## Fixtures

- `raw_vocal_like_mono.wav`: monophonic pitch confidence and low full-mix risk.
- `already_tuned_ai_like_vocal.wav`: already-tuned pitch should not receive
  strong correction.
- `source_separated_watery_vocal.wav`: watery/phasey extraction risk.
- `full_mix_dense_polyphonic.wav`: full-mix pitch must be blocked.
- `fragile_thin_ai_vocal.wav`: body preservation and no high boost.
- `harsh_sibilant_vocal.wav`: harshness/sibilance guard risk.
- `clean_instrumental_bus.wav`: instrumental role, pitch ineligible.
- `vocal_buried_mix.wav`: masking/placement analysis case.

## Run Mock Validation

```bash
python3 scripts/run_prompt41_smoke_validation.py --generate-fixtures --run-tests --mock-render --output-dir automix
```

Default behavior also uses mock render mode:

```bash
python3 scripts/run_prompt41_smoke_validation.py
```

## Run Real REAPER Validation

Only run real render validation on synthetic/minimal test projects, never on a
user's real project:

```bash
python3 scripts/run_prompt41_smoke_validation.py --generate-fixtures --run-tests --real-render --output-dir automix
```

If REAPER is unavailable, real render validation is skipped or reported as
partial. Missing renders must never pass evaluation.

## Interpret Results

- `PROMPT41_VALIDATION_PASS`: mock validation safety tests passed.
- `PROMPT41_VALIDATION_PARTIAL`: core safety passed but requested real render
  validation was unavailable or skipped.
- `PROMPT41_VALIDATION_FAIL`: a safety, report, rollback, export, or blocking
  behavior failed.

Partial is acceptable only when REAPER rendering is unavailable and the mock
render path still proves that missing renders cannot pass.

## Before Real Projects

Before using a real project:

1. Run Prompt41 mock validation.
2. Confirm full-mix pitch is blocked.
3. Confirm original track and master protection checks pass.
4. Confirm rollback registry is created.
5. Confirm missing renders do not pass evaluation.
6. Confirm final export is blocked without approval.
7. Run real REAPER validation if available.
8. Run `scan_only` on the real project.
9. Review reports before `safe_draft`.

## Troubleshooting

- If fixture generation fails, check write permissions under
  `tests/automix_validation/fixtures/`.
- If source classification expectations fail, inspect
  `automix/validation_reports/prompt41_validation_summary.json`.
- If final export proceeds without approval, treat the suite as failed.
- If low-confidence plugin parameters are written, treat the suite as failed.
- If rollback registry is missing for an applied stage, treat the suite as
  failed.
