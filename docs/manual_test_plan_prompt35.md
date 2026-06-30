# Manual Test Plan Prompt 35

Use a saved copy of a REAPER project. Do not test on the only copy of a
session.

## Placement Analysis

1. Run `python3 scripts/run_vocal_placement_workflow.py --project SESSION.rpp --dry-run`.
2. Confirm `project_vocal_placement_matrix.json` exists.
3. Confirm lead vocal tracks produce
   `automix/analysis_reports/{track_name}_vocal_placement_analysis.json`.
4. Confirm masking, spatial, and send/tail profiles are present.

## Policy Safety

1. Full-mix sources must produce `stem_required` or `manual_mix_required`.
2. Missing instrumental bus must produce `manual_mix_required`.
3. Buried vocals should prefer dynamic space creation over large vocal gain.
4. Harsh or fragile AI vocals should use lighter placement.
5. Backing vocals and doubles should duck under the lead when needed.

## Routing Plan

1. Confirm `automix/chain_plans/{track_name}_vocal_sidechain_routing_plan.json`
   exists for placement draft decisions.
2. Confirm the routing plan is dry-run and preserves existing sends.
3. Confirm rollback metadata lists created sends and draft tracks.

## Draft Safety

1. Keep `allow_draft_vocal_placement=false` in the Lua applicator and run it.
2. Confirm no track, FX, routing, master, or media changes occur.
3. On a project copy, enable only after reviewing `safe_to_apply=true`.
4. Confirm the draft is named `_PLACEMENT_DRAFT` and original mix is unchanged.

## A/B Evaluation

1. Render original mix, placement draft, loudness-matched draft, and difference.
2. Confirm missing renders fail evaluation.
3. Reject if the beat weakens, low end thins, hats/snare pump, vocal gets harsh,
   stereo shifts, phase worsens, or AI artifacts become more exposed.

## Human Review

Accept only if the vocal is clearer in context without simply being louder and
the instrumental still feels strong.
