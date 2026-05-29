# Mesi v10 Evidence Pipeline Harness

This document freezes the useful part of the `mesi_1_v10` pass into a reusable repo-local contract. The quoted lines below are the source of truth for the claim gate; automation may elaborate implementation details, but it must not weaken these statements.

## Quoted Contract

> If the only source is MP3, mark it as lossy source.

> Do not claim true rebeat unless drums, bass, and core music elements are actually reconstructed as MIDI/audio/stem tracks inside the REAPER project and bus renders exist.

> If any validation result is WARN or higher, do NOT claim final success.

> `drum_reinforcement` was rendered as candidate E and audited in the RPP, but it was not selected for the final WAV.

> This is not `true_rebeat`, not `stem rebuild`, not `vocal tuned`, and not `lossless restoration`.

> REAPER project was generated and audited, but audio candidates were rendered through the Python/ffmpeg fallback path.

## Harness Files

- `presets/pipeline_contracts/mesi_v10_evidence_contract.json`: machine-readable quote-backed claim policy.
- `harness/pipeline_claim_contract.py`: checks evidence JSON against the policy.
- `tests/test_pipeline_claim_contract.py`: smoke coverage for lossy-source language, true-rebeat blocking, WARN+ final blocking, and the v10 drum-candidate distinction.

## Evidence Command

```sh
python3 harness/pipeline_claim_contract.py \
  --contract presets/pipeline_contracts/mesi_v10_evidence_contract.json \
  --evidence reports/mesi_1_v10_final_report.json \
  --out-json reports/mesi_1_v10_pipeline_claim_contract.json \
  --out-md reports/mesi_1_v10_pipeline_claim_contract.md
```

## Required Behavior

- MP3-derived WAV is a working format only, not lossless restoration.
- `true_rebeat` is blocked unless drum, bass, music, grid, bus-render, RPP-audit, MIDI-audit, and before/after QC evidence all exist.
- A rendered or audited drum reinforcement candidate does not describe the selected final unless that candidate is actually selected.
- A generated RPP does not prove a REAPER-app audio render; fallback rendering must be labeled.
- WARN/FAIL/BLOCKER findings keep the claim in `not_final_warn_plus`.
