# Logic Reference Application

This document describes how arbitrary reference requests should become manual Logic Pro actions. References are high-level production targets only. They must not become exact copies of protected songs, drum patterns, basslines, samples, lyrics, melodies, sound recordings, or a living artist's vocal identity.

If the user says `따와라`, treat it safely. A licensed or owned user-provided sample/stem may be used. Otherwise, translate the request into high-level production traits such as kick punch, bass/808 tone, glide, saturation, transient sharpness, width, and arrangement energy.

## Korean Natural-Language Request Translation

- Preserve the raw user request.
- Show parsed targets, reference confidence, copying policy, automatic scope, manual Logic/stem requirements, and what will not be copied.
- Treat Korean/English mixed text as production direction, not authorization to copy.

## Kick/Bass `따와라` Request

- Do not extract or copy the sample unless the user provides an owned/cleared local sample or stem.
- If stems/MIDI/sample are provided and owned:
  - layer or replace kick/bass carefully
  - preserve phase alignment
  - tune 808 to song key
  - check mono compatibility
- If no owned source:
  - design from scratch based on high-level traits
  - match punch, sub weight, transient, saturation, envelope, and groove density
  - avoid exact pattern/bassline copying

## 2hollis / ycs / SYSTEM SEOUL Style Cluster

- Translate to bright digital hooks, internet/digicore/hyperpop energy, strong controlled 808, sharp but controlled drums, vocal-forward placement if applicable, synth width/movement, hook-forward arrangement, reduced random AI glitch, and no cheap rage clipping.
- No exact artist/song copying.

## Stereo-Only Source Limitation

- If current input is a single stereo WAV, there is no true kick/bass replacement unless stems/manual layering are added.
- No real stem-level drum rewrite.
- No guaranteed vocal removal.
- Broad EQ, saturation, width, trim, fade, gain staging, and mastering polish only.
- QC must mark manual Logic edit needed if the requested target requires stem-level changes.

## Reference Application in Logic Pro

### A. Drums Like Reference

If the request targets drums:

- If stems, MIDI, or a drum track exists:
  - adjust kick sample character
  - adjust snare/clap layer
  - adjust hat density
  - adjust swing
  - add controlled fills
  - avoid copying exact pattern
  - avoid copying an exact protected kick sample unless the user supplied a licensed/owned source
- If only stereo beat exists:
  - use broad transient shaping, EQ, and arrangement cuts only
  - recommend manual drum layering if needed
  - mark stem-level drum rewrite as unavailable

### B. Bass / 808 Like Reference

If the request targets bass or 808:

- Keep sub below roughly 120Hz mono/centered.
- Use saturation for audibility instead of excessive sub gain.
- Use sidechain or automation so melody/vocal remains audible.
- If glide or melodic movement is requested, note that exact bassline rewriting requires MIDI/stems/manual Logic.
- Do not copy an exact protected bassline or bass recording unless the user supplied a licensed/owned source.
- If only stereo source exists, broad low-end EQ/saturation is possible, not true bassline replacement.

### C. Synth Panning / Spatial Width

If the request says `베이스처럼 신디를 패닝`, `신디를 좌우로 벌려`, or `공간감 줘`:

- Do not widen sub frequencies.
- Widen only synth layers, pads, upper harmonics, or high-passed duplicate layers.
- Suggested Logic workflow:
  1. duplicate synth layer if stems exist
  2. high-pass duplicate layer around 120-180Hz
  3. pan or use Direction Mixer/Stereo Spread carefully
  4. automate pan movement subtly
  5. keep main melody or vocal center
  6. check mono compatibility
- If only stereo file exists:
  - use conservative mid/side EQ or stereo width
  - warn about phase/mono risk

### D. Vocal Like Artist

If the user says `내 목소리를 [artist]처럼`:

- Do not clone the artist's voice.
- Translate to vocal production traits only:
  - forwardness
  - brightness
  - compression
  - tuning amount
  - saturation/distortion
  - reverb/delay
  - adlib width
- Keep the user's own vocal identity.
- If reference audio is provided, use it for broad tonal and spatial targets, not exact imitation.

### E. Master / Final Loudness

- Do not over-limit just to match reference loudness.
- Maintain requested master mode: master-ready headroom / streaming-safe / loud demo.
- QC must block PASS if clipping or wrong export format occurs.
