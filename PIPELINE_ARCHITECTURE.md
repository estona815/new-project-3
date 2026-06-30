# Pipeline Architecture

The pipeline is evidence-first and fail-closed. Stages may generate reports,
plans, and review packages without modifying REAPER projects.

## Stage Map

1. Plugin inventory and adapter validation
2. GitHub integration smoke and current bridge-readiness status
3. Source intake and project scan
4. Source classification
5. Intent classification
6. Processing policy audit
7. Vocal recovery analysis
8. Pitch triage and pitch safety
9. Vocal placement analysis
10. Reference matching or target profile comparison
11. Premaster safety
12. User feedback revision loop
13. Final export state resolution
14. Final render, QC, and deliverable package

## Core Packages

- `automix/plugins/`: plugin inventory, adapter confidence, and safe parameter
  writing support.
- `automix/github_integration/`: isolated GitHub-researched MCP/reapy bridge
  references, portable diagnostics, and dry-run-only adapter checks.
- `automix/intent/`: conservative intent classification for vocal rescue,
  Suno artifact suppression, stem mix, full-mix polish, master-only, reels, and
  streaming-master routes.
- `automix/safety/`: chain-plan processing policy audit for conservative
  dry-run, original protection, parameter-discovery, OTT, saturation, widening,
  limiter, and dry/wet limits.
- `automix/vocal_recovery/`: conservative Suno/AI vocal recovery planning.
- `automix/pitch/`: pitch safety and conservative pitch triage.
- `automix/vocal_placement/`: vocal-forward placement and sidechain planning.
- `automix/mastering/`: premaster safety analysis and policy.
- `automix/reference/`: reference and target profile comparison.
- `automix/feedback/`: user feedback intake, action mapping, revision memory,
  feedback-QC integration, and evidence-gated feedback resolution.
- `automix/export/`: final export state, render manifest, QC, packaging, and
  human approval gates.
- `automix/orchestrator/`: stage ordering, global QC, rollback registry, resume
  state, and report index.

## Fail-Closed Rules

- Scan-only modes do not modify REAPER projects.
- Draft modes require validated plugin mappings.
- Intent classification is report-only and must not apply processing.
- Chain plans must pass processing policy audit before final delivery.
- Recovery, placement, premaster, and export each require review evidence.
- Missing renders fail evaluation.
- Missing rollback metadata blocks applied-stage confidence.
- Unresolved user feedback blocks final export, and recorded feedback requires
  an inspectable feedback-QC integration report before delivery.
- Unsafe override creates review copies only and must not produce final-safe
  naming.
- Song-specific user-approved baselines must be backed by a manifest, final
  render paths, QC paths, and a verification harness before they can be treated
  as rollback/reference points. Current example:
  `reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/approved_baseline_manifest.json`.

## Reports

Reports live under:

- `automix/analysis_reports/`
- `automix/chain_plans/`
- `automix/eval_reports/`
- `automix/review/`
- `automix/rollback/`
- `automix/export/`
- `deliverables/`

Current state summary is generated as:

- `automix/eval_reports/current_state_summary.json`
- `automix/eval_reports/current_state_summary.md`

The report index is generated as:

- `automix/eval_reports/automix_report_index.json`
- `automix/eval_reports/automix_report_index.md`
