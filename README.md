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

