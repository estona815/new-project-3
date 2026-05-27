# Security Policy

## No Secrets

Do not commit:

- API keys
- OAuth tokens
- Cookies
- SSH keys
- Passwords
- License files
- Serial numbers
- iLok data
- Plugin activation files

## No Private Audio

Do not commit:

- Private music
- Real Suno exports
- Unreleased artist material
- Stems
- Renders
- Reference tracks
- Voice recordings

## No Copyrighted Source Dumps

Do not commit:

- Full YouTube transcripts
- Downloaded YouTube video or audio
- Full copied articles
- Full copied manuals
- Paywalled course content
- Third-party lesson worksheets

Public resources may be tracked as links, metadata, short paraphrased notes, and original rule cards only. Lesson cards must transform source ideas into REAPER workflow rules, plugin-chain rules, QC rules, or Suno repair rejection conditions.

## No Account Login On Public PC

Do not log into:

- GitHub
- Suno
- DAW accounts
- iLok
- Plugin vendors
- Cloud drives containing music

## `.gitignore` Policy

The `.gitignore` excludes audio/video files, installers, archives, local-only folders, secrets, licenses, credentials, virtual environments, REAPER media folders, and generated reports that may contain private paths.

Plugin installers must not be committed. Any account-based or license-activated plugin is optional/manual and must be handled only on the trusted main computer.

## v0.2 Safety Gates

The repo includes local scripts, pre-commit configuration, and GitHub Actions for no-audio, no-video, no-installer, no-secret, public-PC mode, and manifest integrity checks.

Real audio must stay in ignored `local_only/` folders. Do not commit generated fixtures, renders, plugin inventories with private paths, or real QC reports.

## Manual Pre-Commit Checks

Run:

```bash
python scripts/public_pc/verify_no_audio_files.py
python scripts/public_pc/verify_no_secrets.py
git status --short --branch
git diff --check -- .
```
