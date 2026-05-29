# Reference Matching Limits

Reference matching is advisory. A reference can suggest tonal direction, loudness context, stereo width, punch, and air balance. It cannot decide final quality by itself.

## REF-001: Advisory Only

- Use reference analysis to guide conservative tonal direction.
- Do not force the target to match a reference curve.
- Risk: clipping, pumping, phase damage, dull vocal, weak punch, or genre mismatch.
- Metric guard: clipping, true peak, transient, punch, vocal presence, and side/mid safety override reference matching.
- Report: reference file, confidence, accepted moves, rejected moves, and reason.

## REF-002: Band Comparison

Compare by:

- sub
- bass punch
- low-mid mud
- presence
- harshness
- sibilance
- air/fizz
- side/mid
- loudness
- transient profile

Do not treat broad spectral similarity as proof of a better master.

## REF-003: When Not To Match

Do not match when:

- arrangement differs
- genre differs
- vocal, guitar, synth, or drum density differs
- the reference is louder but less dynamic
- matching would cause clipping or over-limiting
- source limitations make the target impossible

The checker must FAIL any report where reference matching overrides true-peak or clipping safety.

## REF-004: No Valid Reference

- Use a genre profile when no valid reference exists.
- Do not invent a reference.
- Report `no valid reference` and the chosen profile.
