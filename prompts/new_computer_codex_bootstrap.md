# New Computer Codex Bootstrap Prompt

Use this prompt after cloning the GitHub repo on another computer or when a
Codex session is asked to learn the workflow from the GitHub link.

```text
You are working in a REAPER AutoMix / mastering automation harness.

Treat the GitHub repo as source, policy, and reproducible workflow context. Do
not treat it as proof of local plugin semantics, parameter-write safety,
finished audio quality, or listening approval.

First read, in this order:
1. AGENTS.md
2. README.md
3. QUICKSTART.md
4. docs/github_upload_readiness.md
5. REAPER_REFERENCE_MIX_PIPELINE.md if present

Operating rules:
- Do not claim listening results or a finished master without measured QC and
  explicit user review.
- Do not route the raw full mix or reference into any active master path.
- Keep the full mix/reference track named
  SOURCE full mix reference muted - not in master.
- Keep that track muted with master send disabled.
- After plugin insertion, always create work/traces/plugin_trace.json.
- Verify the first FX slot on 08 MALE_NONHOOK_CENTER is exactly
  JS: Codex Vocal AI Artifact Split Tamer.
- External plugin parameter writes require calibration evidence. Plugin presence
  is not semantic write safety.

Start with report-only checks:

python3 scripts/run_github_upload_readiness.py --project-name reaper-automix --require-ready
python3 scripts/run_github_integration_smoke.py --output-dir automix
python3 tools/detect_environment.py
python3 tools/install_reaper_jsfx.py

If REAPER is installed and the user approves local JSFX installation, run:

python3 tools/install_reaper_jsfx.py --apply

If REAPER is available, run the inventory-only scanner from REAPER's Action
List:

automix/scan_reaper_plugin_inventory.lua

Then return to the shell and continue with report-first preparation:

python3 scripts/run_plugin_validation_preflight.py --project-name reaper-automix --output-dir automix
python3 tools/build_asset_manifest.py
python3 tools/run_reaper_pipeline.py --prepare

Treat plugin inventory as capability evidence only. Do not claim the repo has
learned plugin semantics or that parameter writes are automatically safe just
because a plugin was detected.

Stop before rendering if REAPER, plugins, source stems, references, traces,
QC reports, or render outputs are missing. Mark the result blocked or
unverified instead of making delivery claims.
```
