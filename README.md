# AI_SUNO_VOCAL_REPAIR_REAPER_HARNESS

This repository is a GitHub-ready harness for a future REAPER/Suno vocal repair automation system. It is not the final audio project, it does not contain private music, and it should not perform real installation or real audio processing on a public/shared computer.

## Modes

### Public PC Mode

Use this mode on shared, company, school, library, or temporary computers.

- Create documentation, scripts, dry-run checks, templates, and plans only.
- Do not install REAPER extensions, audio plugins, DAWs, AI models, or package-heavy tools.
- Do not log into GitHub, iLok, Soundtoys, Valhalla, Plugin Alliance, Antares, Suno, or any music account.
- Do not store or process real audio.
- Do not commit credentials, licenses, API keys, private media, or personal files.

### Local Production Mode

Use this mode only on the main trusted music production computer.

- Clone this repo.
- Review `PUBLIC_PC_RULES.md`, `SECURITY.md`, and `INSTALL_PLAN.md`.
- Run dry-run install scripts first.
- Execute real installation only with explicit flags such as `--execute` or `EXECUTE_INSTALL=1`.
- Test with dummy audio before any real Suno vocal repair work.

## Repository Purpose

The harness prepares:

- REAPER extension installation planning
- REAPER automation scripting
- Suno vocal cleanup workflow design
- Source separation setup planning
- Denoise candidate generation planning
- REAPER FX chain blueprints
- Render automation stubs
- QC report generation stubs
- Local-machine bootstrap instructions
- Free/recommended plugin expansion planning for future REAPER vocal repair
- Public-source mixing/mastering knowledge base scaffolding

## Mixing Knowledge Base Layer

The knowledge base layer lives in `knowledge_base/`, `decision_engine/`, `docs/research_method/`, and `codex_prompts/15_*` through `codex_prompts/19_*`.

It is a public-safe research and decision layer. Public resources are tracked as links, metadata, short paraphrased notes, and original workflow conclusions. They are not copied into the repo as full articles, manuals, YouTube transcripts, course dumps, audio, or video.

The purpose is REAPER execution and QC, not passive note storage:

- Source entries become copyright-safe lesson cards.
- Lesson cards become actionable REAPER chain rules.
- REAPER chain rules become candidate renders, bypass comparisons, rejection conditions, and QC report fields.
- YouTube lessons may be referenced by title, creator, URL, and timestamp notes only. Videos, audio, and full transcripts are not downloaded or committed.

## Plugin Expansion Layer

The plugin layer lives in `plugin_registry/`, `docs/plugins/`, `scripts/local_install/plugins/`, and additional `reaper/fx_chain_blueprints/`.

Plugin groups:

- Core: Bertom Denoiser Classic, TDR Nova, Techivation T-De-Esser 2, Voxengo SPAN, Youlean Loudness Meter, LoudMax
- Recommended: Klanghelm IVGI, DC1A, MJUC jr
- Optional: TAL-Reverb-4, Valhalla Supermassive, Blue Cat Freeware Pack, Melda MFreeFXBundle, Airwindows
- Disabled by default: GSnap, Graillon

The intended vocal repair chain is conservative denoise, dynamic EQ, de-ess, body restoration, gentle compression, parallel original vocal blend, metering/QC, and safe preview limiting. Pitch tools are disabled by default because they can change vocal identity.

## v0.2 Safety + Decision Engine + Local Runner

v0.2 adds safety gates, GitHub Actions, pre-commit hooks, a plugin capability matrix, candidate scoring schema, decision rules, dummy fixture generators, and a unified runner.

Public PC mode cannot install tools or process audio. Real audio must live only in ignored `local_only/` folders on the main computer and must never be committed.

Runner examples:

```bash
python scripts/runner/runner.py --mode safety-check
python scripts/runner/runner.py --mode manifest-check
python scripts/runner/runner.py --mode local-install-dry-run
python scripts/runner/runner.py --mode plugin-scan-dry-run
```

Real execution later requires `LOCAL_PRODUCTION_MACHINE=1`, `EXECUTE_INSTALL=1`, and `--execute`.

Pre-commit can be enabled later on the main computer with:

```bash
python -m pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Quick Public PC Check

PowerShell:

```powershell
.\scripts\public_pc\check_safe_environment.ps1
python .\scripts\public_pc\verify_no_audio_files.py
python .\scripts\public_pc\verify_no_secrets.py
```

Bash:

```bash
bash scripts/public_pc/check_safe_environment.sh
python scripts/public_pc/verify_no_audio_files.py
python scripts/public_pc/verify_no_secrets.py
```
