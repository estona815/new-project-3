# mesi_1_v11 Plugin Audit

- JSFX files: `220`
- FXChains: `35`
- Plugin map: `/Users/hantaeheuk/Documents/New project 3/config/plugin_map.yaml`
- Custom Suno DeAI references are treated as verified only when file/smoke evidence is present.

## Findings

| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WARN | JSFX_SMOKE_WARN | /Users/hantaeheuk/Documents/New project 3/ESTONA_AUTO_MIX_ENGINE/00_EXTERNAL_REFS/reaper_lua/ReaTeam_ReaScripts_Templates/JSFX/GFX/spk77_Basic GFX text.jsfx | Custom JSFX can be safely inserted. | {"file": "/Users/hantaeheuk/Documents/New project 3/ESTONA_AUTO_MIX_ENGINE/00_EXTERNAL_REFS/reaper_lua/ReaTeam_ReaScripts_Templates/JSFX/GFX/spk77_Basic GFX text.jsfx", "has_desc": false, "has_null_bytes": false, "has_slider_or_code": true, "line_count": 25} | Open the JSFX in REAPER or fix desc/code structure, then rerun plugin audit. | python3 -m harness.plugin_audit --project-root /Users/hantaeheuk/Documents/New project 3 --json | no |
| PASS | PLUGIN_MAP_PRESENT | /Users/hantaeheuk/Documents/New project 3/config/plugin_map.yaml | - | /Users/hantaeheuk/Documents/New project 3/config/plugin_map.yaml | Keep plugin map and REAPER FX-chain logs in sync. | - | no |
