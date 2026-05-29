# Tempo/Grid Analysis

- Input: `/Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v10_reaper_pipeline/intermediate/mesi_1_v10_WORKING_FROM_MP3_48k.wav`
- Profile: `fullmix_drum_reinforcement`
- Duration: `105.850688` sec
- Selected BPM: `129.496`
- Grid confidence: `FAIL` (`0.2412`)
- Quantization safe: `False`
- Onset count: `557`
- Transient density/sec: `5.26213`

## BPM Candidates

- `129.496` bpm score `0.086` support `158`
- `136.312` bpm score `0.062` support `114`
- `99.613` bpm score `0.0555` support `102`
- `132.817` bpm score `0.0495` support `91`
- `143.885` bpm score `0.0397` support `73`
- `161.871` bpm score `0.0343` support `63`
- `117.724` bpm score `0.0343` support `63`
- `123.33` bpm score `0.0343` support `63`

## Findings

| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| INFO | SCIPY_AUDIO_READ_FALLBACK | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v10_reaper_pipeline/intermediate/mesi_1_v10_WORKING_FROM_MP3_48k.wav | - | unknown format: 3 | No action needed if tempo/grid confidence passes. | - | no |
| FAIL | GRID_CONFIDENCE_FAIL | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v10_reaper_pipeline/intermediate/mesi_1_v10_WORKING_FROM_MP3_48k.wav | Detected grid is safe for reconstruction. | grid_score=0.241, selected_bpm=129.496 | Do not quantize/rebeat; use manual tempo map or stems/MIDI. | - | yes |
| WARN | MULTIPLE_BPM_CANDIDATES | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v10_reaper_pipeline/intermediate/mesi_1_v10_WORKING_FROM_MP3_48k.wav | One BPM candidate is clearly dominant. | candidates=[129.496, 136.312, 99.613, 132.817] | Report half/double-time ambiguity and avoid hard quantization until verified. | - | yes |
