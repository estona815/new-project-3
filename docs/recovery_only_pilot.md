# Recovery-Only Pilot

Prompt 43 is the first applied AutoMix pilot, but it is recovery-only. It does
not run pitch correction, vocal placement, reference matching, premaster, final
export, or destructive cleanup.

## Why Recovery-Only First

Suno/AI-style vocals can become dull, watery, metallic, or smeared if pitch,
placement, and premaster changes are stacked before source repair is reviewed.
The first pilot therefore creates only muted recovery draft tracks for eligible
vocal-like sources, and only when plugin mappings and rollback safety are ready.

## Command

Dry run:

```sh
python3 scripts/run_recovery_only_pilot.py \
  --project "/path/to/project.rpp" \
  --from-scan-report automix/eval_reports/real_project_scan_only_report.md \
  --dry-run
```

Apply recovery drafts only:

```sh
python3 scripts/run_recovery_only_pilot.py \
  --project "/path/to/project.rpp" \
  --from-scan-report automix/eval_reports/real_project_scan_only_report.md \
  --apply-drafts \
  --strict-original-protection
```

Apply and render A/B:

```sh
python3 scripts/run_recovery_only_pilot.py \
  --project "/path/to/project.rpp" \
  --from-scan-report automix/eval_reports/real_project_scan_only_report.md \
  --apply-drafts \
  --render-ab \
  --strict-original-protection
```

`--render-ab` requires `--apply-drafts`. Dry-run is the default unless
`--apply-drafts` is explicit.

## Preconditions

The pilot requires Prompt 42 outputs:

- `automix/eval_reports/real_project_scan_only_report.md`
- `automix/eval_reports/real_project_safe_draft_readiness.json`
- `automix/analysis_reports/real_project_track_audit.json`
- `automix/eval_reports/real_project_source_safety_map.json`
- `automix/eval_reports/real_project_plugin_readiness.json`
- `automix/real_project/read_only_guard_report.json`

If Prompt 42 is missing or its read-only guard failed, recovery is not applied.

## Track Selection

Eligible roles are:

- `lead_vocal`
- `backing_vocal`
- `vocal_double`
- `adlib`
- `vocal_bus`

Blocked roles include instrumental, drum, bass, guitar, piano, synth, FX,
reverb/delay send, full-mix reference, master-related, and unknown tracks.

Full mixes are always blocked. Unknown tracks are blocked. Source-separated
vocals are allowed only with explicit source-separated rescue authorization and
only when the damage risk is not extreme.

## Pitch Block

Pitch correction is hard-blocked. The pilot writes:

- `automix/eval_reports/recovery_only_pitch_block_report.json`

The validation fails if a pitch plugin, pitch semantic control, pitch draft
name, or applied pitch chain appears in the recovery-only path.

## Plugin Safety

Every planned parameter write goes through:

- Adapter confidence gate
- Safe parameter writer
- Third-party plugin policy
- Safe range clamp
- Write log

Unknown and low-confidence controls are skipped. Commercial plugins are blocked
unless detected, mapped, and validated.

## Rollback

For each created draft, the pilot writes:

- `automix/rollback/{track_name}_recovery_only_rollback.json`

It also writes:

- `automix/rollback/recovery_only_rollback_registry.json`

Drafts are named `{original_track_name}_RECOVERY_DRAFT_v01` and muted by
default.

## A/B Review

If rendering is not explicitly enabled, only a render plan is created and
evaluation cannot pass. Manual listening remains required before accepting any
draft. The review checklist asks whether the draft became less metallic without
becoming dull, lispy, smeared, phasey, or simply quieter.

## Reports

- `automix/eval_reports/recovery_only_track_selection.json`
- `automix/eval_reports/recovery_only_pitch_block_report.json`
- `automix/logs/recovery_only_parameter_write_log.json`
- `automix/eval_reports/recovery_only_ab_render_plan.json`
- `automix/eval_reports/recovery_only_original_protection_report.json`
- `automix/rollback/recovery_only_rollback_registry.json`
- `automix/eval_reports/recovery_only_pilot_report.md`

Proceed to vocal placement or pitch triage only after recovery drafts are
accepted by human A/B review and the relevant safety gates allow the next stage.

