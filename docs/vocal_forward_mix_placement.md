# Vocal Forward Mix Placement

Vocal-forward does not mean vocal-louder. For Suno-style and AI vocal stems,
plain gain boosts often expose metallic tone, high-band fizz, source separation
residue, tuning artifacts, and phase instability. The safer goal is to create
space around the vocal while keeping the beat powerful.

## Core Strategy

The placement engine prefers dynamic instrumental space over raw vocal gain.
It plans conservative vocal-keyed dynamic EQ, multiband ducking, M/S cleanup,
backing vocal ducking, and send ducking before it allows gain. It does not add
pitch correction, master limiting, OTT, heavy compression, aggressive saturation,
or strong high-end boosts.

## Why Heavy Processing Hurts AI Vocals

AI vocals are often already compressed, tuned, denoised, reverbed, widened, and
limited. More compression or clipping can flatten consonants and make the voice
feel fake. Bright boosts can turn AI fizz into harshness. Widening can make
phasey vocals unstable or weak in mono.

## Analyzer Outputs

The placement analyzer writes:

- `automix/analysis_reports/{track_name}_vocal_placement_analysis.json`

It estimates:

- vocal loudness, peak, crest factor, body, presence, air, sibilance, harshness,
  and stability;
- masking in 120-350 Hz, 350-800 Hz, 800 Hz-2 kHz, 2-5 kHz, and 5-10 kHz;
- instrumental center and side density;
- vocal side leakage and center stability;
- mono compatibility and stereo width risk;
- existing reverb/delay tail masking.

These metrics are triage aids, not proof of audible improvement.

## Placement Profiles

The available profiles are:

- `minimal_vocal_gain_trim`
- `dynamic_space_creation`
- `lead_vocal_forward_clear`
- `fragile_ai_vocal_protect`
- `backing_vocal_duck_under_lead`
- `skip_placement`

Vocal gain is capped. Ducking is conservative. Fragile AI vocals use lower gain
and lighter ducking. Backing vocals and doubles can be gently ducked under the
lead instead of widening or brightening the lead.

## Routing Strategy

Routing is planned as dry-run metadata first:

- vocal to instrumental sidechain;
- vocal to backing vocal sidechain;
- vocal to reverb/delay send sidechain;
- rollback metadata for any created sends.

The preferred runtime strategy is draft-only placement: duplicate draft tracks
or buses, create draft routing, and leave original tracks, buses, routing, media,
master track, and accepted drafts untouched.

## A/B Evaluation

If a placement draft is rendered, evaluation writes:

- original mix section;
- placement draft;
- loudness-matched draft;
- difference render;
- `automix/eval_reports/{track_name}_vocal_placement_eval_metrics.json`.

Vocal audibility alone is not enough. Reject a placement draft if the beat loses
impact, low end gets weak, snare or hats pump, vocal harshness increases, vocal
gets thinner, stereo image shifts, phase correlation worsens, or reverb/delay
tails pump unnaturally.

Missing renders fail closed.

## When To Reject

Reject the placement draft when:

- it only sounds louder, not clearer;
- the beat becomes hollow or weak;
- the low end loses weight;
- the vocal becomes harsher, thinner, or more AI-like;
- backing vocals smear the lead;
- reverb or delay tails breathe unnaturally;
- stereo image or mono compatibility worsens.

Skipping placement or requiring manual mix work is a valid safety result.
