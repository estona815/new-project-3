# Branch Strategy

Repository: `AI_BEAT_LOGIC_WORKFLOW`

This repository uses a stable `main`, an integration `dev`, and small feature branches. Feature work must merge into `dev` first. `main` receives only tested releases from `dev`.

## Permanent Branches

| Branch | Role | Rules |
|---|---|---|
| `main` | Stable branch only | Contains tested releases. Do not commit experimental work directly. |
| `dev` | Integration branch | All feature branches merge here first after tests pass. |

## Feature Branches

| Branch | Scope |
|---|---|
| `feature/00-project-scaffold` | Folder structure, README, CLI skeleton, config schema, default options |
| `feature/01-input-ingest-convert` | Input copy, filename sanitization, original preservation, ffmpeg/afconvert detection, working WAV conversion |
| `feature/02-c-wav-tools` | C WAV tools, Makefile, CLI usage docs |
| `feature/03-python-analysis-engine` | Python analysis engine and audio heuristics |
| `feature/04-edit-plan-generator` | `edit_plan.md` generation and Logic manual editing instructions |
| `feature/05-logic-pro-integration` | macOS/Logic Pro detection and optional automation without false success claims |
| `feature/06-fallback-processing` | Non-Logic trim/fade/gain staging and optional ffmpeg EQ fallback |
| `feature/07-export-qc-report` | Final WAV export, MP3 preview, metadata verification, `qc_report.md` |
| `feature/08-tests-docs-release` | Integration test, final README, troubleshooting, release checklist |

## Required Feature Workflow

1. Create each feature branch from `dev`.
2. Implement only that branch's scope.
3. Add or update verification commands.
4. Run the narrowest relevant checks first.
5. Commit with a clear message.
6. Merge back to `dev` only after tests pass.
7. Promote `dev` to `main` only for tested releases.

See `BRANCH_PLAN.md` for acceptance criteria, test commands, merge order, and rollback details.

