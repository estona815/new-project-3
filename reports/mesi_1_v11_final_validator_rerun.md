# Final Validation

- Final WAV: `/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_MASTER_24-48.wav`
- RPP: `/Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v11_reaper_pipeline/mesi_1_v11_REAPER_PIPELINE.rpp`
- Max severity: `WARN`

## Findings

| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| INFO | WAV_READ_SCIPY_FLOAT_FALLBACK | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_MASTER_24-48.wav | - | unknown format: 65534 | No action needed if downstream metrics pass. | - | no |
| WARN | INTEGRATED_LOUDNESS_UNAVAILABLE | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_MASTER_24-48.wav | Integrated LUFS is available for QC. | pyloudnorm import failed or numpy is unavailable. | Install pyloudnorm in the harness environment, then rerun before/after QC. | python3 -m harness.audio_qc --before BEFORE.wav --after AFTER.wav --json | no |
| PASS | RPP_AUDIT_COMPLETED | /Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v11_reaper_pipeline/mesi_1_v11_REAPER_PIPELINE.rpp | - | tracks=17, items=8, midi_items=3, fx=5 | Keep this audit report attached to any render claim. | - | no |
| WARN | REBEAT_BUS_RENDERS_MISSING | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline | Role bus render evidence exists. | {"bass": [], "drums": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_drums_bus.wav"], "master": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_master_bus.wav", "/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_MASTER_24-48.wav"], "mix": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_mix_bus.wav"], "music": []} | Render drums, bass, music/support, mix, and master buses, then rerun audit. | - | no |
| WARN | FULLMIX_ACTIVE_WITH_REBUILD_ITEMS | /Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v11_reaper_pipeline/mesi_1_v11_REAPER_PIPELINE.rpp | Rebuild items are the primary sound source. | original_fullmix_active=true | Classify as drum reinforcement or partial rebeat unless the independent arrangement can play without fullmix reliance. | - | yes |
