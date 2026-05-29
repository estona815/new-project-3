# mesi_1_v10 Source Audit

- Source was lossy MP3. Output is improved processing/mastering, not true lossless restoration.
- Working WAV: `audio_work/mesi_1_v10_reaper_pipeline/intermediate/mesi_1_v10_WORKING_FROM_MP3_48k.wav`
- Duration: `105.850688` sec
- Sample rate: `48000`
- Channels: `2`
- Peak: `-1.60` dBFS
- RMS: `-12.31` dBFS
- Harshness band: `-12.616643270856189`
- Sibilance band: `-17.79863806013983`
- Air/fizz band: `-18.803156749783135`
- Side/mid ratio: `-11.644691622840334`
- Transient proxy: `0.11775866895914078`

## Findings

| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| INFO | WAV_READ_SCIPY_FLOAT_FALLBACK | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v10_reaper_pipeline/intermediate/mesi_1_v10_WORKING_FROM_MP3_48k.wav | - | unknown format: 3 | No action needed if downstream metrics pass. | - | no |
| WARN | INTEGRATED_LOUDNESS_UNAVAILABLE | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v10_reaper_pipeline/intermediate/mesi_1_v10_WORKING_FROM_MP3_48k.wav | Integrated LUFS is available for QC. | pyloudnorm import failed or numpy is unavailable. | Install pyloudnorm in the harness environment, then rerun before/after QC. | python3 -m harness.audio_qc --before BEFORE.wav --after AFTER.wav --json | no |
| WARN | LOSSY_MP3_SOURCE | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v03_mp3_piano_vocal_noise_tuck/mesi_1_v03_MASTER_320k.mp3 | MP3-derived WAV is a lossless original. | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v03_mp3_piano_vocal_noise_tuck/mesi_1_v03_MASTER_320k.mp3 | Keep lossy-source language in all reports and avoid lossless restoration claims. | - | no |
