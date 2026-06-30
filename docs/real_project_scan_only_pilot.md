# Real Project Scan-Only Pilot

Prompt 42 is the first real-project pilot for the AutoMix orchestrator. It is
intentionally scan-only: it reads a REAPER project or mock project JSON and
writes audit reports, but it does not insert FX, duplicate tracks, change
routing, write plugin parameters, render final audio, approve drafts, or package
deliverables.

## Why Scan-Only

Real user sessions can contain unknown routing, unknown plugin mappings, already
processed AI vocals, source-separated stems, full mixes, references, and prior
FX chains. The pilot must first prove that it can describe the project and fail
closed before any safe_draft workflow is allowed.

## Command

```sh
python3 scripts/run_real_project_scan_only.py \
  --project "/path/to/project.rpp" \
  --target-profile digicore_hyperpop_hiphop_vocal_forward \
  --check-prompt41 \
  --strict-read-only \
  --dry-run
```

`--strict-read-only` and `--dry-run` are defaults. The CLI never transitions to
safe_draft.

## What The Audit Checks

- Prompt 41 validation status.
- Project context and existing track/FX structure.
- Track role heuristics.
- Source safety: vocal-like, full mix, AI/already processed, source-separated,
  stem-required, and unknown tracks.
- Plugin readiness from the Prompt 39 inventory/adapter audit.
- Dry-run chain proposals for recovery, pitch, placement, reference matching,
  premaster, and final export.
- Stem request requirements.
- Safe-draft readiness score and recommended next mode.

## Read-Only Guard

The guard snapshots the project before and after the scan:

- track count, names, and GUIDs;
- FX counts per track;
- media item counts;
- take pitch/playrate states;
- send/receive counts and routing summary;
- master FX count;
- project file timestamp, size, and SHA-256 hash.

If any field changes, the pilot is marked unsafe and the final recommendation is
`scan_failed_do_not_proceed`.

## Source Safety

Full mixes are unsafe for automatic vocal pitch correction. Source-separated
vocals and already tuned AI vocals are high-risk. Unknown tracks are skipped.
Stem-required tracks are written visibly into
`automix/eval_reports/real_project_stem_request_plan.md`.

## Plugin Readiness

Detected third-party plugins are not considered safe unless they are mapped and
validated by the adapter system. Stock/JSFX fallbacks are reported, but fallback
presence alone does not authorize parameter writes.

## Safe-Draft Readiness

The readiness score combines:

- Prompt 41 validation;
- read-only guard result;
- plugin mapping readiness;
- source quality;
- stem availability;
- report completeness;
- rollback registry presence.

Allowed next modes are:

- `run_prompt41_validation`
- `validate_plugin_mappings`
- `provide_isolated_stems`
- `scan_only_again`
- `safe_draft_recovery_only`
- `safe_draft_no_pitch`
- `safe_draft_full_pipeline`
- `manual_mix_required`

## Reports

- `automix/real_project/read_only_guard_report.json`
- `automix/analysis_reports/real_project_track_audit.json`
- `automix/eval_reports/real_project_source_safety_map.json`
- `automix/eval_reports/real_project_plugin_readiness.json`
- `automix/chain_plans/real_project_dry_run_chain_proposals.json`
- `automix/eval_reports/real_project_stem_request_plan.md`
- `automix/eval_reports/real_project_safe_draft_readiness.json`
- `automix/eval_reports/real_project_scan_only_report.md`

