# Vocal Cleanup Rules

These are initial original rules for Suno vocal cleanup. They are not copied from external sources.

## Rules

- Do not over-denoise. Noise reduction is a candidate step, not a default victory condition.
- Prefer dynamic EQ if AI denoise damages the vocal body, consonants, breath shape, or emotional contour.
- Control 6-10 kHz sibilance with de-essing or dynamic EQ before assuming the whole vocal needs broad high-frequency reduction.
- Control 12-16 kHz AI fizz with narrow dynamic EQ or gentle high-shelf restraint when it is audible in context.
- Restore body after denoise with light saturation, gentle compression, or a parallel original blend.
- Reject watery or metallic vocal candidates even if the noise floor is lower.
- Reject candidates that damage consonants, smear syllable starts, or make words less intelligible.
- Always compare original, cleaned vocal, and full mix before selecting a candidate.

## REAPER Translation

- Build A/B/C cleanup candidates with conservative settings.
- Keep the original track muted but available for instant comparison.
- Print candidate renders only after bypass comparison.
- Report denoise amount, de-ess action, body restoration method, and rejection notes.
