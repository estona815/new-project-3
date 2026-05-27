# Branch Plan

## Branches

| Branch | Purpose | Success Criteria |
|---|---|---|
| `main` | Stable published harness | Clean release merged only after verification |
| `dev/scaffold` | Initial public-PC-safe scaffold | Docs and stubs created, checks pass |
| `docs/github-tool-research` | Official-source research notes | Docs only, cited official sources later |
| `feature/public-pc-safe-mode` | Safety checks and public PC policy | No install, no audio, no secrets |
| `feature/reaper-extension-harness` | REAPER extension dry-run installers | Dry-run default, no real install |
| `feature/audio-tool-install-harness` | Audio tool dry-run installers | Dry-run default, no model download |
| `feature/reaper-template-harness` | REAPER template and action blueprints | Lua stubs and docs only |
| `feature/vocal-cleanup-pipeline` | Candidate cleanup workflow | A/B/C/D pipeline documented |
| `feature/qc-reporting-harness` | QC script stubs | Report generation from dummy/safe inputs |
| `feature/local-machine-bootstrap` | Trusted machine setup | Local setup checks documented |
| `feature/plugin-expansion-layer` | Free/recommended plugin registry and dry-run harness | Docs, manifests, dry-run scripts, checks pass |
| `release/v0.1-public-harness` | First public scaffold release | Safe checks pass, no install performed |
| `release/v0.2-main-computer-install` | Future local install release | Only after main computer dry-run/execute validation |

## Merge Rules

- Public PC branches must remain text-only and dry-run.
- `release/v0.1-public-harness` may receive scaffold work only after safety checks pass.
- Do not merge into `main` unless the repository is clean and checks pass.
