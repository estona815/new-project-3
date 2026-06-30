# Residual Monitor

Prompt 16 result: residual monitoring is defined as an evaluation tool, not a denoise feature.

## Plugin Mode

The active JSFX already exposes `Residual Monitor`:

- `Off`: normal processed output.
- `Processed`: processed wet path for debug listening.
- `Residual`: removed signal.

Default is `Off`, so normal plugin output is unchanged.

## Residual Definition

Plugin-side convention:

```text
residual = dryInput - processedBeforeDryWet
```

Harness convention:

```text
residual.wav = inputAligned - processedAligned
```

The current JSFX reports zero latency, so Prompt 16 applies no latency compensation. If a future processor adds latency, residual calculation must compensate before scoring.

## Good Residual

Good residual should mostly contain non-musical material:

- broadband hiss
- hum
- fan or computer noise
- room noise
- AI chirp
- metallic artifact
- codec birdie
- non-musical fuzz

## Bad Residual

Bad residual means the processor is removing source:

- clear vocal phrases
- S/T/CH consonants
- musical breath texture
- harmonic overtones
- guitar picking
- snare attacks
- cymbal musical detail
- piano or plucked attacks
- natural room or reverb tail

If residual sounds like a ghost vocal, processing is too aggressive.

## How To Use

1. Render original, processed, processed-matched, and residual files.
2. Listen to processed-matched against original for level-fair A/B.
3. Listen to residual loud enough to identify musical leakage.
4. Prefer leaving some noise over removing vocal clarity, air, transient attack, ambience, or harmonic texture.

Residual listening is not a replacement for full audio judgment. It is a guardrail that makes destructive cleanup harder to miss.
