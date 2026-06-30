# Local Device QC

- Project: `project`
- Created UTC: `2026-06-05T11:43:20Z`
- Status: `local_device_qc_ready`
- Local device QC ready: `True`
- Runtime collection ready: `True`
- Applied parameter writes ready: `False`
- Delivery claims ready: `False`
- Render audio files found: `135`

This is a local-machine readiness report. It does not open REAPER, write parameters, render audio, or approve delivery.

## Blockers

- none

## Warnings

- `ab_preview_evidence_not_ready`
- `accepted_source_not_ready`
- `ffmpeg_missing_mp3_export_or_filter_qc_limited`
- `ffprobe_missing_external_probe_limited`
- `final_qc_evidence_not_ready`
- `final_render_evidence_not_ready`
- `plugin_semantic_validation_not_ready_for_parameter_writes`

## Commands

- `python3` available=`True` path=`/usr/bin/python3` `Python 3.9.6`
- `pytest` available=`False` path=``
- `afinfo` available=`True` path=`/usr/bin/afinfo`
- `ffmpeg` available=`False` path=``
- `ffprobe` available=`False` path=``
- `sox` available=`False` path=``

## REAPER / JSFX

- `reaper_app` exists=`True` path=`/Applications/REAPER.app`
- `reaper_binary` exists=`True` path=`/Applications/REAPER.app/Contents/MacOS/REAPER`
- `reaper_info_plist` exists=`True` path=`/Applications/REAPER.app/Contents/Info.plist`
- `reaper_stock_fx_dir` exists=`True` path=`/Applications/REAPER.app/Contents/Plugins/FX`
- `reaper_resource_dir` exists=`True` path=`/Users/hantaeheuk/Library/Application Support/REAPER`
- `reaper_effects_dir` exists=`True` path=`/Users/hantaeheuk/Library/Application Support/REAPER/Effects`
- `final_qc_analyzer` exists=`True` path=`/Users/hantaeheuk/Documents/New project 3/automix/export/final_qc_analyzer.py`

## REAPER App Metadata

- Bundle id: `com.cockos.reaper`
- Version: `7.73.0_0826febu`
- Build: `7.73.0_0826febu`
- Info.plist sha256: `8ef01cc42d3d801e`

## Required JSFX

- `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx` present=`True` purpose=`suno_ai_artifact_required_first_slot` sha256=`80e48a08a3e2cb80`
- `Vocal Clarity Repair/vocal_air_guard.jsfx` present=`True` purpose=`post_ott_air_guard` sha256=`86b4c8c31047a091`
- `Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx` present=`True` purpose=`demud_dynamic_eq` sha256=`0b1b73a5b70c2cae`
- `Vocal Clarity Repair/vocal_output_guard.jsfx` present=`True` purpose=`output_guard` sha256=`0f1379c973c65d10`
- `Vocal Clarity Repair/vocal_presence_enhancer.jsfx` present=`True` purpose=`presence_enhancer` sha256=`c6e888cb33ba2ab8`

## Stock FX Fingerprints

- `ReaComp (Cockos)` present=`True` sha256=`2aaa49900d1af67a`
- `ReaDelay (Cockos)` present=`True` sha256=`8b2b008fa7a5dc77`
- `ReaEQ (Cockos)` present=`True` sha256=`7fa3347ce8d7df14`
- `ReaVerbate (Cockos)` present=`True` sha256=`5eb02c27ab856c16`
- `ReaXcomp (Cockos)` present=`True` sha256=`52dce338bbd0732a`
- `ReaPitch (Cockos)` present=`True` sha256=`aba55ae98cfcf4de`
- `ReaLimit (Cockos)` present=`True` sha256=`a02dc5111484585f`

## Gate Status

- `plugin_validation_preflight` found=`True` ready=`False` passed=`None` blockers=`3`
- `plugin_semantic_validation_gate` found=`True` ready=`False` passed=`None` blockers=`21`
- `runtime_collector_package` found=`True` ready=`True` passed=`None` blockers=`0`
- `runtime_collector_safety_audit` found=`True` ready=`True` passed=`True` blockers=`0`
- `runtime_observation_gate` found=`True` ready=`False` passed=`None` blockers=`9`
- `runtime_evidence_gate` found=`True` ready=`False` passed=`None` blockers=`19`
- `source_acceptance` found=`True` ready=`False` passed=`None` blockers=`1`
- `final_render_evidence` found=`True` ready=`False` passed=`None` blockers=`4`
- `final_qc_evidence` found=`True` ready=`False` passed=`None` blockers=`15`
- `ab_preview_evidence` found=`True` ready=`False` passed=`None` blockers=`11`
- `approval_export_readiness` found=`True` ready=`False` passed=`None` blockers=`71`
- `path_hygiene` found=`True` ready=`True` passed=`True` blockers=`0`
- `requirements_traceability` found=`True` ready=`True` passed=`True` blockers=`0`
- `processing_policy` found=`True` ready=`True` passed=`True` blockers=`0`

## Recent Render Files

- `renders/mwolla_v11_constant_vocal_light_dyn_eq_master/mwolla_v11_AB_original_to_constant_vocal_light_dyn_eq_master_320k.mp3` `2242604` bytes
- `renders/mwolla_v11_constant_vocal_light_dyn_eq_master/mwolla_v11_CONSTANT_VOCAL_LIGHT_DYN_EQ_MASTER_320k.mp3` `5967404` bytes
- `renders/mwolla_v11_constant_vocal_light_dyn_eq_master/mwolla_v11_CONSTANT_VOCAL_LIGHT_DYN_EQ_MASTER.wav` `57262394` bytes
- `renders/mwolla_v11_constant_vocal_light_dyn_eq_master/mwolla_v11_POST_FINAL_LEVEL_LOCK_24-48.wav` `57262394` bytes
- `renders/mwolla_v11_constant_vocal_light_dyn_eq_master/mwolla_v11_PHRASE_LEVELED_PREMASTER_24-48.wav` `57262394` bytes
- `renders/mwolla_v11_constant_vocal_light_dyn_eq_master/mwolla_v11_REAPERPRINT_24-48.wav` `42947442` bytes
- `renders/mwolla_v11_constant_vocal_light_dyn_eq_master/mwolla_v11_VOCAL_SOLO_constant_vocal_light_dyn_eq.wav` `57262394` bytes
- `renders/marunouchi_v01_stem_mix_master/marunouchi_v01_AB_original_fullmix_to_stem_master_320k.mp3` `4842284` bytes
- `renders/marunouchi_v01_stem_mix_master/marunouchi_v01_STEM_MIX_MASTER_320k.mp3` `5051564` bytes
- `renders/marunouchi_v01_stem_mix_master/marunouchi_v01_STEM_MIX_MASTER.wav` `36356766` bytes
