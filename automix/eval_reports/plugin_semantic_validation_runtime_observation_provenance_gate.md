# Plugin Semantic Validation Runtime Observation Provenance Gate

- Project: `project`
- Created UTC: `2026-06-05T12:45:24Z`
- Status: `runtime_observation_provenance_pending_observations`
- Passed: `True`
- Expected packet ready: `True`
- Observed provenance ready: `False`
- Safe to write parameters: `False`

This report checks runtime observation provenance only. It does not create validation reports.

## Counts

- `collector_jobs_total`: `9`
- `queue_jobs_total`: `9`
- `observations_existing_total`: `0`
- `observations_missing_total`: `9`
- `observations_provenance_verified_total`: `0`

## Blockers

- none

## Warnings

- `runtime_observation_files_missing:9`
- `semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx:runtime_observation_file_missing`
- `semantic_validation_02_reaverbate_cockos:runtime_observation_file_missing`
- `semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx:runtime_observation_file_missing`
- `semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx:runtime_observation_file_missing`
- `semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx:runtime_observation_file_missing`
- `semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx:runtime_observation_file_missing`
- `semantic_validation_07_reacomp_cockos:runtime_observation_file_missing`
- `semantic_validation_08_readelay_cockos:runtime_observation_file_missing`
- `semantic_validation_09_reaeq_cockos:runtime_observation_file_missing`

## Artifact Hashes

- `collector_script`: `a4dd5f14a41ebbbc`
- `queue_payload`: `112fcc47516e3640`
- `observation_template`: `fd0aeb331c9f0358`
- `collector_package`: `1408f586e1e3ab70`
- `local_device_qc`: `a232be5212c3d647`
- `safety_audit`: `58ebafa6a5d648d7`

## Jobs

### semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx

- Plugin: `Codex Vocal/vocal_ai_artifact_split_tamer.jsfx`
- Status: `observation_missing`
- Observation exists: `False`
- Observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_observation.json`
- Script version: ``
- Parameters observed: `0`
- Blockers: `[]`
- Warnings: `['runtime_observation_file_missing']`

### semantic_validation_02_reaverbate_cockos

- Plugin: `ReaVerbate (Cockos)`
- Status: `observation_missing`
- Observation exists: `False`
- Observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_02_reaverbate_cockos_observation.json`
- Script version: ``
- Parameters observed: `0`
- Blockers: `[]`
- Warnings: `['runtime_observation_file_missing']`

### semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx

- Plugin: `Vocal Clarity Repair/vocal_air_guard.jsfx`
- Status: `observation_missing`
- Observation exists: `False`
- Observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx_observation.json`
- Script version: ``
- Parameters observed: `0`
- Blockers: `[]`
- Warnings: `['runtime_observation_file_missing']`

### semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx

- Plugin: `Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx`
- Status: `observation_missing`
- Observation exists: `False`
- Observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_observation.json`
- Script version: ``
- Parameters observed: `0`
- Blockers: `[]`
- Warnings: `['runtime_observation_file_missing']`

### semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx

- Plugin: `Vocal Clarity Repair/vocal_output_guard.jsfx`
- Status: `observation_missing`
- Observation exists: `False`
- Observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx_observation.json`
- Script version: ``
- Parameters observed: `0`
- Blockers: `[]`
- Warnings: `['runtime_observation_file_missing']`

### semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx

- Plugin: `Vocal Clarity Repair/vocal_presence_enhancer.jsfx`
- Status: `observation_missing`
- Observation exists: `False`
- Observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx_observation.json`
- Script version: ``
- Parameters observed: `0`
- Blockers: `[]`
- Warnings: `['runtime_observation_file_missing']`

### semantic_validation_07_reacomp_cockos

- Plugin: `ReaComp (Cockos)`
- Status: `observation_missing`
- Observation exists: `False`
- Observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_07_reacomp_cockos_observation.json`
- Script version: ``
- Parameters observed: `0`
- Blockers: `[]`
- Warnings: `['runtime_observation_file_missing']`

### semantic_validation_08_readelay_cockos

- Plugin: `ReaDelay (Cockos)`
- Status: `observation_missing`
- Observation exists: `False`
- Observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_08_readelay_cockos_observation.json`
- Script version: ``
- Parameters observed: `0`
- Blockers: `[]`
- Warnings: `['runtime_observation_file_missing']`

### semantic_validation_09_reaeq_cockos

- Plugin: `ReaEQ (Cockos)`
- Status: `observation_missing`
- Observation exists: `False`
- Observation: `/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_09_reaeq_cockos_observation.json`
- Script version: ``
- Parameters observed: `0`
- Blockers: `[]`
- Warnings: `['runtime_observation_file_missing']`

## Limits

- This gate does not open REAPER, execute Lua, create validation reports, write parameters, render, save, or approve audio.
- Missing observations do not fail the expected packet; existing observations must match provenance before report authoring.
- Optional hash fields are checked when present and warned when absent.
- Passing this gate does not make semantic validation ready.
