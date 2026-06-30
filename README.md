# REAPER AutoMix / Mastering Assistant

This workspace contains a conservative REAPER-oriented AutoMix and mastering
assistant for user-owned Suno/AI-generated music, vocal stems, full mixes, stem
mixes, and rebeat projects.

It is not a one-click finalizer. Human listening remains required. The system
is designed to analyze sources, plan safe draft processing, protect the original
material, generate review evidence, and block final delivery until QC and human
review support the result.

## Core Principles

- Preserve original audio, REAPER tracks, routing, and master state.
- Prefer scan-only and dry-run planning before any draft creation.
- Treat Suno/AI sources as already processed unless evidence says otherwise.
- Use artifact reduction and conservative restoration language; do not claim
  flawless artifact cleanup.
- Keep the lead vocal, especially male lead where present, as the anchor.
- Keep female vocals, doubles, harmonies, and adlibs as support layers unless
  the user explicitly chooses otherwise.
- Block final delivery when review, A/B, QC, rollback, plugin validation, or
  unresolved user feedback is incomplete.

## Main Entry Points

- [QUICKSTART.md](QUICKSTART.md)
- [PIPELINE_ARCHITECTURE.md](PIPELINE_ARCHITECTURE.md)
- [AUDIO_ENGINEERING_NOTES.md](AUDIO_ENGINEERING_NOTES.md)
- [SUNO_AI_ARTIFACT_STRATEGY.md](SUNO_AI_ARTIFACT_STRATEGY.md)
- [docs/digicore_suno_ai_reaper_pipeline.md](docs/digicore_suno_ai_reaper_pipeline.md)
- [VOCAL_FIRST_MIXING_STRATEGY.md](VOCAL_FIRST_MIXING_STRATEGY.md)
- [MASTERING_QC_STANDARD.md](MASTERING_QC_STANDARD.md)
- [USER_FEEDBACK_REVISION_LOOP.md](USER_FEEDBACK_REVISION_LOOP.md)
- [TESTING_AND_HARNESS.md](TESTING_AND_HARNESS.md)
- [PLUGIN_FALLBACKS.md](PLUGIN_FALLBACKS.md)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [docs/github_integration_pipeline.md](docs/github_integration_pipeline.md)
- [docs/github_upload_readiness.md](docs/github_upload_readiness.md)
- [prompts/new_computer_codex_bootstrap.md](prompts/new_computer_codex_bootstrap.md)
- [CHANGELOG.md](CHANGELOG.md)

The operational runbook is [docs/automix_runbook.md](docs/automix_runbook.md).

## Codex Mix/Master Harness

This root also contains the reproducible harness requested in
[MIXMASTER_SPEC.md](MIXMASTER_SPEC.md). It uses `input/stems/` and
`input/reference/` as the only source discovery locations, keeps the full mix
reference muted and out of the master path, writes plugin/routing traces to
`work/traces/`, runs measurable QC under `work/qc/`, and packages delivery only
after required render and QC files exist.

For public GitHub handoff, the current portable bootstrap is environment-first:
it can clone cleanly, detect REAPER/Python/runtime availability, install the
bundled JSFX that are present in the repo, inventory visible plugins, build
asset manifests, and prepare trace/report scaffolding. It does not auto-learn
plugin semantics or grant external parameter-write safety from GitHub setup
alone.

Primary commands:

```sh
python3 scripts/run_github_upload_readiness.py --project-name reaper-automix --require-ready
python3 scripts/run_github_integration_smoke.py --output-dir automix
python3 tools/detect_environment.py
python3 tools/install_reaper_jsfx.py
python3 scripts/run_plugin_validation_preflight.py --project-name reaper-automix --output-dir automix
python3 tools/build_asset_manifest.py
python3 tools/run_reaper_pipeline.py --prepare
python3 tools/qc_audio.py work/renders/final_24bit_48k.wav
python3 tools/package_delivery.py
```

## Safe Workflow

1. Run plugin inventory, availability preflight, and semantic validation gates.
2. Run GitHub integration smoke checks through the orchestrator for portable
   diagnostics and future MCP/reapy bridge readiness without modifying REAPER.
3. Run prompt 41 smoke validation before real project work.
4. Run scan-only on the real project.
5. Review source classification, source handoff requests, stem requests, and
   plugin readiness.
6. Run source acceptance gate before treating any provided WAV as accepted
   export or stem evidence.
7. Run artifact evidence and signal audits before any artifact-focused cleanup plan.
8. Create recovery drafts only when source and plugin gates allow it.
9. Validate final render evidence before QC and approval readiness.
10. Validate final QC evidence against the primary WAV render.
11. Validate measured loudness-matched A/B preview evidence before human review.
12. Validate rollback evidence before approval readiness.
13. Record user feedback and resolve it only with evidence.
14. Run final approval evidence gate after human approval is recorded.
15. Run approval export readiness before asking for or finalizing approval.
16. Run final export only after accepted source, approval, final QC, and no
   unresolved feedback blockers.
17. Run the open risk register and risk root-cause rollup before remediation.
18. Validate deliverable package evidence after the ZIP is created.
19. Validate final delivery consistency across render, QC, A/B, approval, and
   package reports.
20. Run professional readiness audit before delivery.

## Current Delivery Language

Use cautious claims:

- artifact reduction
- artifact suppression
- conservative restoration
- perceived noise reduction
- human review required

Avoid claims that imply flawless cleanup, commercial equivalence, or reference
matching unless measured evidence and user review support them.
