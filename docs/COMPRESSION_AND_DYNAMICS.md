# Compression And Dynamics Rules

Compression must solve a defined problem. It is not a mandatory insert.

## COMP-001: Defined Purpose

- Use for unstable vocal level, weak drum punch, excessive dynamic spikes, mix glue, parallel energy, or master control.
- Do not compress only because a chain template has a compressor.
- Risk: raised noise floor, dulled transients, pumping, or smaller mix.
- Metric guard: transient proxy, punch proxy, harshness, and noise floor must remain safe.
- Report: target, purpose, ratio, attack, release, knee, gain reduction target, makeup gain, expected effect, failure mode.

## COMP-002: Attack Logic

- Fast attack controls peaks but can kill punch.
- Slow attack preserves transients but may miss peaks.
- Medium attack can glue but may smear.
- Do not use fast attack on kick/snare/bass-heavy buses without a punch reason.
- Metric guard: transient proxy WARN below profile threshold.
- Report: attack choice and source-specific reason.

## COMP-003: Release Logic

- Fast release can distort or pump.
- Slow release can flatten groove.
- Tempo-aware release is preferred when possible.
- Do not let release timing fight the song groove.
- Metric guard: pumping risk note plus transient and RMS/crest checks.
- Report: release intent and expected behavior.

## COMP-004: DnB And Bass-Heavy Material

- Preserve kick/snare transient and bass punch.
- Use parallel compression only if punch improves without harshness rising.
- Do not make loudness by limiter squeeze alone.
- Metric guard: DnB profile tightens transient and punch thresholds.
- Report: punch before/after and limiter gain strategy.

## COMP-005: Vocal Repair

- Use compression to stabilize vocal after noise, resonance, and sibilance are controlled.
- Do not compress first if it raises noise or sibilance.
- Risk: vocal becomes harsher even when level seems stable.
- Metric guard: noise floor and sibilance must not rise without targeted control.
- Report: chain order and noise/sibilance guard.

## COMP-006: Master Bus

- Use conservative compression, especially on already mastered MP3 sources.
- Do not exceed profile gain-reduction limits without WARN and human listening.
- Risk: reduced punch, smaller image, louder but worse print.
- Metric guard: master bus gain reduction defaults to 2.0 dB max, tighter in DnB/fullmix/MP3 profiles.
- Report: gain reduction target, ceiling, and bypass comparison when possible.
