# Developer Handoff Master

This is the Prompt 10 handoff index. It converts the prior prompt sequence into small, reviewable, testable development work.

## Current Architecture Summary

- Active plugin: REAPER JSFX.
- Active audio file: `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`.
- No JUCE/C++ `AudioProcessor`, `processBlock`, APVTS, VST3/AU/AAX, or model inference runtime exists in this repository.
- Evaluation harness exists and supports passthrough and externally rendered processed WAVs.
- Factory presets and release gates exist as JSON policy.
- Automated RC QA exists, but release is not approved until real renders and manual listening pass.

## Required Docs

- Handoff index: `docs/developer_handoff_master.md`
- Repository map: `docs/repository_audit.md`
- Signal path: `docs/signal_path.md`
- Milestones and dependency graph: `docs/development_milestones.md`
- Guardrails: `docs/audio_quality_guardrails.md`
- Issue list and PR policy: `docs/issue_breakdown.md`
- Testing plan: `docs/testing_plan.md`
- Preset policy: `docs/preset_policy.md`
- Release checklist: `docs/release_candidate_checklist.md`
- Known risks: `docs/known_risks.md`
- Parameter freeze: `docs/parameter_freeze_table.md`
- DAW compatibility: `docs/daw_compatibility_checklist.md`
- RC QA report: `reports/prompt9_final_rc_qa_report.md`

## Priority System

- P0: safety, crash, destructive audio
- P1: source preservation and audio quality
- P2: workflow, testing, evaluation
- P3: UX, presets, documentation, release

P0 must be handled before P1. P1 must be handled before preset tuning. P2 must exist before release decisions. P3 completes release readiness.

## Coding Agent Instructions

Every coding task must follow this sequence:

1. Inspect relevant files.
2. Summarize current behavior.
3. Identify risks.
4. Make a minimal patch.
5. Add or update tests.
6. Build or run available verification.
7. Run relevant tests.
8. Report changed files.
9. Report unresolved risks.
10. Do not claim audio improvement unless tested.

If tests cannot run, state why and provide exact commands for the developer.

## Non-Negotiable Product Rule

The project fails if the final plugin only sounds cleaner by removing source quality.

The correct product is:

`Source-preserving AI noise and artifact suppressor.`

The incorrect product is:

`Maximum noise remover.`

Every issue, PR, test, preset, and release decision must follow that principle.
