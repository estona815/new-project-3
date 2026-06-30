# Reference Matching / Genre Targeting

Prompt 38 adds reference matching and genre targeting for digicore, hyperpop,
hip-hop, and AI/Suno vocal mixes. It compares broad mix features only. It does
not recreate or copy a reference song.

## Reference Safety

References are used for tonal, energy, loudness, stereo, vocal-balance, and
translation comparison. The system does not copy melody, lyrics, arrangement,
artist identity, vocal tone, drums, chords, or reference audio into the final
project.

## Safety Overrides Matching

Target profiles are guides, not commands. Safety constraints override reference
matching:

- If the reference is brighter but the current vocal has AI fizz, high-shelf
  boosts are blocked.
- If the reference is louder but the current mix is already limited, more
  limiting is blocked.
- If the reference is wider but the current mix has phase risk, master widening
  is blocked.
- If 808 is weak but the low-end is muddy, low-end control comes before boost.
- If drums need energy, the planner avoids master clipping as the first move.

## AI Vocal Caution

AI/Suno vocals can become more fake when pushed toward reference brightness or
loudness. The safe planner prefers dynamic space, low-end control, harshness
guards, and draft-only A/B review before any gain, brightness, saturation, or
loudness move.

## Target Profiles

Implemented profiles:

- `digicore_hyperpop_hiphop_vocal_forward`
- `raw_digicore_intense`
- `clean_commercial_ai_repair`
- `melody_sample_flip_forward`
- `phone_reels_loud_clear`

Use target-profile-only mode when no lawful reference audio exists.

## Outputs

The workflow writes:

- `automix/reference/reference_manifest.json`
- `automix/analysis_reports/reference_{name}_analysis.json`
- `automix/analysis_reports/current_mix_reference_features.json`
- `automix/eval_reports/reference_match_comparison.json`
- `automix/chain_plans/project_reference_match_adjustment_plan.json`
- `automix/rollback/project_reference_match_rollback.json`
- `automix/eval_reports/reference_match_eval_metrics.json`
- `automix/eval_reports/reference_match_iteration_history.json`
- `automix/eval_reports/reference_match_report.md`
- `automix/eval_reports/project_reference_match_matrix.json`

## Running

Reference scan:

```sh
python3 scripts/run_reference_match_workflow.py \
  --project /path/to/project.rpp \
  --current-mix /path/to/current_mix.wav \
  --reference /path/to/ref.wav \
  --reference-role primary_reference \
  --target-profile digicore_hyperpop_hiphop_vocal_forward \
  --dry-run
```

Target profile only:

```sh
python3 scripts/run_reference_match_workflow.py \
  --project /path/to/project.rpp \
  --target-profile phone_reels_loud_clear \
  --mode target_profile_scan_only \
  --dry-run
```

Draft metadata:

```sh
python3 scripts/run_reference_match_workflow.py \
  --project /path/to/project.rpp \
  --current-mix /path/to/current_mix.wav \
  --reference /path/to/ref.wav \
  --target-profile raw_digicore_intense \
  --mode conservative_reference_match_draft \
  --apply-draft \
  --dry-run
```

## Reading The Report

`reference_match_report.md` separates:

- current mix vs target profile;
- current mix vs each reference;
- safe adjustment priorities;
- unsafe blocked adjustments;
- draft-only adjustment plan;
- A/B evaluation metrics;
- iteration history;
- manual listening checklist.

Match improvement alone is not enough. Reject a reference-match draft if the
song becomes harsher, fizzier, more metallic, more phasey, less emotional, more
AI-like, weaker in beat impact, or worse at equal loudness.

If reference matching changes mix balance, premaster safety must rerun before
final export.

