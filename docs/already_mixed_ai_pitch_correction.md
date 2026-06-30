# Already-Mixed AI Pitch Correction

Suno-style and similar AI-generated sources are often not raw vocals. They may
already contain pitch correction, compression, EQ, stereo widening, reverb,
limiting, source-separation residue, codec-like artifacts, and mastered full-mix
content. Treating that material like a dry monophonic vocal is unsafe.

For these sources, the safest pitch correction is often no pitch correction.

## Why It Is High Risk

Pitch correction can damage already-processed AI audio by:

- exaggerating metallic or watery artifacts;
- pulling reverb tails into audible pitch warble;
- flattening natural or generated vibrato;
- creating comb-filtered doubled vocals;
- shifting formant identity;
- smearing consonants and sibilants;
- damaging drums, bass, and instruments when the source is actually a full mix.

The system must never make a source more robotic, metallic, phasey, or fake just
to make pitch appear more locked.

## Why Already Mixed Means Less Processing

Already mixed material has fewer clean degrees of freedom. Compression,
limiting, EQ, stereo ambience, denoise, reverb, and pitch correction may already
be baked into the waveform. Additional pitch correction therefore affects not
only the lead vocal pitch, but also consonants, reverb tails, doubled layers,
instrument bleed, and source-separation residue. The correct response to a high
`already_mixed_score` is reduced processing or no processing.

## Why Full Mixes Should Not Be Tuned

Full mixes are polyphonic. A vocal pitch corrector cannot reliably distinguish
the singer from bass, chords, drums, cymbals, reverbs, and stereo side content.
Prompt 32 treats high `full_mix_likelihood` as a hard block unless the user
explicitly requests a full-mix draft experiment. Even then, the correction is
limited to a duplicated draft with very low correction and mandatory A/B review.

## Why Source-Separated Vocals Often Fail

Source-separated vocals can contain watery phase texture, accompaniment bleed,
reverb smear, and unstable harmonics. Pitch correction can lock onto the wrong
component and make the artifacts louder. Source-separated material defaults to
skip or phrase-limited micro correction only.

## Why Already Tuned Vocals Usually Stay Alone

An already tuned vocal may show pitch snapping, flattened note centers, stepped
transitions, and reduced natural drift. Stacking strong pitch correction on top
usually creates robotic stepping, sibilance warble, and formant damage. If
`already_tuned_score > 0.85`, Prompt 32 skips global correction. If it is above
`0.70`, only micro correction is considered, and only when a real benefit is
clear.

## Required Source Classification

Pitch correction is not considered until source classification has run. Prompt
31 uses these classes:

- `raw_vocal`: likely dry or semi-dry monophonic vocal.
- `mixed_vocal_stem`: vocal stem, but already compressed/EQ'd/reverbed.
- `ai_vocal_stem`: AI-generated or AI-converted vocal stem with possible baked
  tuning and artifacts.
- `source_separated_vocal`: extracted vocal with bleed, reverb smear, or watery
  artifacts.
- `full_mix`: drums, bass, instruments, and vocal together.
- `unknown`: not enough confidence.

Reports are written under `automix/analysis_reports/`:

- `{track_name}_source_classification.json`
- `{track_name}_pitch_analysis.json`

## Detection Signals

The analyzer estimates:

- `already_mixed_score`
- `already_tuned_score`
- `baked_reverb_score`
- `full_mix_likelihood`
- `source_separated_likelihood`
- `compression_limited_score`
- `monophonic_pitch_confidence`
- `polyphonic_contamination_score`

These are safety heuristics, not final listening judgments. A high risk score
means the system should process less, not more.

## Decision Policy

Full mixes are not auto-tuned by default. If `full_mix_likelihood > 0.65`, the
plan is `apply=false` and the recommendation is `full_mix_unsafe` or
`stem_required`.

Already-tuned sources are not strongly corrected. If `already_tuned_score >
0.70`, only micro-correction may be proposed. If `already_tuned_score > 0.85`,
global correction is skipped.

Low pitch confidence blocks automatic correction. If monophonic pitch confidence
is low, the plan becomes manual review only.

Unknown plugin parameters are skipped. A pitch adapter must expose
high-confidence semantic mappings before any parameter is written.

## Batch Track Triage

Prompt 33 adds project-level triage before any multi-track AutoTune decision.
The scanner classifies tracks as `lead_vocal`, `backing_vocal`,
`vocal_double`, `adlib`, `vocal_bus`, `instrumental_bus`, `drums`, `bass`,
`guitar`, `piano`, `synth`, `fx`, `full_mix_reference`, `master`, or
`unknown`.

Not every vocal-like track should be tuned. Lead vocals may receive the normal
conservative profile only when the safety gate allows it. Backing vocals,
doubles, and adlibs are automatically scaled lighter because strong correction
on stacked vocals usually creates blur, phase movement, and robotic layer
smear. Vocal buses are treated as high-risk review targets, not normal tuning
targets, because they may contain multiple singers, harmony, printed reverb, or
parallel processing.

Full-mix references, masters, instrumental buses, drums, bass, guitars, pianos,
synths, and FX tracks are not pitch-correction targets. `unknown` is also
skipped by default. These skips are not failures; they are visible safety
decisions in `project_pitch_triage_matrix.json` and the batch report.

Source-separated vocals and full-mix-like tracks generate stem-required reports
instead of hidden correction attempts. A `stem_required` result means the
automation did useful work: it found that a safer isolated lead stem is needed
before pitch correction should be considered.

## PitchSafetyGate

Prompt 32 centralizes eligibility in `automix/pitch/pitch_safety_gate.py`. The
gate fails closed:

- uncertainty reduces correction;
- low pitch confidence skips correction;
- full mixes are blocked by default;
- low adapter confidence blocks parameter writes;
- missing `correction_amount`/`depth`, `dry_wet`, or `speed` controls blocks
  automatic application;
- missing formant preservation halves the maximum correction amount;
- every applied correction is draft-only and requires A/B evaluation.

## Conservative Settings

Already-mixed AI vocal default:

```json
{
  "correction_amount": 0.08,
  "speed": 0.15,
  "depth": 0.15,
  "formant_preserve": 1.0,
  "humanize": 0.70,
  "vibrato_preserve": 0.80,
  "dry_wet": 0.35,
  "output_gain": 0.0
}
```

Raw vocal default:

```json
{
  "correction_amount": 0.25,
  "speed": 0.30,
  "depth": 0.30,
  "formant_preserve": 1.0,
  "humanize": 0.60,
  "vibrato_preserve": 0.70,
  "dry_wet": 0.60,
  "output_gain": 0.0
}
```

Full mix default:

```json
{
  "apply": false,
  "correction_amount": 0.0
}
```

## Draft-Only Workflow

If a plan is eligible and the user explicitly enables the REAPER applicator:

1. The original track remains untouched.
2. A duplicate track is created with `_PITCH_DRAFT` suffix.
3. The draft track is muted by default to avoid changing project playback.
4. Pitch correction is inserted only on the draft.
5. Only high-confidence semantic controls are written.
6. Unknown or low-confidence parameters are skipped.
7. Rollback data is written.
8. A/B and difference evaluation are required before acceptance.

The applicator is disabled by default in
`automix/apply_conservative_pitch_draft.lua`.

## MAutoPitch / AutoTune Adapter Safety

MAutoPitch, AutoTune-style plugins, and ReaPitch are accessed only through
semantic controls. The system does not assume fixed parameter indexes. A learned
or discovered mapping must be high-confidence before a parameter is written.
Unknown and low-confidence parameters are listed as skipped controls in the
chain plan and report.

## A/B And Difference Monitoring

When a processed draft WAV exists, run the analyzer with `--processed` to write:

- `automix/eval_reports/{track_name}_pitch_metrics.json`
- `automix/eval_reports/{track_name}_pitch_difference.wav`
- `automix/eval_reports/{track_name}_pitch_report.md`

Review:

- pitch error improvement;
- formant drift;
- metallic increase;
- clarity and air loss;
- transient loss;
- stereo width change;
- difference source energy.

The difference file is not a denoise residual. It is a damage monitor.

## A/B Interpretation

Pitch error improvement is not enough. Evaluation fails if the draft introduces
formant drift, metallic increase, clarity or air loss, transient loss, stereo
instability, tail warble, reverb pitch drag, or high source energy in the
difference signal. Missing renders also fail closed.

## Rollback Conditions

Reject or reduce pitch correction if any of these appear:

- robotic stepping;
- metallic tone increase;
- formant drift;
- sibilance warble;
- reverb tail pitch drag;
- thinner or cloudier vocal tone;
- full-mix instrumental damage;
- difference signal containing too much musical source.

Never keep a pitch correction chain that only sounds more in tune but lower
quality.

## Manual Listening Checklist

- Does the vocal sound more robotic?
- Are sibilants warbling?
- Did reverb tails start bending?
- Did the vocal get thinner?
- Did consonants smear?
- Did stereo image become unstable?
- Did the source sound more AI-like?
- Is the improvement only pitch-locking but not musical quality?
