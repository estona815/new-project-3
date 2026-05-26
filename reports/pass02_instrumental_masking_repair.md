# Pass 02 Instrumental Masking Repair

- Music stems and MUSIC_BUS were lowered to create a 1-5 kHz vocal pocket.
- Bass/808 was lowered and dynamically controlled around 120-300 Hz.
- Drums/percussion were kept punchy but trimmed, with an 8.5 kHz dynamic control band for brittle hats.
- 03_FX and 08_Guitar remain muted in artifact quarantine.
- FX_BUS remains quiet; no random glitch/noise layer was reintroduced.

## Key Levels
- DRUM_BUS: {'index': 1, 'volume_db': -1.4, 'pan': 0.0, 'mute': False}
- BASS_808_BUS: {'index': 2, 'volume_db': -2.0, 'pan': 0.0, 'mute': False}
- MUSIC_BUS: {'index': 3, 'volume_db': 0.0, 'pan': 0.0, 'mute': False}
- FX_BUS: {'index': 7, 'volume_db': -8.0, 'pan': 0.0, 'mute': False}
