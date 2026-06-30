# Harmonic Preserve Deferred Notes

Prompt 15 keeps harmonic preservation conservative.

## Active Behavior

- JSFX has an internal `harmonic_preserve = 0.75`.
- The active path uses it as a broad source-preserve proxy in high-band and M/S protection factors.
- The Python model contract now includes `is_near_harmonic()` and `apply_harmonic_preserve_to_suppression_limit()` for a future path that has a valid F0 estimate.

## Deferred Behavior

Full F0 harmonic tracking is deferred. In short, full F0 harmonic tracking is deferred until a stable, low-cost pitch estimate exists.

Reasons:

- The active JSFX path has no pitch or F0 estimator.
- Adding pitch tracking inside `@sample` would risk CPU cost and real-time instability.
- No STFT magnitude history or peak-tracking buffer exists in the active runtime path.
- False pitch estimates could protect the wrong bins or create unstable behavior.

## Data Needed

- A stable F0 estimate per frame or per block.
- Confidence value for the F0 estimate.
- Explicit sample-rate and Nyquist handling.
- Preallocated spectral peak or magnitude history if STFT is added later.

## Recommended Future Path

1. Keep full F0 detection outside the audio hot path or preallocate all required state.
2. Reject invalid F0 values below `50 Hz` or above `1000 Hz`.
3. Apply harmonic preserve only by reducing suppression limits near harmonics.
4. Never boost harmonic bins.
5. Dry-fallback or ignore the harmonic guard when F0 confidence is low.

No heavy pitch tracking was added in Prompt 15; no heavy pitch tracking should be added until the state and CPU budget are explicit.
