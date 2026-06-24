# GitHub Upload Readiness

This repo is prepared as a source-first Codex handoff for the REAPER AutoMix /
mastering harness. It should be uploaded as code, configs, tests, JSFX, Lua,
and documentation. It should not include raw stems, references, renders,
delivery ZIPs, private documents, or generated REAPER session files.

## Safe Upload Contract

- Upload source code: `automix/`, `tools/`, `scripts/`, `tests/`, `configs/`,
  `reaper/scripts/`, and the bundled JSFX source that is actually present
  (`VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/` and, when available, `reaper/jsfx/`).
- Upload operating docs: `README.md`, `QUICKSTART.md`, `AGENTS.md`,
  `MIXMASTER_SPEC.md`, `PLUGIN_POLICY.md`, `QC_TARGETS.md`,
  `TESTING_AND_HARNESS.md`, and this `docs/` handoff set.
- Keep runtime source media out of git: `input/stems/`, `input/reference/`,
  `audio_work/`, `renders/`, `deliverables/`, `delivery/`, `output/`,
  `processed_audio/`, and `tmp/`.
- Keep generated local REAPER projects out of git by default: `*.rpp`, `*.RPP`,
  and `*.rpp-bak`.
- Track sanitized REAPER templates only under `reaper/templates/` if a template
  is intentionally reviewed and has no local media paths.

## Readiness Audit

Run this before staging or pushing:

```sh
python3 scripts/run_github_upload_readiness.py --project-name reaper-automix --require-ready
```

It writes:

- `automix/eval_reports/github_upload_readiness.json`
- `automix/eval_reports/github_upload_readiness.md`

The audit does not open REAPER, render audio, stage files, commit, or push.

Important interpretation:

- `source_handoff_ready=true` means required source/docs/tests are present.
- `safe_to_git_add_all=true` means new untracked sensitive files are ignored.
- `clean_public_upload_ready=false` means already tracked legacy media, REAPER
  project files, or deleted tracked files still need manual staging/history
  review before a public repository push.

## New Computer Bootstrap

After cloning on another computer:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
python3 scripts/run_github_upload_readiness.py --project-name reaper-automix --require-ready
python3 scripts/run_github_integration_smoke.py --output-dir automix
python3 tools/detect_environment.py
```

Install bundled JSFX into the local REAPER resource folder. The first command is
dry-run only:

```sh
python3 tools/install_reaper_jsfx.py
python3 tools/install_reaper_jsfx.py --apply
```

Then restart REAPER or rescan FX. If REAPER is available, run the inventory-only
scanner from the REAPER Action List:

```text
automix/scan_reaper_plugin_inventory.lua
```

Back in the shell, continue with source discovery and report-only validation:

```sh
python3 scripts/run_plugin_validation_preflight.py \
  --project-name reaper-automix \
  --output-dir automix
python3 tools/build_asset_manifest.py
python3 tools/run_reaper_pipeline.py --prepare
```

Do not render or deliver unless `work/traces/plugin_trace.json` exists and the
first FX slot on `08 MALE_NONHOOK_CENTER` is exactly:

```text
JS: Codex Vocal AI Artifact Split Tamer
```

## Suggested Stage Review

Before a first GitHub push, inspect:

```sh
git status --short
python3 scripts/run_github_upload_readiness.py --project-name reaper-automix
```

If the readiness report shows tracked sensitive files, decide whether to remove
them from the repository index in a dedicated cleanup commit. Ignore rules do
not remove files that are already tracked.

## Claim Rules

- Do not claim a finished master from GitHub setup alone.
- Do not claim GitHub bootstrap automatically learns plugin semantics.
- Do not claim plugin parameter write safety from plugin presence alone.
- Do not claim reference matching without lawful reference audio analysis.
- Treat GitHub bootstrap as environment readiness, not audio approval.
