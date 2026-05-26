
# Lead Vocal Chain

Processing order:

1. Clip gain / clean gain staging.
2. Cleanup EQ, high-pass around 70-100 Hz.
3. Pitch correction using `Auto-Tune Pro` if it loads; otherwise ReaTune fallback.
4. Dynamic EQ using `TDR Nova` or fallback to ReaXcomp/ReaEQ automation.
5. De-esser using `TDR Nova` or fallback dynamic band around 5.5-9 kHz.
6. Gentle serial compression: clean compressor then character compressor if verified.
7. Tone EQ and only light saturation if the stem stays clean.
8. Send-based reverb/delay only.

Targets:

- Centered, dominant male lead.
- Mud control around 180-350 Hz, box control around 350-600 Hz, nasal/harsh control around 700 Hz-5 kHz as needed.
- Air around 10-14 kHz only if the stem is not noisy.
- No heavy compression that crushes consonants or exposes AI texture.
