# Release Checklist

## Before Merge

- Run Python tests:

```bash
python3 -m unittest discover -s AI_BEAT_LOGIC_WORKFLOW/tests -v
```

- Run C helper tests:

```bash
make -C AI_BEAT_LOGIC_WORKFLOW/tools test
```

- Run dummy pipeline:

```bash
python3 AI_BEAT_LOGIC_WORKFLOW/tests/generate_dummy_audio.py
python3 AI_BEAT_LOGIC_WORKFLOW/src/main.py \
  --input AI_BEAT_LOGIC_WORKFLOW/tests/fixtures/dummy_suno_like.wav \
  --length-mode under_2min \
  --vocal-mode suppress \
  --melody-focus front \
  --drum-808 strong_controlled \
  --export-format wav24_48k \
  --save-logic-project false
```

## Verify Outputs

- Confirm final WAV exists in `05_FINAL_WAV/`.
- Confirm final WAV duration is readable.
- Confirm `06_QC_REPORT/qc_report.md` exists.
- Confirm `06_QC_REPORT/final_verification.json` exists.
- Confirm the CLI printed `COMPLETE` only after verification passed.
- Confirm QC report does not claim Logic processing if fallback was used.

## Clean Before Commit

- Remove generated final WAVs, temporary working WAVs, processing logs, and dummy run outputs unless intentionally committing test fixtures.
- Run `make -C AI_BEAT_LOGIC_WORKFLOW/tools clean`.
- Check `git status --short`.

## Merge

- Merge feature branches into `dev` in order.
- Run tests again on `dev`.
- Merge `dev` to `main` only after tests and dummy pipeline pass.

