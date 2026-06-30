# Plugin Capability Report

- Generated UTC: `2026-06-05T11:41:25Z`
- REAPER version: `unknown`
- Project: `unknown`
- Detected plugins: `0`
- Validated safe plugins: `0`
- Unsafe/unmapped plugins: `0`

## Safety Position

- This report does not prove audio quality or plugin behavior.
- Detected third-party plugins remain write-blocked until adapter validation passes.
- Missing commercial plugins are normal and should trigger stock/JSFX fallback planning.

## Detected Plugins

- none detected from the available inventory file

## Missing Expected Optional Plugins

- `MAutoPitch`: optional commercial or third-party plugin not detected; fallback should be used
- `TDR Nova`: optional commercial or third-party plugin not detected; fallback should be used
- `Decapitator`: optional commercial or third-party plugin not detected; fallback should be used
- `Valhalla Supermassive`: optional commercial or third-party plugin not detected; fallback should be used
- `Valhalla reverb/delay`: optional commercial or third-party plugin not detected; fallback should be used
- `OTT`: optional commercial or third-party plugin not detected; fallback should be used
- `Ozone`: optional commercial or third-party plugin not detected; fallback should be used
- `Soothe-like resonance suppressor`: optional commercial or third-party plugin not detected; fallback should be used
- `DSEQ-like resonance suppressor`: optional commercial or third-party plugin not detected; fallback should be used

## Fallback Strategy

- Pitch: use ReaPitch/manual only after semantic adapter validation.
- EQ/dynamics: prefer validated stock ReaEQ/ReaComp/ReaXcomp adapters; otherwise log as skipped.
- Saturation/OTT/Ozone/Valhalla: optional third-party only, never assumed safe from name matching.
- Unknown plugins: inventory/report only; no automated parameter writes.
