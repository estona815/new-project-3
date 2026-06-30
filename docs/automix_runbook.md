# AutoMix Runbook

This runbook is the safe operating order for the local REAPER AutoMix /
Auto-FX Orchestrator assets in this workspace.

## Inventory First

Run `automix/scan_reaper_plugin_inventory.lua` before any automated FX decision.
After inventory, run the Prompt39 plugin intelligence audit:

```bash
python3 scripts/run_plugin_intelligence_audit.py --scan --report --dry-run --output-dir automix
```

Treat `automix/analysis_reports/plugin_inventory_audit.json` and
`automix/eval_reports/plugin_capability_report.md` as the current authority for
whether a plugin is detected, mapped, validated, or unsafe. A fuzzy match or
installed plugin name is not enough to write a parameter; the adapter must pass
the confidence gate and validation status must be `passed`.

## End-to-End AutoMix Workflow

Use Prompt40's orchestrator for one-command fail-closed runs:

```bash
python3 scripts/run_automix_orchestrator.py --mode scan_only --output-dir automix --dry-run
```

Recommended order:

1. Run plugin intelligence audit.
2. Run `scan_only`.
3. Review source classification and stem-required reports.
4. Run `safe_draft` only after plugin mappings are safe.
5. Listen to A/B for recovery, pitch, placement, and premaster.
6. Accept or reject drafts.
7. Run reference matching only if needed.
8. Rerun premaster after accepted reference changes.
9. Run `review_package`.
10. Run `final_delivery` only after human approval and QC pass.

## Smoke Validation Before Real Project Use

Before using a real user project, run Prompt41 validation:

```bash
python3 scripts/run_prompt41_smoke_validation.py --generate-fixtures --run-tests --mock-render --output-dir automix
```

Recommended checks:

1. Confirm full-mix pitch is blocked.
2. Confirm original protection checks pass.
3. Confirm rollback registry is created.
4. Confirm missing renders do not pass evaluation.
5. Confirm final export is blocked without approval.
6. If available, run real REAPER render validation.
7. Only then run `scan_only` on a real project.
8. Review reports before `safe_draft`.
The inventory step is read-only for original tracks and writes:

- `automix/plugin_inventory.json`
- `automix/plugin_inventory_report.md`

Do not use a plugin family for automation just because a fuzzy match exists.
Ambiguous matches require manual review.

## Pitch Correction On Already Mixed AI Sources

Always classify before pitch correction:

```sh
python3 automix/analyze_ai_pitch_source.py \
  --input /path/to/user_owned_source.wav \
  --track-name Lead_Vocal \
  --output-dir automix
```

Review:

- `automix/analysis_reports/Lead_Vocal_source_classification.json`
- `automix/analysis_reports/Lead_Vocal_pitch_analysis.json`
- `automix/chain_plans/Lead_Vocal_pitch_chain_plan.json`
- `automix/eval_reports/Lead_Vocal_pitch_report.md`

Pitch correction may be considered only when:

- the source is vocal-like;
- full-mix likelihood is not high;
- monophonic pitch confidence is sufficient;
- already-tuned score is not high enough to skip;
- the pitch adapter has high-confidence semantic mappings;
- the user goal allows pitch correction.

Skipping pitch correction is a valid successful safety outcome.

## Batch Pitch Triage

For a whole project, run the batch triage before creating any pitch draft:

```sh
python3 scripts/run_batch_pitch_triage.py \
  --project /path/to/session.rpp \
  --adapter-status-json automix/pitch_adapter_semantics.json \
  --output-dir automix \
  --dry-run
```

The default mode is `conservative_scan_only`. It parses the project or an
offline track manifest, classifies each track role, writes per-track triage
JSON, and produces a project decision matrix. It does not insert FX, render,
save the project, or change original tracks.

Batch outputs:

- `automix/analysis_reports/project_track_role_map.json`
- `automix/analysis_reports/{track_name}_pitch_triage.json`
- `automix/eval_reports/project_pitch_triage_matrix.json`
- `automix/eval_reports/project_pitch_render_plan.json`
- `automix/eval_reports/project_pitch_safety_score.json`
- `automix/eval_reports/project_pitch_batch_report.md`
- `automix/eval_reports/{track_name}_stem_required_report.md` when stems are needed
- `automix/rollback/project_pitch_rollback_index.json` when draft plans are created

Use `conservative_apply_drafts` only with explicit `--apply-drafts --dry-run`.
The Python command still creates plans only; actual REAPER draft creation must
be run through a separate, explicit applicator on a saved project copy.

Available batch modes:

- `conservative_scan_only`: default, report decisions only.
- `conservative_apply_drafts`: create draft and rollback plans only when
  explicitly enabled.
- `report_only`: write reports with no draft intent.
- `no_pitch_correction`: force all pitch decisions to skip.
- `force_review_all_vocals`: route vocal-like tracks to human review.
- `experimental_full_mix_drafts`: only for explicitly approved full-mix tests.

Correct skips must stay visible in the matrix and report. A skipped master,
full-mix reference, drum bus, instrumental bus, or unknown track is a successful
safety decision, not a missing feature.

## Suno / AI Vocal Recovery Before Pitch Correction

Prompt 34 adds a recovery gate before pitch correction. The goal is not to make
the vocal brighter, louder, wider, or more tuned. The goal is to determine
whether a conservative cleanup draft can reduce obvious AI artifacts without
damaging vocal identity, consonants, transients, body, stereo stability, or
emotion.

The batch scanner now writes:

- `automix/analysis_reports/{track_name}_vocal_recovery_analysis.json`
- `automix/chain_plans/{track_name}_vocal_recovery_chain_plan.json`
- `automix/eval_reports/{track_name}_vocal_recovery_report.md`
- `automix/eval_reports/{track_name}_vocal_recovery_iteration_history.json`
- `automix/eval_reports/project_vocal_recovery_matrix.json`
- `automix/rollback/{track_name}_vocal_recovery_rollback.json`

Safe order:

1. Classify source.
2. Analyze artifact profile.
3. Detect already-mixed processing.
4. Select conservative recovery policy.
5. Create recovery draft only.
6. Render A/B and difference.
7. Reject if the vocal becomes dull, thin, phasey, smeared, or less emotional.
8. Run pitch triage only after recovery passes or no recovery is needed.
9. Request an isolated stem if full-mix or source-separated damage is too high.

Recovery profiles do not contain pitch correction. Compression defaults to zero
for already compressed AI vocals, added reverb is avoided on wet vocals, stereo
widening is disabled on phasey vocals, and thin vocals are body-protected.

If recovery needs a draft and A/B renders are missing, pitch correction is
blocked or routed to manual review. This is intentional fail-closed behavior.

## Vocal Forward Placement Workflow

Prompt 35 adds a vocal-forward placement pass after recovery and pitch triage,
before final master preparation. Vocal-forward does not mean simply louder. For
AI vocals, plain gain boosts can expose fizz, metallic tone, phase problems, and
tuning artifacts.

Run a dry scan:

```sh
python3 scripts/run_vocal_placement_workflow.py \
  --project /path/to/session.rpp \
  --mode placement_scan_only \
  --dry-run
```

The workflow writes:

- `automix/analysis_reports/{track_name}_vocal_placement_analysis.json`
- `automix/chain_plans/{track_name}_vocal_placement_chain_plan.json`
- `automix/chain_plans/{track_name}_vocal_sidechain_routing_plan.json`
- `automix/eval_reports/{track_name}_vocal_placement_report.md`
- `automix/eval_reports/{track_name}_vocal_placement_iteration_history.json`
- `automix/eval_reports/project_vocal_placement_matrix.json`
- `automix/rollback/{track_name}_vocal_placement_rollback.json`

Safe order:

1. Analyze vocal recovery and pitch status.
2. Detect masking bands.
3. Prefer dynamic instrumental space over vocal gain.
4. Create draft routing only.
5. Use sidechain dynamic EQ conservatively.
6. Duck backing vocals and sends only when needed.
7. Render loudness-matched A/B.
8. Reject if the beat weakens, vocal gets harsh, stereo shifts, or AI artifacts
   become more exposed.

Placement plans do not add pitch correction or master limiting. Unknown
parameters are skipped, commercial plugins are not required, and routing changes
are planned as dry-run metadata before any REAPER applicator is enabled.

## Premaster Safety Layer

Prompt 36 adds a premaster safety pass after vocal recovery, pitch triage, and
vocal-forward placement. It is not a loudness race or a clarity restoration
stage. If the vocal is still buried, harsh, phasey, or artifact-heavy, the
correct result is `mix_revision_required`.

Run a dry scan:

```sh
python3 scripts/run_premaster_safety_workflow.py \
  --source-mix /path/to/mix.wav \
  --mode premaster_scan_only \
  --dry-run
```

The workflow writes:

- `automix/analysis_reports/project_premaster_safety_analysis.json`
- `automix/chain_plans/project_premaster_chain_plan.json`
- `automix/rollback/project_premaster_rollback.json`
- `automix/eval_reports/project_premaster_eval_metrics.json`
- `automix/eval_reports/project_translation_check.json`
- `automix/eval_reports/project_premaster_iteration_history.json`
- `automix/eval_reports/project_premaster_report.md`

Safe order:

1. Confirm placement/recovery/pitch gates are not rejected.
2. Analyze limiter pressure, crest factor, LRA, true peak, and AI artifact risk.
3. Detect mono compatibility, low-end stereo, and translation risks.
4. Select `safety_only_premaster`, `safe_streaming_premaster`,
   `already_mastered_safety`, or `mix_revision_required`.
5. Create draft-only chain plans using semantic controls.
6. Skip unknown or low-confidence adapter mappings.
7. Render loudness-matched A/B only after a separate draft render exists.
8. Reject or reduce processing if loudness comes with vocal/artifact/beat damage.

Premaster plans do not add pitch correction, exciters, strong high-shelf boosts,
OTT, aggressive multiband compression, or master widening. The original master
bus must remain untouched. The disabled REAPER applicator creates only a muted
`_PREMASTER_DRAFT` track on a saved project copy.

## Final Export And Deliverables Workflow

Prompt 37 creates the client-grade delivery folder after the accepted draft has
passed human review. It does not make an unsafe draft final just because a file
exists.

Diagnostic report-only run:

```sh
python3 scripts/run_final_export_packager.py \
  --project /path/to/session.rpp \
  --profile diagnostic_only \
  --diagnostic-only
```

Approved delivery run:

```sh
python3 scripts/run_final_export_packager.py \
  --project /path/to/session.rpp \
  --source-stage accepted_premaster_draft \
  --source-audio /path/to/accepted_premaster.wav \
  --original-mix /path/to/original_mix.wav \
  --profile professional_master_delivery \
  --approve \
  --acknowledge-warnings \
  --render \
  --make-ab-preview \
  --qc \
  --zip
```

Safe order:

1. Resolve accepted source stage.
2. Verify human approval.
3. Select export profile.
4. Render WAV first.
5. Render MP3 preview/delivery copies when an encoder is available.
6. Run final render evidence gate.
7. Run final QC on exported WAV.
8. Run final QC evidence gate.
9. Generate A/B preview montage.
10. Run A/B preview evidence gate.
11. Record final human approval after matched-loudness listening.
12. Run final approval evidence gate.
13. Run rollback evidence gate.
14. Build reports and manifests.
15. Create deliverables folder.
16. Create ZIP package.
17. Run open risk register and risk root-cause rollup.
18. Run deliverable package evidence gate.
19. Run final delivery consistency gate.
20. Mark `ready_for_delivery` only if QC passes and evidence gates are ready.

Outputs:

- `automix/export/final_export_state.json`
- `automix/review/final_human_approval.json`
- `automix/export/final_render_manifest.json`
- `automix/eval_reports/final_ab_preview_manifest.json`
- `automix/eval_reports/final_qc_metrics.json`
- `automix/eval_reports/final_qc_evidence_gate.json`
- `automix/eval_reports/final_qc_report.md`
- `automix/eval_reports/final_approval_evidence_gate.json`
- `automix/eval_reports/open_risk_register.json`
- `automix/eval_reports/risk_root_cause_rollup.json`
- `automix/eval_reports/risk_remediation_plan.json`
- `automix/eval_reports/deliverable_package_evidence_gate.json`
- `automix/eval_reports/final_delivery_consistency_gate.json`
- `automix/export/project_state_manifest.json`
- `automix/export/plugin_mapping_summary.md`
- `automix/export/deliverable_package_manifest.json`
- `deliverables/{project_slug}_DELIVERABLES_vXX/`

WAV is the primary deliverable. MP3-only final delivery is blocked. Unsafe
override exports must be named `UNSAFE_REVIEW_COPY`, never `FINAL_SAFE`.
The deliverable package evidence gate validates ZIP integrity and required
evidence files only; it does not approve audio or replace human listening.
The final delivery consistency gate checks that render, QC, A/B, approval, and
package reports point to the same evidence; it also does not approve audio.

## Reference Matching / Genre Targeting Workflow

Prompt 38 compares the current mix against user-provided reference files or a
genre target profile. It does not copy reference musical content. Safety
overrides matching.

Dry reference scan:

```sh
python3 scripts/run_reference_match_workflow.py \
  --project /path/to/session.rpp \
  --current-mix /path/to/current_mix.wav \
  --reference /path/to/reference.wav \
  --reference-role primary_reference \
  --target-profile digicore_hyperpop_hiphop_vocal_forward \
  --dry-run
```

Target profile only:

```sh
python3 scripts/run_reference_match_workflow.py \
  --project /path/to/session.rpp \
  --target-profile phone_reels_loud_clear \
  --mode target_profile_scan_only \
  --dry-run
```

Safe order:

1. Add reference files or choose target profile.
2. Analyze references and current mix.
3. Compare broad features only.
4. Generate safe adjustment priorities.
5. Block unsafe adjustments.
6. Create draft only if explicitly requested.
7. Render loudness-matched A/B.
8. Reject if the result becomes more AI-like, harsh, phasey, or worse at equal
   loudness.
9. Rerun premaster safety if the accepted reference-match draft changes mix
   balance.

Outputs:

- `automix/reference/reference_manifest.json`
- `automix/analysis_reports/current_mix_reference_features.json`
- `automix/eval_reports/reference_match_comparison.json`
- `automix/chain_plans/project_reference_match_adjustment_plan.json`
- `automix/rollback/project_reference_match_rollback.json`
- `automix/eval_reports/reference_match_eval_metrics.json`
- `automix/eval_reports/reference_match_report.md`
- `automix/eval_reports/project_reference_match_matrix.json`

Final export cannot use a reference-match draft unless it is accepted. Reference
files are not included in final deliverables unless the user explicitly requests
it and has rights.

## When To Skip AutoTune

Skip automatic pitch correction when:

- `classification` is `full_mix`;
- `classification` is `unknown`;
- `pitch_correction_risk` is `unsafe`;
- `full_mix_likelihood > 0.65`;
- `already_tuned_score > 0.85`;
- monophonic pitch confidence is low;
- key/scale confidence is low and strong scale correction would be required;
- source-separated artifacts are strong;
- plugin parameter mapping is uncertain.

If `already_tuned_score > 0.70`, use only skip or micro-correction policy. Do
not stack strong AutoTune on already tuned AI audio.

## When To Request An Isolated Vocal Stem

Request an isolated vocal stem when the report says:

- `full_mix_unsafe`
- `stem_required`
- high low-end/drum/transient evidence;
- high polyphonic contamination;
- vocal isolation confidence is low.

Full mixes should not be tuned as if they are monophonic vocal tracks.

Use isolated vocal stems whenever full-mix likelihood is high. If no isolated
stem exists, keep pitch correction disabled unless the user explicitly approves a
low-correction full-mix draft experiment.

## Draft-Only Pitch Application

`automix/apply_conservative_pitch_draft.lua` is disabled by default. To use it,
first create and review a chain plan, then test on a saved copy of the REAPER
project.

The applicator:

- requires exactly one selected original track;
- duplicates it to `_PITCH_DRAFT`;
- mutes the draft by default;
- inserts pitch correction only on the draft;
- discovers semantic parameters by name;
- skips unknown or low-confidence controls;
- writes rollback data;
- leaves the original track untouched.

The Lua applicator writes rollback metadata under `automix/rollback/` and checks
that the original track FX count, item count, name, routing count, and pitch-FX
state did not change.

Do not enable full-mix pitch experiments unless the user explicitly requests an
experimental draft and accepts mandatory A/B review.

## A/B Review

When a pitch draft is rendered, run:

```sh
python3 automix/analyze_ai_pitch_source.py \
  --input /path/to/original.wav \
  --processed /path/to/pitch_processed.wav \
  --track-name Lead_Vocal \
  --output-dir automix
```

Reject or iterate if the report flags:

- formant drift;
- metallic increase;
- clarity loss;
- air loss;
- transient loss;
- stereo/phase change;
- high difference source energy.

The goal is not maximum pitch lock. The goal is a better-sounding vocal that
does not become robotic, metallic, phasey, or fake.

## Prompt 32 Fail-Closed Layer

Prompt 32 adds a central `PitchSafetyGate`. It blocks correction when:

- full-mix likelihood is high;
- already tuned score is high;
- pitch confidence is low;
- source separation risk is high;
- plugin mapping confidence is low;
- required semantic controls are missing;
- damage metrics fail;
- A/B renders are missing.

The gate never strengthens correction during iteration. It only lowers
correction amount, slows speed, reduces wet mix, disables scale forcing, or
rejects pitch correction.

## Real Project Scan-Only Pilot

Prompt 42 adds `real_project_scan_only`, a strict read-only pilot for a real
REAPER project path. It writes audit reports only; it does not duplicate tracks,
insert plugins, write parameters, change routing, render final audio, or move
into safe_draft.

Recommended sequence:

1. Run Prompt 41 validation first if possible.
2. Provide the real REAPER project path.
3. Run the pilot in strict read-only mode:

```sh
python3 scripts/run_real_project_scan_only.py \
  --project "/path/to/project.rpp" \
  --target-profile digicore_hyperpop_hiphop_vocal_forward \
  --check-prompt41 \
  --strict-read-only \
  --dry-run
```

4. Confirm `automix/real_project/read_only_guard_report.json` reports
   `safe: true` and `modified: false`.
5. Review `automix/analysis_reports/real_project_track_audit.json`.
6. Review `automix/eval_reports/real_project_source_safety_map.json`.
7. Review `automix/eval_reports/real_project_plugin_readiness.json`.
8. Run `scripts/run_plugin_validation_preflight.py` to separate local plugin
   availability from semantic write-safety validation.
9. Run `scripts/run_source_handoff_readiness.py` to separate current source
   file presence from accepted source or isolated-stem evidence.
10. Run `scripts/run_artifact_signal_audit.py` before artifact-focused cleanup
    planning.
11. Provide isolated stems when the stem request plan requires them.
12. Validate plugin mappings before allowing any draft that writes parameters.
13. Only then consider safe_draft mode.

The scan-only report is:

- `automix/eval_reports/real_project_scan_only_report.md`

## Recovery-Only Pilot

Prompt 43 is the first applied pilot, but only for conservative vocal recovery
drafts. Pitch correction, vocal placement, reference matching, premaster, and
final export remain blocked.

Recommended sequence:

1. Run Prompt 41 validation.
2. Run Prompt 42 `real_project_scan_only`.
3. Review source safety and plugin readiness.
4. Run recovery-only dry-run first:

```sh
python3 scripts/run_recovery_only_pilot.py \
  --project "/path/to/project.rpp" \
  --from-scan-report automix/eval_reports/real_project_scan_only_report.md \
  --dry-run
```

5. If eligible tracks and validated plugin mappings exist, run with
   `--apply-drafts`.
6. Render A/B only with `--render-ab --apply-drafts`.
7. Listen manually before accepting recovery drafts.
8. Do not proceed to pitch unless recovery is accepted and the pitch safety gate
   allows it.

Important outputs:

- `automix/eval_reports/recovery_only_track_selection.json`
- `automix/eval_reports/recovery_only_pitch_block_report.json`
- `automix/eval_reports/recovery_only_ab_render_plan.json`
- `automix/eval_reports/recovery_only_original_protection_report.json`
- `automix/rollback/recovery_only_rollback_registry.json`
- `automix/eval_reports/recovery_only_pilot_report.md`

## Recovery Draft Human Review

Prompt 44 blocks all downstream use of recovery drafts until explicit human
review decisions are saved. Created drafts are not treated as accepted.

Recommended steps:

1. Run the recovery-only pilot.
2. Generate the recovery review form:

```sh
python3 scripts/run_recovery_review_gate.py \
  --project "/path/to/project.rpp" \
  --generate-form
```

3. Listen to original, recovery draft, loudness-matched A/B, and difference.
4. Accept only drafts that are better at matched loudness.
5. Use `accepted_light` for fragile AI vocals.
6. Reject drafts that are dull, thin, phasey, lispy, or less emotional.
7. Provide stems if source quality blocks recovery.
8. Proceed to vocal placement scan only after the review gate passes.

Important outputs:

- `automix/review/recovery_review_form.md`
- `automix/review/recovery_review_state.json`
- `automix/review/accepted_recovery_sources.json`
- `automix/orchestrator/downstream_recovery_gate.json`
- `automix/eval_reports/recovery_review_report.md`

Final export remains blocked after recovery acceptance until later placement,
premaster, QC, and approval gates pass.

## User Feedback Revision Loop

Prompt 45 records user mix/master feedback as evidence before any new
processing pass. It converts natural-language feedback into conservative
diagnostic actions, revision memory, and final-delivery blockers when feedback
is still unresolved.

Initialize the no-feedback baseline when a handoff or readiness audit needs
explicit evidence that no listening notes have been recorded yet:

```sh
python3 scripts/run_feedback_revision_loop.py \
  --output-dir automix \
  --project-name project \
  --initialize-baseline
```

The baseline writes empty memory and QC integration reports only. It does not
invent a listening review.

Record feedback:

```sh
python3 scripts/run_feedback_revision_loop.py \
  --output-dir automix \
  --project-name project \
  --pass-id v01 \
  --track-name "Lead Vocal" \
  --feedback "보컬이 뿌옇고 Suno fizz가 남아 있다."
```

Important outputs:

- `automix/review/user_feedback_revision_memory.json`
- `automix/eval_reports/user_feedback_action_plan.json`
- `automix/eval_reports/user_feedback_revision_report.md`

The action plan is dry-run evidence only. It may recommend checks such as vocal
mud, high fizz, M/S side cleanup, limiter pressure, or dynamic vocal-seat
carving, but it does not insert FX, write plugin parameters, render audio, or
claim improvement. If unresolved feedback exists, global QC blocks final
delivery until the issue is addressed with measured QC and human review.

## Final Vocal Space Finish

The finishing pass starts after a recovery source has been accepted by the
Prompt 44 human review gate. It creates a conservative vocal-space carving plan,
A/B render plan, protection report, review form, and optional review-only
package. It does not create final delivery files.

Recommended dry run:

```sh
python3 scripts/run_final_vocal_space_finish.py \
  --project "/path/to/project.rpp" \
  --dry-run \
  --make-review-package \
  --strict-protection
```

Important outputs:

- `automix/analysis_reports/finalizing_target_resolution.json`
- `automix/analysis_reports/final_vocal_space_analysis.json`
- `automix/chain_plans/final_vocal_space_carving_chain_plan.json`
- `automix/eval_reports/final_vocal_space_ab_render_plan.json`
- `automix/eval_reports/final_vocal_space_protection_report.json`
- `automix/review/final_vocal_space_review_form.md`
- `automix/eval_reports/finalizing_vocal_space_and_review_package_report.md`

Pitch correction, destructive mastering, and final export remain blocked. Do not
claim improvement until loudness-matched A/B and human review confirm it.

## Final Placement Adapter Validation

Before any REAPER vocal-space placement applicator can be enabled, validate the
semantic adapter mapping:

```sh
python3 scripts/run_final_placement_adapter_validation.py \
  --output-dir automix \
  --chain-plan automix/chain_plans/final_vocal_space_carving_chain_plan.json \
  --write-configured-applicator
```

This creates:

- `automix/eval_reports/final_placement_adapter_mapping_report.json`
- `automix/chain_plans/final_vocal_space_applicator_plan.lua`
- `automix/apply_final_vocal_space_placement_draft_configured.lua`

The configured applicator remains disabled unless the report has
`apply_allowed=true` and the operator explicitly requests
`--enable-configured-applicator`. The REAPER applicator does not save, render,
insert pitch correction, or edit the original master.
