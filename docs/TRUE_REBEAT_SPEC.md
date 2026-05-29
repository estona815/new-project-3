# True Rebeat Spec

This spec prevents false rebeat claims in REAPER automation. A filename, preset name, report title, or louder render never proves a rebeat. Only auditable musical elements in the REAPER project and matching bus renders can support the claim.

## Classifications

- `master_only`: master bus processing only. No reconstruction claim.
- `fullmix_rescue`: the original stereo fullmix is still the main source. EQ, M/S repair, DeAI, dynamics, resonance control, and mastering are allowed.
- `drum_reinforcement`: kick, snare, hat, or percussion support is added to the fullmix. The original beat is still primary.
- `stem_assisted_rebuild`: existing stems are imported, routed, and actively mixed. Source-separated stems must be labeled machine-separated.
- `partial_rebeat`: one or more roles are reconstructed, but drums, bass, and core music are not all independently evidenced.
- `true_rebeat`: drums, bass, and core music are recreated as MIDI or separate audio items on the timeline, and the song can be audited without relying primarily on the original fullmix.

## Required Evidence For `true_rebeat`

All requirements must pass:

- BPM/grid report with PASS confidence, or WARN confidence with a documented musical justification.
- Drum MIDI/audio reconstruction evidence.
- Bass MIDI/audio reconstruction evidence.
- Music/chord/lead MIDI/audio support or original stem evidence replacing that role.
- RPP audit confirming track names, items, media sources, and role-specific reconstruction.
- Separate bus renders for drums, bass, music/support, mix, and master.
- Before/after QC with no FAIL or BLOCKER.
- Final report that lists what was rebuilt, what was not rebuilt, and what still requires listening.

If any true-rebeat requirement is missing, downgrade to `partial_rebeat`, `drum_reinforcement`, `stem_assisted_rebuild`, `fullmix_rescue`, or `master_only`.

## Source Limits

If the only source is a stereo MP3 or stereo WAV, the default classification is `fullmix_rescue` or `drum_reinforcement`. `partial_rebeat` is allowed only after new MIDI/audio items are actually created. `true_rebeat` is forbidden unless enough independent drums, bass, and music are reconstructed and rendered.

## Report Language

Allowed when evidence exists:

- `fullmix rescue`
- `drum reinforcement`
- `kick/snare support layer`
- `partial drum MIDI reconstruction`
- `bass support reconstruction`
- `fullmix-derived vocal-focused processing`
- `stem-assisted rebuild`
- `partial_rebeat`
- `true_rebeat`

Forbidden without strict evidence:

- `비트 다 새로 찍음`
- `true rebeat`
- `full MIDI reconstruction`
- `stem rebuild`
- `remade instrumental`
- `새 beat print`
- `vocal tuned`
- `lossless restoration`
- `professional final master`

Korean reporting must stay precise. Use: `이번 작업은 true rebeat가 아니라 fullmix rescue + drum reinforcement입니다.` Do not use: `비트 다 새로 찍었습니다` unless this spec passes.
