# Changelog

## Unreleased

- Recorded `mwolla_v14_no_chop_max_clarity_hook_reprise_master` as the current
  user-approved baseline, including a manifest, approval report, verification
  wrapper, and pipeline/harness docs.
- Added GitHub upload readiness checks, new-computer Codex bootstrap docs, and
  dry-run JSFX installation helper for portable REAPER AutoMix handoff setup.
- Added a user feedback revision loop that classifies listening notes, creates
  dry-run action plans, and stores revision memory.
- Added unresolved feedback blockers to global QC and final export state
  resolution.
- Added evidence-gated feedback resolution requiring existing evidence, measured
  QC, loudness-matched A/B review, and human review.
- Added feedback-QC integration reports linking feedback items to diagnostic
  hypotheses, dry-run actions, QC metric snapshots, A/B review state, and
  remaining risks.
- Added an explicit no-feedback baseline mode for feedback revision memory so
  readiness audits can record that no listening notes exist without fabricating
  user review.
- Added conservative intent classification reports and CLI for vocal rescue,
  Suno artifact suppression, conservative cleanup, stem mix, full-mix polish,
  master-only, reels, and streaming-master routing.
- Added processing policy audit reports and CLI for chain-plan safety checks
  before automated application or final delivery.
- Added fixture coverage audit reports and CLI for synthetic audio/mock
  analysis scenarios, including Suno fizz, watery smear, phase, rollback,
  render-failure, and feedback-mapping coverage.
- Added requirements traceability audit reports and CLI mapping the project
  brief to implementation, docs, tests, and runtime evidence.
- Added open risk register reports and CLI to consolidate blockers, warnings,
  review items, source/plugin risks, and safe next actions before delivery.
- Added risk remediation plan reports and CLI that convert open risks into
  dry-run commands, required evidence, acceptance criteria, and disallowed
  unsafe shortcuts.
- Added risk root-cause rollup reports and CLI that compress repeated open-risk
  blockers into ordered root causes and next evidence actions without approving
  audio.
- Added plugin validation action plan reports and CLI that convert plugin
  availability and semantic validation blockers into plugin-level evidence
  actions without approving parameter writes.
- Added plugin availability resolution plan reports and CLI that turn
  unavailable plugins into explicit install, disable, or manual-review operator
  decisions without approving fallback writes.
- Added plugin availability decision gate reports and CLI that require an
  operator-acknowledged disable manifest before unavailable plugins are treated
  as disabled for automatic drafts.
- Added path hygiene audit reports and CLI for hardcoded local path detection,
  and switched Prompt41 audio/mock-project fixture paths to portable relative
  paths.
- Added plugin validation preflight reports and CLI to separate local plugin
  availability evidence from semantic parameter write safety.
- Added plugin semantic validation gate reports and CLI to audit passed,
  no-fake-success parameter validation reports before any automated writes.
- Added plugin semantic validation collection plan reports and CLI that turn
  missing or failed semantic validation into REAPER-observed report collection
  jobs without granting write safety.
- Added plugin semantic validation queue reports and CLI that package
  collectable REAPER-observed validation jobs into a runtime queue without
  opening REAPER or granting write safety.
- Added plugin semantic validation runtime collector package reports and CLI
  that generate a REAPER Lua raw-observation collector and operator runbook
  without creating passing validation evidence.
- Added plugin semantic validation runtime observation gate reports and CLI that
  validate raw REAPER collector observations before manual report authoring
  without granting write safety.
- Added source handoff readiness reports and CLI to separate current source
  file presence from accepted export source or isolated stem evidence.
- Added source acceptance gate reports and CLI to validate accepted-source or
  isolated-stem evidence with explicit user acceptance before final export
  packaging.
- Added artifact signal audit reports and CLI so artifact-focused work requires
  source, metric, or user-feedback evidence instead of zero-metric assumptions.
- Added artifact evidence gate reports and CLI to separate measured render/QC
  artifact metrics from report-only placeholders, source signals, and user
  feedback.
- Added A/B preview evidence gate reports and CLI to require real preview,
  original, and final WAV evidence plus measured loudness-match metrics before
  approval readiness.
- Added final render evidence gate reports and CLI to reject
  diagnostic/report-only render manifests, missing primary WAVs, hidden
  limiter/normalization flags, and source-path-as-render shortcuts.
- Added final QC evidence gate reports and CLI to validate passing measured QC
  metrics, file-integrity checks, true-peak ceiling evidence, and primary-WAV
  render linkage before approval readiness.
- Added final approval evidence gate reports and CLI to validate that recorded
  human approval references matched-loudness A/B review, final audio, and final
  QC evidence before delivery request.
- Added deliverable package evidence gate reports and CLI to validate ZIP
  integrity, package manifest size, required evidence files, supporting gates,
  original/master protection, and credential/raw-source exclusion before
  professional delivery readiness.
- Added final delivery consistency gate reports and CLI to cross-check render,
  QC, A/B preview, approval, package, project-state, and rollback evidence paths
  before professional delivery readiness.
- Added rollback evidence gate reports and CLI to validate original protection,
  rollback validation, rollback file presence, and safe rollback entries before
  delivery readiness.
- Added approval export readiness reports and CLI to check accepted source,
  render, A/B preview, project-state, feedback, and human approval evidence
  without inventing approval.
- Added CLI support for recording and resolving feedback via
  `scripts/run_feedback_revision_loop.py`.
- Added root-level professional delivery documentation entrypoints.
- Added professional readiness audit reports and CLI:
  `scripts/run_professional_readiness_audit.py`.
- Added final-delivery evidence validation for primary WAV renders, final render
  evidence gates, delivery ZIPs, project-state manifests, plugin mapping
  summaries, A/B previews, rollback registries, and rollback evidence gates.
- Added claim-language guard coverage for unsupported artifact cleanup,
  commercial, reference-match, and listening-approval claims.
- Added focused regression coverage for Prompt37 final export, Prompt40
  orchestrator, Prompt41 export blocking, Prompt45 feedback revision loop,
  Prompt46 professional docs, Prompt47 readiness audit, and Prompt48 intent
  classification, Prompt49 processing policy audit, Prompt50 fixture coverage
  audit, Prompt51 requirements traceability audit, Prompt52 open risk register,
  Prompt53 risk remediation planning, Prompt54 path hygiene audit, and Prompt55
  plugin validation preflight, Prompt56 source handoff readiness, Prompt57
  artifact signal audit, Prompt58 approval export readiness, and Prompt59
  source acceptance gate, Prompt60 plugin semantic validation gate, and Prompt61
  artifact evidence gate, Prompt62 A/B preview evidence gate, Prompt63 final
  render evidence gate, Prompt64 rollback evidence gate, Prompt65 final QC
  evidence gate, Prompt66 final approval evidence gate, and Prompt67 deliverable
  package evidence gate, Prompt68 final delivery consistency gate, Prompt69
  risk root-cause rollup, Prompt70 plugin validation action planning, and
  Prompt71 plugin availability resolution planning, and Prompt72 plugin
  availability decision gating, and Prompt73 plugin semantic validation
  collection planning, Prompt74 plugin semantic validation queue packaging, and
  Prompt75 plugin semantic validation runtime evidence gating, and Prompt76
  plugin semantic validation runtime collection packaging, and Prompt77 plugin
  availability operator decision packaging, and Prompt78 plugin semantic
  validation runtime collector packaging, and Prompt79 plugin semantic
  validation runtime observation gating, and Prompt80 plugin semantic validation
  runtime report authoring packaging, and Prompt81 plugin semantic validation
  runtime report authoring candidate gating.
