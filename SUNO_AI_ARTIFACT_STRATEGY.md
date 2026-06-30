# Suno / AI Artifact Strategy

The goal is conservative artifact risk reduction, not flawless cleanup.

## Artifacts To Watch

- high-band fizz
- metallic 3-5 kHz edge
- watery smear
- fake stereo halo
- smeared consonants
- phasey ambience
- unstable vocal texture
- over-compressed vocal body
- over-limited transient shape
- plastic high end
- side-channel hash
- codec-like swirls
- reverb tail noise

## Required Language

Use:

- artifact reduction
- artifact suppression
- conservative restoration
- AI-like texture risk reduction
- perceived noise reduction
- human review required

Avoid language that implies flawless artifact cleanup or unsupported commercial
equivalence.

## Safe Order

1. Estimate AI/Suno-like source probability.
2. Detect already processed source risk.
3. Run the artifact evidence gate so report-only metrics, source signals, and
   user feedback are not confused with measured render/QC evidence.
4. Use conservative mode by default when AI risk is high.
5. Protect formants, consonants, transients, and body.
6. Prefer dynamic notch, dynamic EQ, de-essing, spectral harshness reduction,
   and M/S side cleanup.
7. Render loudness-matched A/B before acceptance.
8. Require user review for accepted candidates.

## First-Slot Rescue Gate

For clean-main-vocal rescue, follow
[REAPER_REFERENCE_MIX_PIPELINE.md](REAPER_REFERENCE_MIX_PIPELINE.md). The
developed Suno/AI artifact plugin must be verified by actual REAPER plugin
trace before final claims.

Fallback plugins are not proof that the developed first-slot rescue plugin was
used.

## Rejection Criteria

Reject or revise if the vocal becomes dull, thin, robotic, phasey, lispy,
smeared, less emotional, or more visibly AI-like at matched loudness.

## Artifact Cleanup Cookbook

Use this as diagnosis guidance only. Do not invent measurements when no audio
file is available.

### Metallic High-End Hiss

- Detection: elevated 8-16 kHz band share, side-channel hash, harshness visible
  in spectrum, user reports "metallic" or "plastic" top.
- Tools: `JS: Codex Vocal AI Artifact Split Tamer`, `TDR Nova`, `Vocal Clarity
  Air Guard`, `ReaEQ`.
- Start range: dynamic attenuation 0.5-2.5 dB above 8 kHz; Air Guard mix
  0.20-0.45; avoid broad air boosts.
- Failure signs: dull consonants, missing breath texture, cymbals disappear,
  matched A/B feels smaller without less harshness.

### Harsh Sibilance

- Detection: 5-10 kHz band share, narrow bursts on S/T/SH, de-ess gain
  reduction only during consonants.
- Tools: `TDR Nova`, `JS: De-esser`, `ReaXcomp`, item gain for isolated spikes.
- Start range: 1-4 dB gain reduction, fast attack, release 40-160 ms.
- Failure signs: lisping, de-esser pumping vowels, vocal moves behind beat.

### Vocal Warble

- Detection: unstable pitch/formant trace, watery tail after notes, user A/B
  reports "robot/water" even when level matched.
- Tools: first-slot `Codex Vocal AI Artifact Split Tamer`, light `TDR Nova`,
  `Vocal Clarity De-Mud Dynamic EQ`; avoid live pitch inserts unless stylized.
- Start range: Artifact Split Tamer Amount 20-45, Mask Strength 0.25-0.45,
  Max Reduction 4-8 dB.
- Failure signs: formants flatten, emotion drops, tune artifacts become more
  obvious, residual monitor contains obvious lead body.

### Smeared Hats / Cymbals

- Detection: transient blur in 6-12 kHz, wide side smear, mono check collapses
  top rhythm.
- Tools: `TDR Nova`, `ReaEQ`, `ReaXcomp`, `Ozone Imager 2` only after mono
  check.
- Start range: narrow dynamic high-mid attenuation 0.5-2 dB; reduce width above
  8 kHz before adding brightness.
- Failure signs: hats lose groove, snare dulls, stereo top vanishes in mono.

### Fake Stereo / Mono Collapse

- Detection: stereo correlation below 0.25, side level dominates mid, mono
  loudness delta outside -1 to +1 dB.
- Tools: `Ozone Imager 2`, `Wider` only with caution, `ReaEQ` M/S-capable JSFX,
  pan/routing fixes.
- Start range: low end mono below 120 Hz; reduce side 2-4 dB in artifact band;
  keep lead vocal center.
- Failure signs: hook gets smaller, vocal doubles smear lead, low end shifts in
  mono.

### Over-Compressed Pumping

- Detection: sustained master or bus gain reduction above 2 dB, low-end-driven
  loudness dips, crest factor too flat for the genre target.
- Tools: reduce bus compression first; then `TDR Kotelnikov`, `Codex V20 Master
  Glue`, `FreeClip`, `ReaLimit` with lighter input.
- Start range: bus compression 0.5-2 dB GR; master clip/limit only catches
  peaks; if sustained >2 dB, return to source buses.
- Failure signs: vocal ducks on kicks, hats splash, 808 pulls mix down, loud
  copy is worse than safe copy at matched loudness.
