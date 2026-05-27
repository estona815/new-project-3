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

## No Account Login On Public PC

Do not log into:

- GitHub
- Suno
- DAW accounts
- iLok
- Plugin vendors
- Cloud drives containing music

## `.gitignore` Policy

The `.gitignore` excludes audio/video files, local-only folders, secrets, virtual environments, REAPER media folders, and generated reports that may contain private paths.

## Manual Pre-Commit Checks

Run:

```bash
python scripts/public_pc/verify_no_audio_files.py
python scripts/public_pc/verify_no_secrets.py
git status --short --branch
git diff --check -- .
```

