# Mesi 1 Single Pipeline

This is the current source of truth for future Mesi 1 work in this project.

## Accepted Final

- Current accepted final: `mesi_1_v42_vocal_down_1db_final`
- Accepted date: `2026-05-31`
- Final WAV: `renders/mesi_1_v42_vocal_down_1db_final/VOCAL_CLARITY_PASS01_FULL.wav`
- Final MP3: `renders/mesi_1_v42_vocal_down_1db_final/VOCAL_CLARITY_PASS01_FULL_320k.mp3`
- Deliverable ZIP: `renders/mesi_1_v42_vocal_down_1db_final/mesi_1_v42_VOCAL_DOWN_1DB_FINAL_DELIVERABLE.zip`
- REAPER project: `reaper/mesi_1_v42_vocal_down_1db_final/mesi_1_v42_VOCAL_DOWN_1DB_FINAL.rpp`
- Acceptance copy: `deliverables/mesi_1_ACCEPTED_FINAL_v42/`
- Final metrics: `-8.5 LUFS`, MP3 true peak `-1.5 dBTP`.
- Gate status: passed the mandatory Suno/AI vocal-chain gate with `JS: Codex Vocal AI Artifact Split Tamer` in the lead vocal chain.

## Preserve

- `renders/mesi_1_v35_louder_safe_peak_master/`
- `reports/mesi_1_v35_louder_safe_peak_master/`
- `reaper/mesi_1_v35_louder_safe_peak_master/`
- `tools/mesi_1_v35_louder_safe_peak_master.py`
- `renders/mesi_1_v42_vocal_down_1db_final/`
- `reports/mesi_1_v42_vocal_down_1db_final/`
- `reaper/mesi_1_v42_vocal_down_1db_final/`
- `tools/mesi_1_v42_vocal_down_1db_final.py`
- `deliverables/mesi_1_ACCEPTED_FINAL_v42/`
- `tools/validate_reaper_vocal_chain_gate.py`
- `reports/MESI_1_INTEGRATED_REPORT.md`

The old Mesi/0530/0531 iteration folders have been deleted. Other named render folders were left alone unless they match that repeated Mesi chain. Version `v42` is the user-accepted final; do not continue from `v35` unless explicitly asked.

## Do Not Reopen

- Do not use v28 as a valid clean-vocal proof.
- Do not resurrect 0530/0531 exploratory renders unless the user asks for forensic comparison.
- Do not create multiple candidate renders without a written stop rule.
- Do not replace `v42` as accepted final unless the user asks for a new revision.

## Command

Run the final locked delivery gate with:

```sh
python3 tools/mesi_1_v42_vocal_down_1db_final.py
```

That command verifies the v42 final WAV/MP3/ZIP, the QC metrics, and the mandatory Codex vocal-chain gate.
