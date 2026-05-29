# Tempo Grid And MIDI Reconstruction

Tempo/grid analysis is the first gate for any beat correction, MIDI reconstruction, drum reinforcement, or rebeat claim. The system must report uncertainty instead of forcing one tempo.

## Tempo/Grid Report

`harness/tempo_grid_analyzer.py` must report:

- BPM candidates
- half-time and double-time alternatives
- selected BPM when confidence supports it
- downbeat confidence
- transient density
- section boundary hints
- tempo stability
- grid confidence
- onset timing distribution
- likely kick/snare positions
- whether quantization is safe

## Confidence Policy

- PASS: stable BPM, clear downbeats, and consistent transient grid.
- WARN: ambiguous half/double time, drift, dense noisy transients, or weak drum definition.
- FAIL: no usable tempo estimate or grid would create obvious misalignment.
- BLOCKER: source missing or unreadable.

Do not claim beat correction or rebeat if grid confidence is too low.

## MIDI Reconstruction Rules

Create MIDI only when evidence supports it:

- `DRUMS_MIDI_REBUILD`: kick, snare/clap, hat/percussion notes from detected events or MIDI/stem evidence.
- `BASS_MIDI_SUPPORT`: only from reliable pitch/bass evidence, existing MIDI, or stems.
- `MUSIC_MIDI_SUPPORT`: only from existing MIDI, stems, reliable transcription data, or manual notes in reports.
- `FX_MIDI_OR_AUDIO_SUPPORT`: transitions, risers, impacts, and chops when detected or available.

Every MIDI item must be placed on the REAPER timeline and be auditable in the `.RPP`.

## Drum Note Map

- Kick: 36
- Snare/clap: 38 or 40
- Closed hat: 42
- Open hat: 46
- Percussion: 39, 51, or profile-defined

Velocity should derive from transient strength, defaulting to 45-115. Avoid flat same-velocity note walls.

## Quantization

- Use grid quantization only when grid confidence is high.
- Use light quantization for groove preservation.
- Do not hard snap breakbeat/DnB material unless the profile explicitly requests it.
- Report average timing deviation and quantization strength.

DnB requires half/double-time awareness. Hyperpop and sample-based tracks require stricter transient filtering because dense high-frequency material can look like hats.
