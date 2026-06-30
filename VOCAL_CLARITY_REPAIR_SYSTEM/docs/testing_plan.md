# Testing Plan

This plan defines tests required before any release candidate approval. Automated tests lock regressions; real REAPER renders and manual listening are still required.

## Test Layers

| Layer | Purpose | Current command/status |
| --- | --- | --- |
| JSON/schema validation | Catch malformed preset, policy, metadata files. | Covered by `run_rc_qa.sh`. |
| Python compile | Catch syntax/runtime import issues in harness modules. | Covered by `run_rc_qa.sh`. |
| Direct test runner | Run pytest-style tests without local pytest dependency. | Covered by `VOCAL_CLARITY_REPAIR_SYSTEM.eval.rc_qa`. |
| JSFX static/math tests | Lock safety formulas and default values. | `tests/test_vocal_ai_artifact_split_tamer_jsfx.py` |
| Model contract tests | Validate hypothetical model output bounding/fallback. | `tests/test_model_output_contract.py` |
| A/B harness tests | Validate metrics, reports, synthetic assets, external-render mode. | `tests/test_ab_quality_harness.py` |
| Preset policy tests | Validate factory presets, Strong isolation, release gates. | `tests/test_prompt8_preset_release_policy.py` |
| RC QA lock tests | Validate metadata, parameter freeze, quick matrix, docs. | `tests/test_prompt9_rc_qa_lock.py` |
| Prompt 10 handoff tests | Validate handoff docs and issue taxonomy. | `tests/test_prompt10_developer_handoff.py` |

## Primary Automated Command

```sh
VOCAL_CLARITY_REPAIR_SYSTEM/scripts/run_rc_qa.sh --output-dir /tmp/codex_vocal_rc_qa
```

Expected output:

- `rc_qa_summary.json`
- `rc_qa_summary.md`
- `release_gate_result.json`
- `release_gate_result.md`
- per-preset `run_metrics.json`
- block-size matrix reports
- sample-rate matrix reports

## Required Block Sizes

- 1
- 16
- 32
- 64
- 128
- 256
- 512
- 1024
- 2048
- 4096
- non-power-of-two 333

Expected:

- no crash
- no NaN/Inf
- no release gate failure
- no missing reports

## Required Sample Rates

- 44.1 kHz
- 48 kHz
- 88.2 kHz
- 96 kHz

Expected:

- no filter instability
- no band above Nyquist
- high-band guard remains safe
- no NaN/Inf

## Channel Layout Tests

Required before ship:

- mono
- stereo
- stereo with M/S enabled
- stereo with M/S disabled
- unsupported layouts if host supplies them

Expected:

- mono safe
- stereo safe
- M/S encode/decode correct
- unsupported layout falls back or is documented unsupported
- residual monitor finite

## Bypass And Dry/Wet Tests

Required:

- bypass dry
- host bypass if applicable
- DryWet 0 dry
- DryWet 0.25/0.5/0.75/1 finite
- fallback returns dry
- residual monitor ignored by bypass

## Automation Tests

Automate:

- Amount
- DryWet
- VocalPreserve
- ClarityPreserve
- AirPreserve
- TransientPreserve
- MaxSuppressionDb
- SideAmount
- SurgicalArtifactReduction
- MultibandMode
- ResidualMonitor

Expected:

- no crash
- no NaN/Inf
- no severe click
- no destructive gain collapse
- no audio-thread allocation

## Real-Audio Evaluation

Use Prompt 7 harness with REAPER-rendered processed WAVs for:

- clean vocal
- clean consonant vocal
- clean acoustic guitar
- clean drum transient
- vocal with hiss
- room tone vocal
- AI metallic vocal
- watery source-separated vocal
- stereo ambience
- full mix centered vocal

For each preset, collect:

- average noise reduction
- average and worst source preservation
- average and worst clarity
- average and worst air
- transient score
- residual cleanliness
- stereo score
- failure tags

## Manual Listening

Listen to:

- original
- processed loudness-matched
- residual
- Preserve
- Balanced
- Surgical
- Strong separately

Fail release if Preserve sounds dull/cloudy/lower fidelity, even if metrics pass.
