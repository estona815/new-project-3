# mesi_1_v11 Candidate QC

| candidate | score | classification | harshness_delta_db | sibilance_delta_db | air_fizz_delta_db | punch_delta_db | transient_ratio | side_mid_delta_db | true_peak_after_dbfs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C_punch_preserve | 100.287 | fullmix_rescue + Suno_DeAI_repair + master processing | -0.06 | -0.094 | -0.07 | 0.025 | 0.9971 | -0.314 | -1.4253022379948799 |
| E_drum_reinforcement | 94.351 | fullmix_rescue + drum_reinforcement + Suno_DeAI_repair + master processing | -0.089 | -0.157 | -0.125 | -0.021 | 0.8737 | -0.227 | -3.522195358348663 |
| D_reference_match | 93.534 | fullmix_rescue + Suno_DeAI_repair + master processing | -0.09 | -0.162 | -0.158 | -0.018 | 0.8628 | -0.231 | -3.618089176792904 |
| A_safe | 93.4 | fullmix_rescue + Suno_DeAI_repair + master processing | -0.029 | -0.1 | -0.086 | -0.094 | 0.8648 | -0.175 | -3.621821408553286 |
| B_more_deai | 91.738 | fullmix_rescue + Suno_DeAI_repair + master processing | 0.009 | -0.073 | -0.114 | -0.126 | 0.8446 | -0.155 | -3.806061281122277 |

- Selected: `C_punch_preserve`

## Rebeat QC

# Rebeat QC

- Selected candidate: `C_punch_preserve`
- Max severity: `WARN`

| Candidate | Classification | Status | Max severity | Render |
| --- | --- | --- | --- | --- |
| C_punch_preserve | fullmix_rescue | pass | PASS | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_candidate_C_punch_preserve.wav |
| E_drum_reinforcement | drum_reinforcement | warn_listen | WARN | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_candidate_E_drum_reinforcement.wav |
| D_reference_match | fullmix_rescue | pass | PASS | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_candidate_D_reference_match.wav |
| A_safe | fullmix_rescue | pass | PASS | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_candidate_A_safe.wav |
| B_more_deai | fullmix_rescue | pass | PASS | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_candidate_B_more_deai.wav |

## Findings

| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WARN | DRUM_REINFORCEMENT_NO_PUNCH_GAIN | /Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_candidate_E_drum_reinforcement.wav | Reinforcement improves punch. | punch_delta_db=-0.02, target=0.25 | Prefer no-reinforcement or reduce/realign drum support. | - | yes |
