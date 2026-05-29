# De-Esser And Vocal Repair Rules

## De-Essing

De-essing is dynamic attenuation of sibilant consonants and harsh vocal events. It is not the same as cutting all treble.

### DEESS-001: Only When Justified

- Use when sibilance proxy or listening notes show excessive `s`, `sh`, `ch`, `t`, spit, or splatter.
- Do not insert a de-esser by habit.
- Risk: lisped vocal, dull cymbals, muffled mix.
- Metric guard: sibilance improves while air/fizz, vocal presence, and transient proxy stay within threshold.
- Report: evidence that de-essing was needed.

### DEESS-002: Prefer Isolated Vocal

- Use vocal-track de-essing when a vocal stem exists.
- Do not fullmix de-ess when isolated vocal repair is available.
- Risk: fullmix de-essing can dull drums, synths, and air.
- Metric guard: brightness loss must stay within profile guard.
- Report: target source and whether it was isolated or fullmix-derived.

### DEESS-003: Fullmix De-Essing Is Risky

- Use only light, narrow, dynamic processing when no isolated vocal exists.
- Do not claim vocal-only repair from fullmix processing.
- Risk: cymbals and stereo brightness get pulled down with the vocal.
- Metric guard: fullmix de-esser max reduction defaults to 2.0 dB or tighter by profile.
- Report: fullmix risk note, max reduction, and human listening requirement.

## Vocal Repair

Vocal repair includes noise guard, resonance control, de-essing, level stabilization, presence repair, and limited artifact reduction. Pitch correction is separate and requires evidence.

### Vocal Repair Requirements

- Use when the vocal source or fullmix vocal band is identified.
- Do not claim `vocal fully tuned` unless pitch contour, correction settings, edit/take evidence, and validation exist.
- Risk: repair can reduce intelligibility or emotional articulation while improving noise metrics.
- Metric guard: vocal presence and sibilance must improve or remain musically safe; brightness and transient loss must not exceed profile limits.
- Report: source type, processing chain, pitch/timing status, what remains for listening.

## Sibilance Bands

- Male vocal sibilance often lives around 4.5-8 kHz.
- Female or bright vocal sibilance often lives around 6-10 kHz.
- Harsh consonants can extend into 3-5 kHz.
- AI splatter can extend into 8-14 kHz.

These are starting ranges, not permission for broad treble cuts.
