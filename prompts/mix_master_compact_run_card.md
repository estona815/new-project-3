# Compact Mix/Master Run Card

## Goal

Run the next REAPER AI/Suno mix-master pass with thin prompting and thick state
files. Do not attempt final delivery unless the compact gates prove it.

## Inputs

Read only the compact order first:

1. `work/state/RUN_CONTEXT.compact.json`
2. `work/state/current_state_summary.md`
3. `work/state/QUALITY_GATE.compact.json`
4. `reports/latest_qc_headline.json`
5. `work/blockers/open_blockers.json`
6. `work/state/PASS_PLAN.latest.json`

Open long docs or old logs only when a listed blocker directly requires them.

## Current Blockers

Use `open_blockers` and `QUALITY_GATE.compact.json` as the source of truth. If
`safe_to_export` is false, status may only be `blocked` or `review_copy`.

## Primary Target

Choose exactly one:

`vocal_clarity`, `vocal_center_stability`, `female_layer_control`,
`low_end_density`, `instrumental_presence`, `ai_fizz_reduction`,
`master_cohesion`, `limiter_pressure_control`.

Default candidate render count is one. Use two only for necessary A/B comparison.
Do not create three or more without explicit user request.

## Forbidden Actions

- No final delivery or commercial-ready claim while gates are incomplete.
- No louder master before masking, harshness, AI fizz, low-mid mud, mono
  fold-down, and limiter pressure checks.
- Never put raw full mix/reference in the active premaster/master path.
- Male vocal stays center lead.
- Female vocal cannot be lead; side/shadow/double/harmony only.

## Required Outputs

Update compact state, pass plan, plugin trace status, QC headline, open blockers,
and next action. Render/QC/A-B paths must be real files before claiming
`qc_passed_review_ready`.

## Status Update Rule

Reply with changed files, blockers, QC headline, delivery status, one next
primary target, and the next command. Avoid full-document summaries.
