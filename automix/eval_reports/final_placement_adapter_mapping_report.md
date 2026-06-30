# Final Placement Adapter Mapping Report

- Project: `mesi_1_v37_VOCAL_CLARITY_FINAL`
- Apply allowed: `False`
- All required categories safe: `False`
- Blocked reasons: `harshness_guard_adapter_not_validated, ms_cleanup_adapter_not_validated, multiband_ducker_adapter_not_validated, output_gain_adapter_not_validated, send_return_ducker_adapter_not_validated, sidechain_ducker_adapter_not_validated, sidechain_dynamic_eq_adapter_not_validated, utility_gain_adapter_not_validated`

## Category Results

| Category | Target | Plugin | Adapter | Safe | Required Controls | Reason Codes |
|---|---|---|---|---:|---|---|
| `utility_gain` | `lead_vocal` | `ReaComp (Cockos)` | `reacomp_adapter` | `False` | `vocal_gain_db` | `ADAPTER_CONFIDENCE_LOW, FALLBACK_REQUIRED, SEMANTIC_CONTROL_MISSING, VALIDATION_MISSING` |
| `sidechain_dynamic_eq` | `instrumental_bus` | `ReaComp (Cockos)` | `reacomp_adapter` | `False` | `instrumental_duck_amount_db, presence_duck_amount_db, low_mid_duck_amount_db, sibilance_conflict_duck_db, duck_attack_ms, duck_release_ms` | `ADAPTER_CONFIDENCE_LOW, FALLBACK_REQUIRED, SEMANTIC_CONTROL_MISSING, VALIDATION_MISSING` |
| `multiband_ducker` | `instrumental_bus` | `ReaComp (Cockos)` | `reacomp_adapter` | `False` | `instrumental_duck_amount_db, duck_attack_ms, duck_release_ms` | `ADAPTER_CONFIDENCE_LOW, FALLBACK_REQUIRED, SEMANTIC_CONTROL_MISSING, VALIDATION_MISSING` |
| `ms_cleanup` | `instrumental_bus` | `ReaComp (Cockos)` | `reacomp_adapter` | `False` | `ms_mid_cleanup_amount, ms_side_cleanup_amount` | `ADAPTER_CONFIDENCE_LOW, FALLBACK_REQUIRED, SEMANTIC_CONTROL_MISSING, VALIDATION_MISSING` |
| `sidechain_ducker` | `backing_vocals` | `ReaComp (Cockos)` | `reacomp_adapter` | `False` | `backing_duck_amount_db, duck_attack_ms, duck_release_ms` | `ADAPTER_CONFIDENCE_LOW, FALLBACK_REQUIRED, SEMANTIC_CONTROL_MISSING, VALIDATION_MISSING` |
| `send_return_ducker` | `send_returns` | `ReaComp (Cockos)` | `reacomp_adapter` | `False` | `send_duck_amount_db, duck_attack_ms, duck_release_ms` | `ADAPTER_CONFIDENCE_LOW, FALLBACK_REQUIRED, SEMANTIC_CONTROL_MISSING, VALIDATION_MISSING` |
| `harshness_guard` | `lead_vocal` | `ReaComp (Cockos)` | `reacomp_adapter` | `False` | `harshness_guard_amount, sibilance_control_amount` | `ADAPTER_CONFIDENCE_LOW, FALLBACK_REQUIRED, SEMANTIC_CONTROL_MISSING, VALIDATION_MISSING` |
| `output_gain` | `lead_vocal` | `ReaComp (Cockos)` | `reacomp_adapter` | `False` | `vocal_gain_db` | `ADAPTER_CONFIDENCE_LOW, FALLBACK_REQUIRED, SEMANTIC_CONTROL_MISSING, VALIDATION_MISSING` |

## Safety

- Pitch correction remains blocked.
- No final export is created.
- No parameter index assumptions are allowed.
- REAPER parameter writes require target-name lookup and normalized 0-1 values.
- If this report is not fully safe, the REAPER applicator must remain disabled.
