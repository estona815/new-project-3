# Current Favorite Mix/Master Preference Lock

- Lock: `mesi_current_favorite_mix_master_lock`
- Song: `mesi_1`
- Preferred candidate: `C_punch_preserve`
- Selected candidate: `C_punch_preserve`
- Classification: `fullmix_rescue + Suno_DeAI_repair + master processing`
- Lock status: `locked_with_known_limitations`
- Max severity: `INFO`

## Findings

| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |
| --- | --- | --- | --- | --- | --- | --- | --- |
| INFO | PREFERENCE_LOCK_WARN_PLUS_SURFACED | - | A preferred style lock clears validation limitations. | EXTERNAL_VALIDATOR_WARN,FULLMIX_ACTIVE_WITH_REBUILD_ITEMS,FULLMIX_DEESSER_RISK,GRID_CONFIDENCE_FAIL,INTEGRATED_LOUDNESS_UNAVAILABLE,LOSSY_SOURCE_REBEAT_LIMITATION,REAPER_RENDER_FALLBACK,REBEAT_BUS_RENDERS_MISSING | Keep WARN+ language in reports; fix unknown WARN+ codes before treating this as a stronger delivery claim. | - | yes |

## Metric Summary

```json
{
  "air_fizz_delta_db": -0.07,
  "duration_after": 105.850688,
  "duration_before": 105.850688,
  "harshness_delta_db": -0.06,
  "peak_after_dbfs": -1.4253022379948799,
  "punch_delta_db": 0.025,
  "sibilance_delta_db": -0.094,
  "side_mid_delta_db": -0.314,
  "transient_ratio": 0.9971,
  "true_peak_after_dbfs": -1.4253022379948799
}
```

## Allowed Language

- `fullmix rescue`
- `Suno DeAI repair`
- `lossy-source processed print`
- `candidate C_punch_preserve selected`
- `drum reinforcement candidate/audit only`
- `human listening required before stronger final claims`

## Forbidden Language Without Evidence

- `true_rebeat`
- `true rebeat`
- `비트 다 새로 찍음`
- `stem rebuild`
- `vocal tuned`
- `lossless restoration`
- `professional final master`
- `noise completely removed`
