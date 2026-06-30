# REAPER Runtime Collector Safety Audit

- Project: `project`
- Created UTC: `2026-06-05T12:24:11Z`
- Status: `collector_safety_passed`
- Passed: `True`
- Safe for operator runtime collection: `True`
- In-memory temporary probe mutation: `True`
- Writes parameters: `False`
- Renders audio: `False`
- Saves project: `False`

This audit is static. It does not run REAPER or approve semantic parameter writes.

## Blockers

- none

## Warnings

- `blocked_queue_jobs_remain:2`
- `collector_writes_raw_observation_files`
- `temporary_probe_track_mutation_detected`

## REAPER Calls

- `CountTracks`
- `DeleteTrack`
- `GetSetMediaTrackInfo_String`
- `GetTrack`
- `InsertTrackAtIndex`
- `PreventUIRefresh`
- `RecursiveCreateDirectory`
- `SetMediaTrackInfo_Value`
- `ShowMessageBox`
- `TrackFX_AddByName`
- `TrackFX_Delete`
- `TrackFX_GetCount`
- `TrackFX_GetFXName`
- `TrackFX_GetNumParams`
- `TrackFX_GetParamName`
- `Undo_BeginBlock`
- `Undo_EndBlock`
- `ValidatePtr2`

## Limits

- This is a static safety audit of the generated collector package.
- A passing audit does not prove plugin semantic write safety or audio quality.
- The collector still requires a saved test copy or temporary muted REAPER context because it creates and removes a probe track in memory.
- The collector writes raw observation JSON only; raw observations are not validation reports.
