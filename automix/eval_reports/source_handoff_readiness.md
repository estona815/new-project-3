# Source Handoff Readiness

- Project: `project`
- Created UTC: `2026-06-02T15:23:47Z`
- Stem requests: `2`
- Manual review tracks: `4`
- Source files present: `6/8`
- Accepted export source present: `False`
- Automatic processing ready: `False`

This is a handoff/readiness report only. It does not approve or process audio.

## Blockers

- `accepted_export_source_missing`
- `current_source_file_missing:V37 RETURN ReaDelay filtered throw`
- `current_source_file_missing:V37 RETURN ReaVerbate dark send`
- `full_mix_unsafe_tracks:2`
- `stem_requests_open:2`

## Warnings

- `current_source_file_presence_is_not_acceptance`
- `manual_review_required_tracks:4`

## Stem Requests

### SOURCE full mix reference muted

- Role: `full_mix_reference`
- Source classification: `full_mix`
- Stem category: `instrumental_bus_required`
- Current source exists: `True`
- Current source path: `/Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v37_vocal_clarity_max_guarded/processed_stems/source_full_mix_reference.wav`
- Requested files:
  - `instrumental_or_music_bus_stem`: Needed to evaluate vocal-seat carving without treating a full mix as a vocal source.
  - `separate_lead_vocal_stem_if_available`: Useful for level-matched A/B and vocal-first balance validation.

### V37 INSTRUMENTAL BUS free EQ pocket

- Role: `instrumental_bus`
- Source classification: `full_mix`
- Stem category: `instrumental_bus_required`
- Current source exists: `True`
- Current source path: `/Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v37_vocal_clarity_max_guarded/processed_stems/instrumental_vocal_pocket.wav`
- Requested files:
  - `instrumental_or_music_bus_stem`: Needed to evaluate vocal-seat carving without treating a full mix as a vocal source.
  - `separate_lead_vocal_stem_if_available`: Useful for level-matched A/B and vocal-first balance validation.


## Manual Review Tracks

- `V37 PRINTED VOCAL REVERB SEND` role=`reverb_send` source=`unknown` exists=`True`
- `V37 PRINTED VOCAL DELAY SEND` role=`delay_send` source=`unknown` exists=`True`
- `V37 RETURN ReaVerbate dark send` role=`unknown` source=`unknown` exists=`False`
- `V37 RETURN ReaDelay filtered throw` role=`delay_send` source=`unknown` exists=`False`
