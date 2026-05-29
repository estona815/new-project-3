# Drum Reinforcement Rules

Drum reinforcement adds support to an existing beat. It is not true rebeat.

## Allowed Uses

- Subtle kick reinforcement to restore punch.
- Snare/clap support to improve backbeat definition.
- Hat/percussion support only when event confidence is high.
- Parallel drum support with explicit phase, flam, transient, and harshness checks.

## Candidate Types

- `A_no_reinforcement_mix_rescue`: baseline fullmix rescue/master processing.
- `B_kick_snare_subtle_support`: conservative kick/snare reinforcement.
- `C_drum_support_punch`: stronger support with phase and headroom checks.
- `D_hat_perc_detail`: high-confidence hat/percussion detail only.
- `E_rebeat_test`: experimental, allowed only when enough MIDI/audio reconstruction exists.

## Phase, Flam, And Groove Safety

Reject or downgrade a candidate when:

- flam risk is high
- low end gets weaker after kick support
- punch does not improve
- hats become splashy or harsh
- clipping or true-peak failure occurs
- stereo image collapses
- duration mismatches source
- MIDI evidence is missing for the claimed reconstruction

Flam risk must check timing deviations between detected source transients and reinforcement events. If reinforcement consistently lands early or late, mark WARN. If a double-hit proxy is high, reject the candidate.

## Report Requirements

Every reinforcement candidate must report:

- kick, snare, hat, and percussion event counts
- MIDI item count
- audio support item count
- render file path
- transient/punch/harshness/side-mid/peak changes
- flam risk
- classification
- whether human listening is required

If the fullmix remains primary, report `drum_reinforcement`, not `true_rebeat`.
