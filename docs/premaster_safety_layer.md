# Premaster Safety Layer

Prompt 36 adds a premaster / master-bus safety layer for Suno-style and AI
vocal mixes. This is not a loudness maximizer and not a final mastering engine.
Its job is to decide whether the mix is safe enough for a conservative draft and
to block destructive master-bus processing when the mix itself needs revision.

## Core Rule

Do not fix vocal clarity on the master bus. If the vocal is buried, harsh,
phasey, too wet, or artifact-heavy, route the session back to recovery,
placement, or manual mix revision. The premaster layer may only make a
draft-only safety plan.

## Analyzer Outputs

The analyzer writes:

- `automix/analysis_reports/project_premaster_safety_analysis.json`

It estimates:

- integrated LUFS proxy, short-term loudness, peak, LRA, crest factor, peak
  density, and limiter-pressure risk;
- sub, bass, low-mid, mid, presence, harshness, sibilance, air, and ultra-high
  tonal balance;
- metallic harshness, high fizz, codec-birdies, sibilance splatter, phasey
  width, vocal thinness, and reverb-tail pumping risk;
- vocal forwardness, clarity, body, sibilance, harshness, and masking risk;
- stereo width, mid/side energy, mono compatibility, phase correlation, and
  low-end stereo risk;
- phone, earbud, club, small-speaker, and mono translation warnings.

These metrics are triage proxies. They are not a claim that the premaster sounds
better.

## Policy Outcomes

The policy can select:

- `safety_only_premaster`
- `safe_streaming_premaster`
- `loud_but_safe_premaster`
- `already_mastered_safety`
- `skip_premaster`
- `mix_revision_required`

`loud_but_safe_premaster` is allowed only for low-risk sources. If limiter
pressure, artifact risk, mono risk, or weak vocal forwardness is detected, the
policy downgrades to a safer mode or blocks premaster work.

## Chain Categories

Plans use semantic categories instead of fixed plugin parameter indexes:

- input trim;
- clean EQ;
- dynamic EQ;
- de-esser or harshness guard;
- low-end mono control;
- M/S EQ with no widening by default;
- conservative bus compression;
- optional subtle saturation;
- optional soft clipper;
- true-peak limiter;
- loudness meter;
- phase correlation meter;
- output gain.

Unknown or low-confidence semantic mappings are skipped. Paid plugins are not
required. Stock REAPER fallbacks are listed as intent, but the REAPER applicator
does not write uncertain parameters.

## Safety Limits

The profiles are intentionally conservative:

- no pitch correction;
- no exciter;
- no high-shelf clarity boost;
- no OTT or aggressive multiband processing;
- no master widening by default;
- no compressor, clipper, or saturation on already limited mixes;
- limiter gain is capped;
- target LUFS is capped when requested too loud;
- original master bus must remain untouched.

## A/B Evaluation

If an original mix render and premaster draft render exist, evaluation writes:

- `automix/eval_reports/project_premaster_eval_metrics.json`
- `automix/eval_reports/project_premaster_loudness_matched.wav`
- `automix/eval_reports/project_premaster_difference.wav`

Missing renders fail closed. A draft is rejected if it becomes louder but also
increases harshness, sibilance, metallic artifacts, high fizz, vocal thinness,
vocal-forwardness loss, beat impact loss, low-end loss, stereo shift, phase
worsening, limiter pumping, or reverb-tail pumping.

## Translation Check

The translation report writes:

- `automix/eval_reports/project_translation_check.json`

Review warnings for:

- mono fold-down risk;
- phone speaker vocal loss;
- earbud harshness;
- low-end translation;
- vocal sibilance;
- limiter pumping.

## Running

Dry scan:

```sh
python3 scripts/run_premaster_safety_workflow.py \
  --source-mix /path/to/mix.wav \
  --mode premaster_scan_only \
  --dry-run
```

Conservative plan:

```sh
python3 scripts/run_premaster_safety_workflow.py \
  --source-mix /path/to/mix.wav \
  --mode safe_streaming_premaster \
  --adapter-status-json automix/plugin_inventory.json \
  --output-dir automix \
  --dry-run
```

A/B evaluation after a separate draft render:

```sh
python3 scripts/run_premaster_safety_workflow.py \
  --source-mix /path/to/original_mix.wav \
  --premaster-draft /path/to/premaster_draft.wav \
  --render-ab \
  --dry-run
```

The Python workflow never modifies REAPER directly. `--apply-draft` is
fail-closed unless paired with `--dry-run`, and still only writes plans.

## REAPER Draft Applicator

`automix/apply_premaster_draft.lua` is disabled by default:

- `allow_draft_premaster=false`

When enabled on a saved project copy, it creates a muted `_PREMASTER_DRAFT`
track from one selected source mix print and writes rollback metadata. It does
not save, render, insert pitch correction, or touch the original master bus.

Skipping premaster or returning `mix_revision_required` is a successful safety
outcome when the mix is not ready.
