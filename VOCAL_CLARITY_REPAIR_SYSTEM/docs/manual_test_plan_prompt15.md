# Manual Test Plan - Prompt 15 Source Preserve Guards

Use the Preserve default preset unless a step says otherwise. Do not use Strong Test mode for source-preservation validation.

## Clean Vocal

Expected:

- Processed vocal stays close to dry.
- Consonants do not move backward.
- Air and breath texture are not heavily reduced.
- Residual monitor should not contain obvious full consonants or vowel tone.

## Vocal With Hiss

Expected:

- Hiss can reduce moderately.
- Vocal presence should stay forward.
- Some hiss is acceptable if stronger removal would dull the source.

## AI Metallic Vocal

Expected:

- This patch is not the final surgical artifact remover.
- Metallic artifacts may remain.
- Protected presence and air bands should not collapse.

## Acoustic Guitar Picking

Expected:

- Pick attacks remain intact.
- No obvious transient smear.
- Residual should not sound like the main pick transient.

## Drum Loop

Expected:

- Snare and hat attacks remain sharp.
- No broad high-band pumping.

## Vocal With Reverb Tail

Expected:

- Room and reverb tail should not be abruptly chopped.
- Some artifact tail can remain if removal would damage ambience.

## Sine And Harmonic Stack

Render clean tones at `3 kHz`, `6 kHz`, and `12 kHz`, plus a simple harmonic stack.

Expected:

- No heavy default attenuation.
- No modulation or unstable flutter.
- No NaN, Inf, silence, or sudden click.

## Regression Checks

- Bypass returns dry.
- DryWet `0` returns dry.
- Amount `0` produces no attenuation.
- Processing disabled returns dry.
- Silence remains silence.
- Residual monitor is off for normal use.
