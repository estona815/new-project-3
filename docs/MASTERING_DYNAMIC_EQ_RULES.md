# Mastering Dynamic EQ Rules

Mastering dynamic EQ is frequency-specific dynamic control on the master bus. It is not random static EQ, not broadband compression, and not reference-curve chasing.

## DYNEQ-001: Subtle Master Control

- Use for intermittent harshness spikes, low-mid buildup, sibilance bursts, side fizz, bass resonance, or limiter-triggering sub energy.
- Do not rewrite the mix on the master bus.
- Risk: vocal pushed back, snare loses crack, cymbals dull, kick/bass weak, mix smaller.
- Metric guard: max reduction defaults to 2.5 dB or tighter by profile.
- Report: reason and why track/bus repair was not available.

## DYNEQ-002: Required Band Report

Every dynamic EQ band must define:

- frequency range
- Q or bandwidth
- detection range
- threshold behavior
- max gain reduction
- attack/release concept
- reason
- risk

Missing fields are WARN because the decision cannot be audited.

## DYNEQ-003: Safety Before Loudness

- Use dynamic EQ to reduce limiter-triggering energy only when it preserves musical punch.
- Do not trade punch for a louder integrated number.
- Risk: loud but flat master.
- Metric guard: punch, transient, crest, and true peak checks.
- Report: limiter interaction and bypass comparison when possible.

## DYNEQ-004: Failure Conditions

Reject or downgrade the candidate when dynamic EQ causes:

- vocal pushed back
- snare crack loss
- dull cymbals
- weak kick/bass
- smaller stereo image
- harder limiter movement
- side image collapse

The final report must list the failure, exact next patch, rerun command, and whether human listening is required.
