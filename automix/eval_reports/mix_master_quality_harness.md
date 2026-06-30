# Mix/Master Quality Harness

- Project: `project`
- Created UTC: `2026-06-05T10:49:55Z`
- Handoff valid: `True`
- Offline high-quality planning ready: `True`
- REAPER dry-run ready: `True`
- Applied parameter writes ready: `False`
- Delivery claims ready: `False`
- Render created by this harness: `False`

## Handoff Recipe

- Recipe: `target_genre_based_draft_mix_recipe`
- Type: `genre_based_draft`
- Mastering mode: `pre_master`
- Roles: `21`
- Roles with FX: `20`
- Reference master-only: `True`

## Action Plan

- `passed` `restore_validate_handoff`: ZIP handoff source-of-truth files, recipes, scripts, and tools must be complete before integration.
- `ready` `recipe_script_consistency_pass`: Use target_mix_recipe plus Lua recipe/scripts as the dry-run mix/master contract.
- `ready` `dry_run_stem_classification_and_routing`: Classify stems, build role buses, and verify reference/full-mix tracks stay out of PREMASTER BUS.
- `blocked` `semantic_plugin_validation`: High-quality automation must not write FX parameters until controls are semantically validated.
- `blocked` `source_acceptance`: Accepted stems/source exports are required before applied mix or premaster claims.
- `planning_ready` `high_quality_mix_plan`: Build vocal-first balance, role-bus routing, conservative FX, send returns, and premaster headroom plan.
- `planning_ready` `premaster_safety_plan`: Premaster remains draft-only until measured render, A/B, rollback, and final QC evidence exist.
- `blocked` `render_qc_ab_delivery_gates`: Delivery or high-confidence quality claims require final render evidence, QC metrics, and loudness-matched A/B.

## Blockers

- `ab_preview_evidence_missing_for_human_review`
- `accepted_source_or_stem_evidence_missing`
- `final_qc_evidence_missing_for_delivery_claims`
- `final_render_evidence_missing_for_delivery_claims`
- `plugin_semantic_validation_not_ready_for_parameter_writes`

## Warnings

- `Lua syntax needs target validation`
- `No audio/reference/renders included`
- `No reference matching without lawful reference audio`
- `Non-volume revision actions are mostly manual-check`
- `Plugin parameter mapping is conservative`
- `REAPER runtime not tested in this packaging environment`
- `no_reference_match_claim_without_lawful_reference_audio_analysis`
- `premaster_bus_not_declared_in_role_buses`
- `render_execution_intentionally_skipped`

## Claim Boundary

- This harness prepares and audits the high-quality mix/master path only.
- It does not render audio, approve delivery, or claim reference matching.
- Applied processing remains blocked until source acceptance and semantic plugin validation are ready.
