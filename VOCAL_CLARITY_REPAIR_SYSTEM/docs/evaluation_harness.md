# Evaluation Harness

Prompt 16 result: measurement foundation only. No denoise algorithm, EQ boost, exciter, M/S logic, dynamic multiband suppressor, surgical notch bank, AI model, preset retune, or Strong mode change was added.

## Implementation Note

- AudioProcessor file: NOT FOUND.
- processBlock file/function: NOT FOUND.
- active audio path: `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`, JSFX `@sample`.
- dry copy location: JSFX `in_l = spl0`, `in_r = spl1`.
- processed signal location: JSFX `proc_l` / `proc_r` before dry/wet.
- dry/wet location: JSFX `out_l = in_l + (proc_l - in_l) * wet_state`.
- latency handling if any: metadata and active JSFX report zero latency; harness residual alignment currently uses no compensation.
- test framework location: direct Python tests under `tests/`, run through `VOCAL_CLARITY_REPAIR_SYSTEM/eval/rc_qa.py`.
- scripts folder: `VOCAL_CLARITY_REPAIR_SYSTEM/scripts/`.
- existing audio test assets: `VOCAL_CLARITY_REPAIR_SYSTEM/audio_tests/manifest.json` placeholders plus deterministic synthetic generator.
- offline render possibility: `evaluation_harness.py` supports `passthrough` and `external` rendered WAVs. Direct JSFX execution outside REAPER is not available.

## Entry Points

Generate synthetic assets and run the foundation evaluator:

```sh
python3 -m VOCAL_CLARITY_REPAIR_SYSTEM.eval.evaluation_harness \
  --generate-synthetic VOCAL_CLARITY_REPAIR_SYSTEM/audio_tests/generated \
  --preset Preserve \
  --output-dir eval_outputs/prompt16_preserve
```

Evaluate one WAV file:

```sh
python3 VOCAL_CLARITY_REPAIR_SYSTEM/scripts/plugin_eval.py \
  --input path/to/input.wav \
  --preset Preserve \
  --output-dir eval_outputs/single_file
```

Evaluate external REAPER/plugin renders:

```sh
python3 -m VOCAL_CLARITY_REPAIR_SYSTEM.eval.evaluation_harness \
  --manifest VOCAL_CLARITY_REPAIR_SYSTEM/audio_tests/manifest.json \
  --renderer external \
  --processed-dir path/to/rendered_outputs \
  --preset Preserve \
  --output-dir eval_outputs/external_preserve
```

## Output Structure

For each input item:

```text
eval_outputs/
  Preserve/
    item_id/
      original.wav
      processed.wav
      processed_matched.wav
      residual.wav
      metrics.json
      report.md
    run_metrics.json
    index.md
```

## Residual Definition

```text
residual.wav = inputAligned - processedAligned
```

For plugin-side residual monitor:

```text
residual = dryInput - processedBeforeDryWet
```

The current JSFX has zero reported latency. Future latency must be compensated before residual scoring.

## Metrics

Level metrics:

- input / processed RMS and RMS dB
- RMS delta dB
- peak and peak dB
- clipping counts
- matched gain dB for `processed_matched.wav`

Band metrics:

- low: `20 Hz..120 Hz`
- low_mid: `120 Hz..350 Hz`
- body: `350 Hz..1 kHz`
- nasal: `1 kHz..2 kHz`
- presence: `2 kHz..5 kHz`
- clarity: `4 kHz..8 kHz`
- air: `8 kHz..min(16 kHz, Nyquist)`
- full: `20 Hz..Nyquist`

Preservation metrics:

- presence_loss_db
- clarity_loss_db
- air_loss_db
- spectral_tilt_loss_db
- transient_preservation_ratio

Residual metrics:

- residual_rms_db
- residual_presence_ratio_db
- residual_clarity_ratio_db
- residual_air_ratio_db
- residual_transient_score
- source_leakage_score

Safety metrics:

- NaN count
- Inf count
- clipping count

## Warning Thresholds

Preserve mode initial thresholds:

- presence loss over `2 dB`: fail/warning depending severity
- clarity loss over `2 dB`: fail/warning depending severity
- air loss over `3 dB`: fail/warning depending severity
- transient loss over `2 dB`: fail/warning depending severity
- residual source leakage over threshold: fail/warning depending preset
- NaN/Inf: fail
- introduced clipping: fail

These are first-pass guardrails. They should not replace listening.

## Limitations

- The harness does not instantiate JSFX directly.
- `passthrough` validates the measurement pipeline, not denoise quality.
- `external` requires REAPER or another render path to produce processed WAVs.
- Real vocal and AI-artifact assets are not committed.
- Metrics are approximate and intentionally conservative; residual listening remains required.

The purpose is to make a clean but low-quality result visible before future DSP changes are accepted.
