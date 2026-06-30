# Suno / AI Vocal Recovery

Suno-style and other AI vocal stems are often not raw vocals. They can already
contain pitch correction, compression, limiting, EQ, reverb, stereo widening,
source separation residue, codec artifacts, and synthetic high-band fizz.

The recovery stage exists before pitch correction because pitch tools can lock
onto those artifacts and make them more obvious. The safest result is sometimes
no recovery and no pitch correction.

## Core Rule

Recovery is conservative, draft-only, and preservation-first. It must not make
the vocal dull, underwater, phasey, smeared, thinner, more robotic, more
metallic, or less emotionally clear.

No pitch correction is inserted in the vocal recovery chain.

## Why More Processing Can Make AI Vocals Worse

Already processed AI vocals have fewer clean degrees of freedom. Heavy denoise
can remove consonants and breath. Heavy compression can flatten an already
limited source. Saturation can hide fizz for a moment but create harsher upper
mids. Stereo widening can make source-separated phase residue collapse in mono.

For that reason the recovery policy reduces processing intensity when
`already_mixed_score` is high, disables compression when the source appears
limited, avoids added reverb when reverb is already baked in, disables widening
when phase risk is high, and protects body when the vocal is thin.

## Analyzer Outputs

The recovery analyzer writes:

- `automix/analysis_reports/{track_name}_vocal_recovery_analysis.json`

It estimates:

- metallic harshness
- watery phase texture
- codec birdies
- formant wobble
- sibilance warble
- reverb smear
- side noise
- high-band fizz
- low-mid mud
- nasal resonance
- transient smear
- vocal thinness
- compression limiting
- baked reverb
- stereo width
- mono compatibility risk
- phase correlation

These are triage metrics, not proof of audible improvement.

## Recovery Profiles

The available semantic profiles are:

- `minimal_cleanup`
- `conservative_ai_vocal_cleanup`
- `source_separated_rescue`
- `thin_vocal_body_preserve`
- `skip_recovery`

They are semantic settings, not fixed plugin indexes. Unknown or low-confidence
plugin parameters are skipped.

## Draft Safety

Recovery plans target `{track_name}_RECOVERY_DRAFT`. The original track, media,
FX, and routing must remain untouched. Rollback metadata is written under:

- `automix/rollback/{track_name}_vocal_recovery_rollback.json`

The Python planner does not directly modify REAPER. A future REAPER runtime
applicator must create the draft under an undo block and validate the original
track state after application.

## A/B Evaluation

If a recovery draft is rendered, the evaluation writes:

- original render
- recovered render
- loudness-matched recovered render
- difference render
- `automix/eval_reports/{track_name}_vocal_recovery_eval_metrics.json`

Artifact reduction alone is not enough. Reject the recovery if the vocal loses
clarity, air, body, transients, formant stability, phase stability, or if the
difference signal contains too much main vocal body.

Missing renders fail closed.

## Interaction With Pitch Correction

Pitch correction must wait until vocal recovery analysis has run.

The order is:

1. Track role detection.
2. Source classification.
3. Vocal recovery analysis.
4. Vocal recovery policy decision.
5. Optional recovery draft.
6. Recovery A/B evaluation.
7. Pitch triage.
8. Pitch safety gate.
9. Optional pitch draft.
10. Pitch A/B evaluation.
11. Human review.

If recovery requires a draft and the draft has not passed A/B review, pitch
correction is blocked or routed to manual review. If the source is a full mix,
the system requests an isolated vocal stem before recovery and pitch correction.

## When To Request A Better Stem

Request a better isolated lead vocal stem when:

- full-mix likelihood is high;
- source-separated likelihood is high and no audio-backed rescue analysis is
  available;
- watery phase and reverb smear are severe;
- mono compatibility risk is high;
- recovery would need aggressive denoise, widening, compression, or saturation.

Skipping recovery or requesting a stem is a valid successful safety result.
