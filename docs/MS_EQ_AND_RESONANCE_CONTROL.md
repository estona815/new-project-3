# M/S EQ And Resonance Control

## M/S EQ Definition

Mid is center information: vocal, kick, snare, bass, and lead elements often live here. Side is difference information: width, cymbals, reverb, stereo synths, room tone, stereo noise, and AI side wash often live here. M/S EQ is not a generic widener.

## M/S Rules

### MS-001: Use Only For A Named Reason

- Use when reducing side wash, stabilizing low-end mono compatibility, controlling stereo harshness, protecting vocal center, cleaning reverb/cymbal/synth sides, or stabilizing master width.
- Do not use because a preset includes it.
- Risk: center vocal can hollow out, width can collapse, or side noise can become unstable.
- Metric guard: side/mid ratio WARN at 1.5 dB change, FAIL at 3.0 dB or audible collapse.
- Report: band, Mid or Side, static/dynamic, reduction amount, reason, risk, before/after side/mid metric.

### MS-002: Low-End Side Control

- Use below 80-150 Hz when side energy threatens mono compatibility or limiter stability.
- Do not remove intentional safe stereo low-end.
- Risk: bass loses size or musical intent.
- Metric guard: punch proxy and side/mid change must remain within profile threshold.
- Report: cutoff/band, reduction, whether bass punch was preserved.

### MS-003: Vocal Center Protection

- Use Mid cuts from 1-4 kHz only when vocal or lead harshness is proven.
- Do not scoop Mid presence to make a graph smoother.
- Risk: vocal disappears, snare loses crack, lead becomes distant.
- Metric guard: vocal presence band must not drop without a clear harshness benefit.
- Report: vocal/lead risk note and before/after presence metric.

### MS-004: Side Harshness

- Use side-only dynamic reduction when 5-16 kHz side energy is painful, fizzy, or unstable.
- Do not dull the whole stereo signal to fix side-only artifacts.
- Risk: cymbal sheen and synth width can vanish.
- Metric guard: air/fizz loss and side/mid ratio must pass.
- Report: band, dynamic behavior, max reduction, artifact target.

## Resonance Rules

Resonance is narrow or semi-narrow ringing, whistling, boxiness, metallic tone, nasal buildup, harsh spikes, or unstable AI bands. Broad EQ is tonal correction, not resonance control.

### RES-001: Detect Before Broad EQ

- Use spectral peak detection, band comparison, high-Q sweep approximation, reference comparison as secondary evidence, or human listening notes.
- Do not call a wide shelf or broad cut "resonance control."
- Risk: broad cuts remove body, punch, air, or vocal clarity.
- Metric guard: presence, punch, brightness, and transient checks.
- Report: detected frequency area, evidence, and chosen treatment.

### RES-002: Narrow Ringing

- Use high-Q notch or dynamic notch first.
- Do not stack deep cuts without evidence.
- Risk: phasey tone, hollow vocal, weak snare.
- Metric guard: max reduction must be limited and candidate must pass tonal/punch checks.
- Report: frequency, Q estimate, static/dynamic mode, max dB reduction.

### RES-003: AI Harsh Bands

- Use limited dynamic EQ or dynamic notch for unstable 3-8 kHz shards and 8-14 kHz splatter.
- Do not flatten the top end.
- Risk: dullness, lisping, or loss of excitement.
- Metric guard: harshness should improve while air/fizz, vocal presence, and transient proxy stay safe.
- Report: trigger band, threshold concept, attack/release concept, max reduction.
