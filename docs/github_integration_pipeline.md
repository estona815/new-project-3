# GitHub Integration Pipeline

This project now has an isolated GitHub-researched integration layer for future
REAPER MCP, reapy, and bridge work:

- Code: `automix/github_integration/`
- Smoke runner: `scripts/run_github_integration_smoke.py`
- Smoke report: `automix/eval_reports/github_integration_smoke.json`
- Optional audio diagnostics: `automix/analysis_reports/github_audio_diagnostics.json`

## Source Pack

The local source pack reviewed for this addition is:

`$REAPER_AUTOMIX_INTEGRATION_PACK`

The pack was treated as a project-addition seed, not as a replacement for the
existing AutoMix pipeline.

## Reference Repositories

These repositories are architecture references only. Do not vendor cloned repos
or copy licensed source into this project without a separate license notice.

| Repository | Route | Project Use |
| --- | --- | --- |
| `shiehn/total-reaper-mcp` | https://github.com/shiehn/total-reaper-mcp | File-based Lua/Python MCP bridge shape, tool profiles, natural-language command routing. |
| `wegitor/reaper-reapy-mcp` | https://github.com/wegitor/reaper-reapy-mcp | Curated FX, track, item, and render command surface for future tool candidates. |
| `RomeoDespres/reapy` | https://github.com/RomeoDespres/reapy | Optional Python control layer once REAPER/reapy is configured locally. |
| `2nist/reaper-bridge` | https://github.com/2nist/reaper-bridge | Lightweight bridge and generated Lua fallback ideas. |
| `X-Raym/REAPER-ReaScripts` | https://github.com/X-Raym/REAPER-ReaScripts | Mature ReaScript style and packaging conventions only. |
| `Buy-One/REAPER-scripts` | https://github.com/Buy-One/REAPER-scripts | Practical Lua script organization and configurable script patterns only. |

## Fit In The Existing Pipeline

The layer sits before live plugin execution:

1. Portable smoke check and optional audio diagnostics.
2. Existing plugin inventory and semantic validation gates.
3. Existing processing policy audit.
4. Snapshot/rollback proof.
5. A/B preview render proof.
6. Only then can future REAPER-facing execution be considered.

It does not bypass `automix/plugins/`, `automix/safety/`, `automix/orchestrator/`,
or final export gates.

The orchestrator now includes `github_integration_smoke` as a dry-run current
state stage and rolls it into:

- `automix/eval_reports/global_qc_summary.json`
- `automix/eval_reports/current_state_summary.json`
- `automix/eval_reports/automix_report_index.json`

## Safety Contract

- Default all REAPER-facing actions to `dry_run=true`.
- Never overwrite the original REAPER project.
- Never delete tracks, takes, items, regions, renders, or source files.
- Never apply pitch/formant, denoise, hard gate, or limiter changes without
  explicit approval plus review evidence.
- Treat portable loudness and artifact outputs as proxies, not LUFS, reference
  matching, or final QC evidence.
- Keep `safe_to_write_parameters=false` until runtime semantic validation proves
  the exact plugin and parameter behavior.

## Commands

Run the integration smoke without audio:

```sh
python3 scripts/run_github_integration_smoke.py --output-dir automix
```

Run with a user-owned audio file:

```sh
python3 scripts/run_github_integration_smoke.py path/to/audio.wav --output-dir automix
```

The no-audio smoke should pass on any machine with Python. The audio path writes
report-only diagnostics and still does not modify REAPER.

## Development Rules

- Keep third-party repositories as references unless a license review is added.
- Add one command at a time behind the dry-run adapter.
- For any write operation, require snapshot path, rollback handle, validated
  plugin adapter, semantic parameter evidence, and A/B preview manifest.
- Do not claim reference matching or commercial readiness from this layer.
