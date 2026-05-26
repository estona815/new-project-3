# Edit Plan

This document is a production guide generated from the analysis pass, creative brief, and reference target profile. It does not claim that a humanized mix, Logic edit, stem remix, or final export has already been achieved.

Reference-inspired targets, when present, describe high-level production direction only. They do not authorize exact copying of protected melodies, samples, lyrics, or recordings.

Korean `따와라` requests require a licensed/owned user-provided sample or stem. Without that source, translate the request into production traits such as kick punch, bass tone, 808 glide, saturation, width, transient sharpness, and arrangement energy.

Text-only reference prompts are lower-confidence direction. Accurate tone matching requires reference audio, stems, MIDI, or manual Logic production choices.

Logic Pro instructions in this document are manual engineering checklists. AppleScript automation cannot fully mix vocals, choose plugin settings, tune a performance, or replace a listening pass.

Plugin-specific vocal requests are plugin-aware but claim-safe: if Soundtoys Decapitator is not detected or not inserted by verified automation, write a manual Logic instruction and label any fallback as generic saturation approximation.

## Korean Natural-Language Request Translation

The generated plan must preserve the raw Korean request, parsed targets, reference confidence, copying policy, automatic scope, manual Logic/stem requirements, and a clear list of what will not be copied.

## Kick/Bass `따와라` Request

- Do not extract or copy a kick/bass sample unless the user provides an owned/cleared local sample or stem.
- If stems, MIDI, or an owned/cleared sample are provided, layer or replace carefully, preserve phase alignment, tune 808 to the song key, and check mono compatibility.
- If no owned source is provided, design from scratch from high-level traits: punch, sub weight, transient, saturation, envelope, and groove density.
- Avoid exact pattern or bassline copying.

## Decapitator / AutoTune Vocal Request

- Plan pitch correction as subtle, medium, or hard_effect.
- Use Soundtoys Decapitator only if installed and manually/verified applied; otherwise use generic saturation.
- Recommended insert order: cleanup EQ, pitch correction, compression, saturation/Decapitator, de-esser after saturation if needed, tone EQ, reverb/delay sends.
- If Logic automation cannot insert plugins, mark `manual_required`.
- Do not claim plugin application unless verified.

## 2hollis / ycs / SYSTEM SEOUL Style Cluster

- Translate to bright digital hooks, internet/digicore/hyperpop energy, strong controlled 808, sharp but controlled drums, vocal-forward placement if applicable, synth width/movement, hook-forward arrangement, reduced random AI glitch, and no cheap rage clipping.
- Do not copy exact artists, songs, vocals, melodies, samples, patterns, or recordings.

## Synth Width / Panning

- Keep sub/kick/808 fundamental mono and centered.
- Widen upper synth layers only.
- High-pass widened duplicate around 120-180Hz.
- Pan/auto-pan only high-passed layers.
- Check mono compatibility.
- If only stereo source exists, use conservative mid/side treatment and warn about limits.

## Stereo-Only Source Limitation

- A single stereo WAV cannot provide true kick/bass replacement, real stem-level drum rewrite, or guaranteed vocal removal.
- Broad EQ, saturation, width, trim, fade, gain staging, and mastering polish are possible.
- QC must mark manual Logic edit needed when the requested target requires stem-level changes.

## Reference Application in Logic Pro

Use the generated request-specific reference section as a manual Logic checklist. References must be translated into high-level production traits only; do not copy exact songs, drum patterns, basslines, samples, lyrics, melodies, or sound recordings.

### A. Drums Like Reference

If the request targets drums:

- If stems, MIDI, or a drum track exists, adjust kick sample character, snare/clap layer, hat density, swing, and controlled fills.
- Avoid copying the exact pattern.
- If only a stereo beat exists, use broad transient shaping, EQ, and arrangement cuts only.
- Recommend manual drum layering if needed.
- Mark stem-level drum rewrite as unavailable from stereo-only material.

### B. Bass / 808 Like Reference

If the request targets bass or 808:

- Keep sub below roughly 120Hz mono/centered.
- Use saturation for audibility instead of excessive sub gain.
- Use sidechain or automation so melody/vocal remains audible.
- If glide or melodic movement is requested, note that exact bassline rewriting requires MIDI, stems, or manual Logic.
- If only stereo source exists, broad low-end EQ/saturation is possible, not true bassline replacement.

### C. Synth Panning / Spatial Width

For requests like `베이스처럼 신디를 패닝`, `신디를 좌우로 벌려`, or `공간감 줘`:

- Do not widen sub frequencies.
- Widen only synth layers, pads, upper harmonics, or high-passed duplicate layers.
- Suggested Logic workflow: duplicate synth layer if stems exist, high-pass duplicate layer around 120-180Hz, pan or use Direction Mixer/Stereo Spread carefully, automate subtly, keep main melody or vocal center, and check mono compatibility.
- If only a stereo file exists, use conservative mid/side EQ or stereo width and warn about phase/mono risk.

### D. Vocal Like Artist

If the user says `내 목소리를 [artist]처럼`:

- Do not clone the artist's voice.
- Translate to vocal production traits only: forwardness, brightness, compression, tuning amount, saturation/distortion, reverb/delay, and adlib width.
- Keep the user's own vocal identity.
- If reference audio is provided, use it for broad tonal and spatial targets, not exact imitation.
- For Decapitator requests, insert Soundtoys Decapitator on the vocal bus only if installed and manually/verified applied; otherwise use generic saturation approximation language.
- Put tuning before saturation in most cases, and de-ess again if brightness or saturation raises sibilance.

### E. Master / Final Loudness

- Do not over-limit just to match reference loudness.
- Maintain requested master mode: master-ready headroom, streaming-safe, or loud demo.
- QC must block PASS if clipping or wrong export format occurs.

{{ body }}
