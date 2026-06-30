# Known Risks

## P0 - Safety / Crash / Destructive Audio

| Risk | Current status | Mitigation | Blocking? |
| --- | --- | --- | --- |
| NaN/Inf reaches output | JSFX static guards and tests exist. | Keep finite checks; run real REAPER render. | Blocks release if observed. |
| Bypass not dry | Static tests and JSFX bypass path exist. | REAPER manual bypass test still required. | Blocks release if observed. |
| DryWet 0 not dry | Static tests exist. | REAPER render test still required. | Blocks release if observed. |
| Model not ready causes garbage | No model backend ships; model contract falls back. | Do not claim AI Assist until backend exists. | Blocks model shipping. |
| Hard mask zeros source | Current JSFX uses bounded soft attenuation. | Preserve tests and residual listening. | Blocks if reintroduced. |
| Full-band collapse | Guard exists in JSFX. | Real audio residual/listening required. | Blocks release if observed. |
| processBlock allocation | No C++ processBlock; JSFX static audit passes. | Host validation still required. | Blocks if future processor allocates. |

## P1 - Source Preservation / Audio Quality

| Risk | Current status | Mitigation | Blocking? |
| --- | --- | --- | --- |
| Vocal presence loss | Preserve guards and metrics exist. | Prompt 7 real render and listening. | Blocks default release. |
| Consonant loss | Clarity preserve, transient guard, metrics. | Residual listening. | Blocks default release. |
| Air loss | Air preserve and air guard. | 8 kHz+ metric and listening. | Blocks default release. |
| Transient smear | Transient guard and impulse tests. | Drum/guitar transient render. | Blocks default release. |
| Harmonic removal | Harmonic preserve proxy exists. | Real source residual checks. | Blocks if obvious. |
| Stereo width collapse | M/S width guard and metrics. | Stereo ambience test. | Blocks default release. |
| Clean but low-fidelity output | Main product risk. | Guardrails, residual, do-no-harm gates. | Blocks release. |

## P2 - Workflow / Testing / Evaluation

| Risk | Current status | Mitigation | Blocking? |
| --- | --- | --- | --- |
| No direct JSFX offline renderer | Harness supports passthrough/external WAVs only. | Render in REAPER and feed external WAVs. | Blocks final audio approval. |
| No committed real audio assets | Synthetic assets exist; manifest placeholders exist. | Use private assets and archive reports. | Blocks final listening proof. |
| No golden audio baseline | Policy exists but golden set not captured. | Capture approved RC renders. | Blocks regression confidence. |
| `pytest` absent locally | Direct runner passes. | Install pytest in CI or keep direct runner. | Warning. |

## P3 - UX / Presets / Documentation / Release

| Risk | Current status | Mitigation | Blocking? |
| --- | --- | --- | --- |
| Strong mode confusion | Strong isolated in policy and tests. | UI/preset labeling in REAPER still manual. | Blocks if default/auto-selected. |
| Unsupported format claims | Docs state REAPER JSFX only. | Do not market VST3/AU/AAX. | Blocks release notes if false claim. |
| Packaging missing | No JSFX package manifest yet. | Add package checklist/artifact. | Blocks distribution. |
| DAW matrix incomplete | Checklist exists. | Manual host validation. | Blocks compatibility claims. |

## Unknowns

- Real vocal quality under Preserve on the user's target material.
- REAPER automation click behavior under fast slider jumps.
- Long-run CPU and denormal behavior in REAPER.
- Whether factory presets will be installed as actual REAPER presets or documented slider states.
- Future model backend shape, latency, sample-rate constraints, and output type.
- Future VST3/AU/AAX framework and parameter ID migration behavior.
