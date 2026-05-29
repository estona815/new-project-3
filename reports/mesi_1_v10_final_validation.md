# mesi_1_v10 Final Validation

- Max severity: `WARN`

## Command Results

| command | status | evidence |
| --- | --- | --- |
| python3 tools/validate_suno_vocal_rescue_workflow.py | PASS | Suno vocal rescue workflow validation passed. |
| python3 REAPER_PLUGIN_INTELLIGENCE_SYSTEM/scripts/validate_suno_deai_system.py | PASS | Suno DeAI validation passed |
| python3 -m pytest tests/test_harness_smoke.py | WARN | /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest |
| python3 -m pytest tests/test_engineering_rules.py | WARN | /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest |
| python3 -m pytest tests/test_rebeat_classification.py | WARN | /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest |
| python3 -m pytest tests/test_pipeline_integration.py | WARN | /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest |

## Findings

| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| INFO | WAV_READ_SCIPY_FLOAT_FALLBACK | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_24-48.wav | - | unknown format: 65534 | No action needed if downstream metrics pass. | - | no |
| WARN | INTEGRATED_LOUDNESS_UNAVAILABLE | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_24-48.wav | Integrated LUFS is available for QC. | pyloudnorm import failed or numpy is unavailable. | Install pyloudnorm in the harness environment, then rerun before/after QC. | python3 -m harness.audio_qc --before BEFORE.wav --after AFTER.wav --json | no |
| PASS | RPP_AUDIT_COMPLETED | /Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v10_reaper_pipeline/mesi_1_v10_REAPER_PIPELINE.rpp | - | tracks=17, items=8, midi_items=3, fx=5 | Keep this audit report attached to any render claim. | - | no |
| WARN | REBEAT_BUS_RENDERS_MISSING | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline | Role bus render evidence exists. | {"bass": [], "drums": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_drums_bus.wav"], "master": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_master_bus.wav", "/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_MASTER_24-48.wav"], "mix": ["/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v10_reaper_pipeline/mesi_1_v10_mix_bus.wav"], "music": []} | Render drums, bass, music/support, mix, and master buses, then rerun audit. | - | no |
| WARN | FULLMIX_ACTIVE_WITH_REBUILD_ITEMS | /Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v10_reaper_pipeline/mesi_1_v10_REAPER_PIPELINE.rpp | Rebuild items are the primary sound source. | original_fullmix_active=true | Classify as drum reinforcement or partial rebeat unless the independent arrangement can play without fullmix reliance. | - | yes |
| WARN | EXTERNAL_VALIDATOR_WARN | python3 -m pytest tests/test_harness_smoke.py | All requested validators are available and pass. | /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest | Install missing validator/test dependency or create the missing test, then rerun. | - | no |
| WARN | EXTERNAL_VALIDATOR_WARN | python3 -m pytest tests/test_engineering_rules.py | All requested validators are available and pass. | /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest | Install missing validator/test dependency or create the missing test, then rerun. | - | no |
| WARN | EXTERNAL_VALIDATOR_WARN | python3 -m pytest tests/test_rebeat_classification.py | All requested validators are available and pass. | /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest | Install missing validator/test dependency or create the missing test, then rerun. | - | no |
| WARN | EXTERNAL_VALIDATOR_WARN | python3 -m pytest tests/test_pipeline_integration.py | All requested validators are available and pass. | /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest | Install missing validator/test dependency or create the missing test, then rerun. | - | no |
| WARN | REAPER_RENDER_FALLBACK | /Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v10_reaper_pipeline/mesi_1_v10_REAPER_PIPELINE.rpp | REAPER executable availability means the final WAV was rendered by REAPER. | reaper_executable=/Applications/REAPER.app/Contents/MacOS/REAPER, selected_candidate=C_punch_preserve | Run a REAPER batch/render pass from the generated RPP or render_candidates.lua, then rerun final validation if REAPER-render evidence is required. | /Applications/REAPER.app/Contents/MacOS/REAPER -newinst -nosplash /Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v10_reaper_pipeline/mesi_1_v10_REAPER_PIPELINE.rpp | yes |
