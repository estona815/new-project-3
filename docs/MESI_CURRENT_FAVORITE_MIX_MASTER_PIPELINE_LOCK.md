# Mesi Current Favorite Mix/Master Pipeline Lock

This document freezes the current user-preferred `mesi_1_v11` direction as a repo-local default for future `mesi_1` passes.

The lock is not a claim that the render is a final professional master. It is a taste and safety contract: preserve the clean/clear v11 balance, prevent heavier cleanup from becoming the default, and keep all WARN+ limitations visible.

## Locked Source

- Song: `mesi_1`
- Locked version: `v11`
- Preferred selected candidate: `C_punch_preserve`
- Evidence report: `reports/mesi_1_v11_final_report.md`
- Machine lock: `presets/pipeline_contracts/mesi_current_favorite_mix_master_lock.json`
- Harness checker: `harness/pipeline_preference_lock.py`

## Actual Classification To Preserve

Use this wording:

`fullmix_rescue + Suno_DeAI_repair + master processing`

The current favorite may mention drum reinforcement only as candidate/audit evidence. It must not say the selected final is drum-rebuilt unless a later version actually selects and validates that route.

## Why Candidate C Is Locked

`C_punch_preserve` is the preferred current direction because it made only small, controlled changes:

- Harshness: `-0.060 dB`
- Sibilance: `-0.094 dB`
- Air/fizz: `-0.070 dB`
- Punch: `+0.025 dB`
- Transient ratio: `0.997`
- Side/mid: `-0.314 dB`
- Duration delta: `0.000 sec`
- Peak/true-peak proxy: about `-1.43 dBFS`

This is the current "cleaner and clearer, but not over-cleaned" target.

## Locked Processing Character

- Mild Suno/AI artifact control, especially in high-side fizz bands.
- Dynamic/semi-narrow resonance control before broad tonal EQ.
- Light fullmix de-essing only when the sibilance metric or listening note justifies it.
- M/S side wash control that does not collapse width.
- Minimal compression and limiting. Do not chase loudness by flattening the track.
- Protect 45-140 Hz punch and vocal presence around 900 Hz-3 kHz.
- Treat future improvement as stem-level cleanup first, not heavier fullmix processing.

## Candidates That Must Not Become Default Automatically

- `B_more_deai`: too risky as a default because stronger cleanup can reduce punch/transient clarity.
- `E_drum_reinforcement`: kept as an audit/candidate only because grid confidence failed and punch gain was not proven.

## Required Honesty Language

The source route is MP3-derived, so reports must keep this meaning:

`Source was lossy MP3. Output is improved processing/mastering, not true lossless restoration.`

Forbidden without new evidence:

- `true_rebeat`
- `비트 다 새로 찍음`
- `stem rebuild`
- `vocal tuned`
- `lossless restoration`
- `professional final master`
- `noise completely removed`

## Lock Command

```sh
python3 harness/pipeline_preference_lock.py \
  --lock presets/pipeline_contracts/mesi_current_favorite_mix_master_lock.json \
  --evidence reports/mesi_1_v11_final_report.json \
  --candidate-qc reports/mesi_1_v11_candidate_qc.json \
  --out-json reports/mesi_1_v11_current_favorite_pipeline_lock.json \
  --out-md reports/mesi_1_v11_current_favorite_pipeline_lock.md
```

## Future Route

For the next `mesi_1` pass:

1. Start from the latest user-preferred print or from cleaner stems if available.
2. Run candidate generation, but compare every candidate against this lock.
3. Select `C_punch_preserve`-style processing unless the user explicitly approves a different A/B result.
4. Keep WARN+ findings in the report. The lock does not clear validation warnings.
5. For meaningful improvement beyond this point, prioritize cleaner vocal/instrument stems or stem-level noise repair.
