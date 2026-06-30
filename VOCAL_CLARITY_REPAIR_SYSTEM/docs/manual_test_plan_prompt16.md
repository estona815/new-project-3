# Manual Test Plan - Prompt 16 Evaluation Foundation

Prompt 16 does not make the plugin cleaner. It creates the measurement path that catches clean but low-quality results.

## Generate Synthetic Assets

```sh
python3 -m VOCAL_CLARITY_REPAIR_SYSTEM.eval.evaluation_harness \
  --generate-synthetic VOCAL_CLARITY_REPAIR_SYSTEM/audio_tests/generated \
  --preset Preserve \
  --output-dir eval_outputs/prompt16_preserve
```

Expected:

- `processed.wav` exists for each item.
- `processed_matched.wav` exists for each item.
- `residual.wav` exists for each item.
- `metrics.json` exists for each item.
- `report.md` exists for each item.
- `run_metrics.json` and `index.md` exist at run level.

## Evaluate Real Rendered Plugin Output

Render the JSFX in REAPER, then place outputs in the structure expected by `--processed-dir`, or add `processed_path` to the manifest.

```sh
python3 -m VOCAL_CLARITY_REPAIR_SYSTEM.eval.evaluation_harness \
  --manifest VOCAL_CLARITY_REPAIR_SYSTEM/audio_tests/manifest.json \
  --renderer external \
  --processed-dir path/to/rendered_outputs \
  --preset Preserve \
  --output-dir eval_outputs/real_preserve
```

## Listening Steps

For each item:

1. Listen to `original.wav`.
2. Listen to `processed_matched.wav`.
3. A/B original against processed matched.
4. Listen to `residual.wav`.
5. Read `metrics.json`.
6. Read `report.md`.

## Expected Results

Clean sine and harmonic-stack sources:

- residual should be very low.
- no heavy presence, clarity, or air loss.
- no NaN, Inf, or introduced clipping.

Hiss plus harmonic source:

- residual should contain more hiss than harmonic tone.
- some hiss may remain if removing it would damage the harmonic source.

Impulse and transient sources:

- residual should not contain excessive attack loss.
- transient preservation ratio should not collapse.

Vocal-like or AI-artifact proxies:

- artifact may remain.
- residual should not sound like ghost vocal, consonants, musical breath, or source ambience.

## Failure Meaning

If processed audio sounds cleaner but dull, cloudy, lower fidelity, or moved backward, do not approve the DSP change. Prompt 16 is specifically designed to make that failure visible.
