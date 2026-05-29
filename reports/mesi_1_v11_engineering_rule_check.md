# mesi_1_v11 Engineering Rule Check

- Status: `not_final_warn_plus`
- Max severity: `WARN`

## Findings

| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| INFO | WAV_READ_SCIPY_FLOAT_FALLBACK | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v11_reaper_pipeline/intermediate/mesi_1_v11_WORKING_FROM_MP3_48k.wav | - | unknown format: 3 | No action needed if downstream metrics pass. | - | no |
| WARN | INTEGRATED_LOUDNESS_UNAVAILABLE | /Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v11_reaper_pipeline/intermediate/mesi_1_v11_WORKING_FROM_MP3_48k.wav | Integrated LUFS is available for QC. | pyloudnorm import failed or numpy is unavailable. | Install pyloudnorm in the harness environment, then rerun before/after QC. | python3 -m harness.audio_qc --before BEFORE.wav --after AFTER.wav --json | no |
| INFO | WAV_READ_SCIPY_FLOAT_FALLBACK | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_MASTER_24-48.wav | - | unknown format: 65534 | No action needed if downstream metrics pass. | - | no |
| WARN | INTEGRATED_LOUDNESS_UNAVAILABLE | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_MASTER_24-48.wav | Integrated LUFS is available for QC. | pyloudnorm import failed or numpy is unavailable. | Install pyloudnorm in the harness environment, then rerun before/after QC. | python3 -m harness.audio_qc --before BEFORE.wav --after AFTER.wav --json | no |
| WARN | FULLMIX_DEESSER_RISK | - | Fullmix de-essing is low risk. | move_index=1, target=fullmix master, max_reduction_db=1.20 | Prefer isolated vocal de-essing when possible; keep fullmix de-essing narrow and light, then run brightness/vocal A/B. | - | yes |
