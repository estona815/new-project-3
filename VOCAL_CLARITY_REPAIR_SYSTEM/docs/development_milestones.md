# Development Milestones

## Milestone 0 - Repository Audit And Build Baseline

Goal: understand current state and establish baseline evidence.

Must include:

- architecture audit
- build instructions and limitations
- test instructions
- current signal path map
- current risk list

Exit criteria:

- `docs/repository_audit.md` exists
- `docs/signal_path.md` exists
- build/test baseline is documented
- no DSP change included

## Milestone 1 - Safety Baseline

Goal: prevent crashes, invalid output, unsafe audio-thread behavior, and destructive fallback failures.

Key issues:

- parameter default unification
- parameter snapshot
- real-time safety audit
- safe fallback behavior
- numerical safety
- model output validation
- dry/wet correctness

Exit criteria:

- no known NaN/Inf path
- bypass returns dry
- DryWet 0 returns dry
- invalid model/output path falls back safely
- default is preservation-first

## Milestone 2 - Conservative Denoise Core

Goal: replace destructive hard suppression with bounded soft attenuation.

Exit criteria:

- soft-knee attenuation
- nonlinear Amount mapping
- MaxSuppressionDb gain floor
- frequency-dependent limits
- smoothing
- full-band collapse guard

## Milestone 3 - Source Preservation Guards

Goal: protect vocal, clarity, air, transients, harmonics, tilt, ambience, and stereo width.

Exit criteria:

- preserve parameters high by default
- preserve guards only reduce attenuation
- transient and spectral-tilt guards active
- residual source leakage policy exists

## Milestone 4 - DAW Prototype And Band Validation

Goal: validate REAPER/TDR Nova/ReaEQ/ReaXcomp/ReaFIR multiband decisions before porting.

Exit criteria:

- prototype routing exists
- residual monitor works
- band decision table exists
- port/reject recommendations documented

## Milestone 5 - M/S Dynamic Multiband DSP

Goal: port only validated dynamic multiband and M/S behavior into plugin DSP.

Exit criteria:

- M/S encode/decode is correct
- mono/stereo safe
- band count capped
- total attenuation budget enforced
- residual mode finite and aligned

## Milestone 6 - AI Model Safety And Training Redesign

Goal: make model output explicit, bounded, and source-preserving.

Exit criteria:

- ModelOutputType contract exists
- invalid output falls back
- model confidence/domain status exists
- no model output bypasses safety caps
- training/loss policy addresses source preservation

## Milestone 7 - Evaluation Harness

Goal: build A/B, residual, and source-preservation evaluation tools.

Exit criteria:

- original/processed/matched/residual reports
- synthetic CI assets
- source-preservation metrics
- human listening report
- CI-safe regression gate

## Milestone 8 - Presets, UI, Defaults

Goal: define safe factory presets and release-safe defaults.

Exit criteria:

- Preserve default
- Strong isolated
- factory presets explicit
- fresh default lock test
- UI/preset documentation

## Milestone 9 - Final QA And Release Candidate

Goal: validate DAW compatibility, automation, latency, CPU, packaging, and release blockers.

Exit criteria:

- RC QA report
- DAW matrix
- packaging validation
- manual listening sign-off
- no release blockers

## Dependency Graph

```text
Milestone 0
  -> Milestone 1
       -> Milestone 2
            -> Milestone 3
                 -> Milestone 4
                      -> Milestone 5
       -> Milestone 6 model validation can begin after safety fallback exists
       -> Milestone 7 basic harness can begin after safety baseline exists
Milestone 7 + Milestone 3
  -> Milestone 8 preset tuning
Milestone 1-8 frozen
  -> Milestone 9 release candidate QA
```

Hard rules:

- Do not implement multiband DSP before safety baseline.
- Do not tune presets before evaluation harness.
- Do not ship AI model path before output contract.
- Do not select Strong as default.
- Do not port surgical bands without DAW validation.
- Do not release without clean-input do-no-harm tests.

## Suggested Branch Names

- `audit/repo-signal-path`
- `safety/parameter-defaults`
- `safety/processblock-rt`
- `safety/model-output-validation`
- `dsp/conservative-soft-mask`
- `dsp/preserve-guards`
- `prototype/reaper-nova-session`
- `dsp/ms-multiband`
- `ml/model-output-contract`
- `eval/offline-harness`
- `presets/safe-defaults`
- `qa/release-candidate`

## Definition Of Done

For every issue:

- implementation complete
- tests added or justified
- build/test command run or inability documented
- no unrelated DSP change
- no new audio-thread unsafe operation
- no new NaN/Inf path
- bypass and dry/wet not broken
- defaults not made more aggressive
- documentation updated if behavior changed
- audio-quality risk stated

For audio DSP issues:

- synthetic test passes
- clean-input test passes when relevant
- residual checked when relevant
- source-preservation impact reported

## Definition Of Release Ready

- all P0 issues closed
- required P1 issues closed
- evaluation harness exists
- Preserve passes clean-input do-no-harm
- residual leakage low in Preserve
- factory presets validated
- Strong not default
- model output contract implemented if model path ships
- invalid model output falls back safely
- final QA report produced
- manual listening sign-off completed
- no release blockers remain
