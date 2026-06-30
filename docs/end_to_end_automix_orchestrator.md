# End To End AutoMix Orchestrator

Prompt40 adds a one-command orchestration layer for the REAPER AutoMix /
Auto-FX workflow. It coordinates the existing analysis, plugin intelligence,
planning, review, rollback, QC, and final-export gates without assuming that
processing is safe.

## Workflow Overview

The orchestrator runs stages in a fixed dependency order:

1. plugin intelligence
2. project scan
3. track role detection
4. source classification
5. intent classification
6. vocal recovery analysis/draft/eval
7. pitch triage/draft/eval
8. vocal placement analysis/draft/eval
9. reference match analysis/draft/eval
10. premaster analysis/draft/eval
11. translation check
12. final export resolver/export/QC/package
13. professional readiness audit

Every stage writes a stage result. Skipped stages are visible and are not hidden
as success.

## Workflow Modes

- `scan_only`: default. Writes analysis and reports only.
- `safe_draft`: may create draft plans only when safety gates pass.
- `review_package`: creates review-oriented reports and preview package
  metadata, not final delivery.
- `final_delivery`: requires explicit final approval, acknowledged warnings,
  accepted source, and passing final QC.
- `diagnostic_continue`: continues analysis after blockers but cannot apply
  processing.

## Safety Gates

The orchestrator blocks processing when plugin mappings are missing, source
classification or intent classification says a stem or review-only route is
required, A/B evaluation is missing for applied stages, rollback integrity
fails, final approval is missing, QC fails, user feedback is unresolved, final
render/package/A-B preview evidence is incomplete, or delivery reports contain
unsupported claim language.

Skip can be a successful outcome. Examples:

- no pitch correction
- no premaster draft
- stem required
- manual review required
- final export blocked because approval is missing

## Draft-Only Processing

Python orchestration does not directly modify REAPER tracks. Later REAPER
applicators must be run explicitly and must consume the generated plans only
after the safety gates pass.

## Human Review

Final delivery is blocked unless the selected source stage is accepted, warnings
are acknowledged, final QC passes, user feedback is resolved with evidence, and
the professional readiness audit passes. The readiness audit also checks the
primary WAV render, delivery ZIP, project-state manifest, plugin mapping
summary, loudness-matched A/B preview, and rollback registry. `--approve-final`
does not override a QC failure or missing export source.

## Rollback

`automix/rollback/global_rollback_registry.json` aggregates rollback metadata
from every applied stage. If an applied stage has no rollback file, rollback
validation fails and final export is blocked.

## Resume

`automix/orchestrator/resume_state.json` detects previous manifests, marks
outputs stale when the project file changed after the previous run, and warns
when accepted/reviewable drafts may exist.

## Commands

```bash
python3 scripts/run_automix_orchestrator.py --project "/path/to/project.rpp" --mode scan_only --target-profile digicore_hyperpop_hiphop_vocal_forward
python3 scripts/run_automix_orchestrator.py --project "/path/to/project.rpp" --mode safe_draft --allow-recovery-drafts --allow-placement-drafts --allow-premaster-draft --render-ab --dry-run
python3 scripts/run_automix_orchestrator.py --project "/path/to/project.rpp" --mode review_package --package-review --render-ab --dry-run
python3 scripts/run_automix_orchestrator.py --project "/path/to/project.rpp" --mode final_delivery --allow-final-export --approve-final --acknowledge-warnings
```

Recommended workflow:

1. Run plugin intelligence audit.
2. Run `scan_only`.
3. Review source and intent classification plus stem-required reports.
4. Run `safe_draft` only after plugin mappings and intent classification are safe.
5. Listen to A/B for recovery, pitch, placement, and premaster.
6. Accept or reject drafts.
7. Run reference matching only if needed.
8. Rerun premaster after accepted reference changes.
9. Run `review_package`.
10. Run `final_delivery` only after approval, QC, feedback resolution, and
    readiness audit pass.
