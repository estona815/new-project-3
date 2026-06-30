# Issue Breakdown

All issues must be small, reviewable, and testable. Priority is exactly one of P0, P1, P2, or P3.

## Issue Template

```md
Issue title:
[Priority] Short title

## Objective
What this issue accomplishes.

## Background
Which prompt this issue comes from and why it matters.

## Scope
Files/classes/functions likely involved.

## Non-goals
What must not be changed.

## Implementation notes
Specific technical direction.

## Tests required
Unit tests, DSP tests, render tests, or manual checks.

## Acceptance criteria
Clear pass/fail criteria.

## Audio-quality guardrail
How this prevents clean-but-low-quality output.

## Risks
Potential side effects.

## Dependencies
Issues that must be completed first.

## Deliverables
Patch, tests, docs, report, or metrics.
```

## First Five Recommended Issues

### Issue 0.1 - [P0] Repository architecture and signal-path audit

## Objective
Map the active signal path before any DSP changes.

## Background
Prompt 10 requires an intake audit. This repo is currently JSFX-based, not JUCE/C++.

## Scope
`JSFX/vocal_ai_artifact_split_tamer.jsfx`, `eval/*`, `ml/*`, `presets/*`, `scripts/*`, `.github/workflows/*`, root `CMakeLists.txt`.

## Non-goals
No algorithm, preset, or sound changes.

## Implementation notes
Keep `docs/repository_audit.md` and `docs/signal_path.md` current.

## Tests required
Documentation test verifies required paths and missing components are stated.

## Acceptance criteria
Repository map, signal path, build/test baseline, and current risk list exist.

## Audio-quality guardrail
Prevents accidental work on the wrong code path.

## Risks
Audit can go stale if future C++ target is added.

## Dependencies
None.

## Deliverables
Audit docs.

### Issue 0.2 - [P0] Build and test baseline

## Objective
Confirm current build and test state.

## Background
Prompt 10 requires build/test baseline before implementation.

## Scope
`CMakeLists.txt`, `.github/workflows/*`, `tests/*`, `eval/rc_qa.py`, `scripts/run_rc_qa.sh`.

## Non-goals
No build system rewrite.

## Implementation notes
Document that local `cmake` and `pytest` are unavailable, and direct runner is the working baseline.

## Tests required
Run `VOCAL_CLARITY_REPAIR_SYSTEM/scripts/run_rc_qa.sh`.

## Acceptance criteria
Build limitations documented; available tests run; failures recorded.

## Audio-quality guardrail
Ensures future sound changes are compared against a known baseline.

## Risks
CI may differ from local machine.

## Dependencies
Issue 0.1.

## Deliverables
Baseline report and command.

### Issue 1.1 - [P0] Unify denoise parameter defaults

## Objective
Keep DSP/UI/preset defaults in one source of truth.

## Background
Prompt 1/8 require preservation-first defaults and preset compatibility.

## Scope
JSFX sliders, `presets/factory_presets_safe_defaults.json`, `docs/parameter_freeze_table.md`, preset tests.

## Non-goals
No retuning without Prompt 7 report.

## Implementation notes
Preserve default: Amount 30%, DryWet 70%, MaxSuppressionDb 8 dB, MaskStrength 0.35, high preserve values.

## Tests required
Fresh default lock test; factory preset validation; legacy missing-value test.

## Acceptance criteria
JSFX defaults and preset JSON match; Strong not default; old presets load with safe defaults.

## Audio-quality guardrail
Prevents accidental aggressive default that sounds clean but damaged.

## Risks
Changing JSFX slider defaults can affect new instances.

## Dependencies
Issue 0.1.

## Deliverables
Default source file, tests, docs.

### Issue 1.2 - [P0] Add processBlock parameter snapshot

## Objective
Read and clamp parameters once per audio block in a future C++ processor.

## Background
Prompt 1 requires no repeated APVTS reads inside inner loops. Current active path is JSFX, so this issue applies when a C++ processor exists.

## Scope
Future `AudioProcessor::processBlock`, parameter manager/APVTS.

## Non-goals
No DSP algorithm change.

## Implementation notes
Create immutable snapshot containing Amount, DryWet, MaxSuppressionDb, MaskStrength, preserve controls, inference/bypass flags.

## Tests required
Unit test for clamping and no allocation if framework supports it.

## Acceptance criteria
No inner-loop APVTS reads; all values clamped; bypass/dryWet included.

## Audio-quality guardrail
Prevents inconsistent automation reads from creating sudden destructive attenuation.

## Risks
Not directly actionable until C++ processor exists.

## Dependencies
Issue 0.1 and future C++ target.

## Deliverables
Snapshot struct, tests, docs.

### Issue 1.4 - [P0] Safe fallback behavior

## Objective
Return dry or previous stable state on every invalid processing condition.

## Background
Prompt 1 requires safe bypass/model/error behavior.

## Scope
JSFX fallback path now; future C++ processor/model path later.

## Non-goals
No new denoise strength.

## Implementation notes
Fallback for bypass, disabled processing, bad input/output, invalid model, unsupported layout, empty block, numerical instability.

## Tests required
Bypass dry, ProcessingEnabled off dry, NaN/Inf sanitization, silence, DryWet 0.

## Acceptance criteria
No crash, no garbage, no silence unless input silence, residual mode does not leak into bypass.

## Audio-quality guardrail
When uncertain, preserve source instead of producing damaged cleanup.

## Risks
Fallback transitions can click if not smoothed in future C++ path.

## Dependencies
Issue 1.1.

## Deliverables
Patch/tests/report.

## Milestone Issue List

| Issue | Priority | Title | Dependencies | Tests required | Acceptance summary |
| --- | --- | --- | --- | --- | --- |
| 0.1 | P0 | Repository architecture and signal-path audit | none | doc test | map, signal path, risks |
| 0.2 | P0 | Build and test baseline | 0.1 | RC QA command | build/test baseline recorded |
| 0.3 | P0 | Current audio behavior baseline | 0.1, 0.2 | external render if available | bad behavior documented |
| 1.1 | P0 | Unify denoise parameter defaults | 0.1 | preset/default tests | single source of truth |
| 1.2 | P0 | Add processBlock parameter snapshot | future C++ target | snapshot tests | clamped block snapshot |
| 1.3 | P0 | Real-time safety audit and patch | 0.1 | static/host tests | no unsafe audio-thread ops |
| 1.4 | P0 | Safe fallback behavior | 1.1 | bypass/error tests | dry fallback on invalid state |
| 1.5 | P0 | STFT/mask numerical safety | future STFT path | numerical tests | finite/clamped gain |
| 1.6 | P0 | Model output validation | model path | model contract tests | invalid output falls back |
| 1.7 | P0 | Dry/Wet correctness | 1.4 | dry/wet tests | wet 0 dry, bypass dry |
| 2.1 | P0 | Replace hard mask with soft attenuation | 1.x | soft-mask tests | no binary zeroing |
| 2.2 | P0 | Add nonlinear Amount mapping | 2.1 | amount curve tests | conservative mapping |
| 2.3 | P0 | Make MaxSuppressionDb main cap | 2.1 | gain floor tests | no zero collapse |
| 2.4 | P1 | Frequency-dependent suppression limits | 2.3 | band limit tests | presence/air protected |
| 2.5 | P1 | Time and frequency smoothing | 2.1 | smoothing tests | no chatter/bin holes |
| 2.6 | P1 | Full-band collapse guard | 2.3 | collapse tests | source-wide collapse prevented |
| 3.1 | P1 | Add preserve parameters | 1.1 | default tests | high preserve defaults |
| 3.2 | P1 | Add frequency preserve weights | 3.1 | band tests | 2-16 kHz protected |
| 3.3 | P1 | Apply preserve guards | 3.2 | attenuation tests | guards only reduce attenuation |
| 3.4 | P1 | Transient detection and preserve | 3.1 | impulse/burst tests | attacks protected |
| 3.5 | P1 | Harmonic preservation guard | 3.1 | harmonic tests | harmonics not removed |
| 3.6 | P1 | Spectral tilt and air loss guards | 3.2 | tilt/air tests | darkening reduced |
| 3.7 | P1 | Residual source-leakage warning | 7.4 | residual metrics | source leakage flagged |
| 4.1 | P2 | Build REAPER prototype template | 2, 3 | manual REAPER check | routing documented |
| 4.2 | P2 | TDR Nova/ReaEQ/ReaXcomp/ReaFIR docs | 4.1 | doc review | safe chain settings |
| 4.3 | P2 | Band decision log template | 4.1 | doc review | every band justified |
| 4.4 | P2 | Prototype preset evaluation | 4.1, 7 | metrics/listening | port recommendations |
| 5.1 | P1 | DynamicMultibandSuppressor module | 4.4 | DSP tests | bounded preallocated bands |
| 5.2 | P1 | M/S encode/decode path | 5.1 | M/S tests | mono/stereo safe |
| 5.3 | P1 | Preserve/Balanced/Surgical layouts | 5.1 | band tests | capped layouts |
| 5.4 | P1 | Artifact score detector | 5.1 | detector tests | not raw-level only |
| 5.5 | P1 | Total attenuation budget | 5.1 | budget tests | no stacked over-reduction |
| 5.6 | P1 | Residual monitor output mode | 5.2 | residual tests | finite aligned residual |
| 6.1 | P0 | ModelOutputType contract | 1.4 | model tests | unknown rejected |
| 6.2 | P0 | Safe model postprocessing | 6.1 | model tests | output bounded |
| 6.3 | P1 | Model confidence/domain status | 6.1 | confidence tests | uncertainty reduces influence |
| 6.4 | P1 | Inference real-time safety audit | 6.1 | RT tests | no model loading in audio path |
| 6.5 | P2 | Training/loss redesign doc | 6.1 | doc review | do-no-harm loss policy |
| 7.1 | P2 | Offline render harness | 1.4 | harness tests | original/processed/residual |
| 7.2 | P2 | Test asset manifest | 7.1 | manifest tests | categories annotated |
| 7.3 | P2 | Synthetic test generator | 7.1 | synthetic tests | deterministic CI audio |
| 7.4 | P2 | Source-preservation metrics | 7.1 | metrics tests | severe damage fails |
| 7.5 | P2 | Human listening report | 7.1 | report tests | A/B residual report |
| 7.6 | P2 | CI synthetic regression gate | 7.3, 7.4 | RC QA | automated gate |
| 8.1 | P1 | Factory preset implementation | 7.4 | preset tests | explicit values |
| 8.2 | P1 | Fresh default lock test | 8.1 | default tests | Preserve default |
| 8.3 | P2 | UI simplification | 8.1 | UI/manual | safe controls |
| 8.4 | P2 | Preset evaluation and tuning report | 7.4, 8.1 | Prompt 7 reports | pass/fail gates |
| 8.5 | P3 | Documentation update | 8.1 | doc tests | user/preset docs |
| 9.1 | P0 | Final real-time safety audit | 1.x | static/host tests | no unsafe ops |
| 9.2 | P0 | Block size/sample rate/channel tests | 7.6 | matrix tests | no NaN/Inf |
| 9.3 | P0 | Bypass/dry-wet/latency validation | 1.7 | impulse tests | dry/latency correct |
| 9.4 | P1 | Automation/mode-switch stress | 9.2 | automation tests | no crash/click |
| 9.5 | P1 | DAW compatibility matrix | 9.2 | manual host tests | supported hosts documented |
| 9.6 | P1 | CPU/memory/long-run stability | 9.2 | performance tests | bounded CPU/memory |
| 9.7 | P2 | Final Prompt 7 evaluation | 8.4 | external render gate | final audio report |
| 9.8 | P3 | Packaging, release notes, RC report | 9.7 | package review | RC package docs |

## PR Policy

- One PR solves one issue or a tightly related group.
- No drive-by DSP changes.
- No silent default changes.
- No preset tuning without evaluation.
- No model changes without model output validation.
- No Strong mode as default.
- No post-EQ/exciter clarity compensation unless explicitly approved later.
- No processBlock allocation.
- No audio-thread logging.
- No hidden behavior changes without tests.

Every PR must include:

- summary
- files changed
- risk level
- tests run
- audio tests run if relevant
- before/after behavior
- residual notes if DSP changed
- known limitations

Do not merge if:

- build/tests fail
- NaN/Inf path is possible
- bypass or dry/wet breaks
- fresh default becomes aggressive
- source preservation regresses without explicit approval
- residual contains obvious source leakage in default tests

## First Five Issues To Implement

For a new developer starting from scratch:

1. `[P0] Repository architecture and signal-path audit`
2. `[P0] Build and test baseline`
3. `[P0] Unify denoise parameter defaults`
4. `[P0] Add processBlock parameter snapshot` if/when C++ processor exists
5. `[P0] Safe fallback behavior`

Do not begin with multiband, M/S, surgical notches, AI training, preset tuning, Strong mode, or UI polish.
