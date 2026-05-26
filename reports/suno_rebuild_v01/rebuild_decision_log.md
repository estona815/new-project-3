# Rebuild Decision Log

## Production Choices

- Rebuilt the track as a new 162 BPM, B minor, 96-bar DAW-style instrumental trimmed to the Suno reference length.
- Programmed new kick, snare/clap, hi-hat, open hat, perc, and transition fills with deterministic humanized timing and velocity.
- Wrote a new tuned 808 line around Bm-G-D-A with controlled saturation, mono low end, and kick ducking.
- Wrote new piano/bell/pluck/pad melody parts that preserve sad melody-forward energy without copying the guide MIDI notes.
- Added only non-vocal FX: risers, impacts, filtered noise sweeps, and night-city transitions.
- Avoided Antares products and third-party dependency assumptions; processing is generated locally with Python DSP and REAPER stock/JS placeholders where available.

## Intentional Changes From Suno

- Removed AI vocal texture dependence and did not use vocal chops.
- Replaced the guide drums with less robotic microtiming and more section-aware density.
- Simplified the low-mid arrangement so the beat stays vocal-ready.
- Kept melody forward but gave it cleaner transient shape and less AI-like top-band hash.

## Outputs

- `full_mix`: `/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01/rebuilt_full_mix.wav`
- `mp3`: `/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01/rebuilt_full_mix_320.mp3`
- `drums`: `/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01/drums_stem.wav`
- `bass`: `/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01/bass_808_stem.wav`
- `melody`: `/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01/melody_stem.wav`
- `fx`: `/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01/fx_stem.wav`
- `reaper_sum`: `/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01/rebuilt_full_mix_reaper_sum.wav`
- `rpp`: `/Users/hantaeheuk/Documents/New project 3/reaper/suno_rebuild_v01/reaper_project.rpp`
- `midi_drums`: `/Users/hantaeheuk/Documents/New project 3/reaper/suno_rebuild_v01/midi/rebuilt_drums.mid`
- `midi_bass`: `/Users/hantaeheuk/Documents/New project 3/reaper/suno_rebuild_v01/midi/rebuilt_bass_808.mid`
- `midi_melody`: `/Users/hantaeheuk/Documents/New project 3/reaper/suno_rebuild_v01/midi/rebuilt_melody.mid`
- `midi_fx`: `/Users/hantaeheuk/Documents/New project 3/reaper/suno_rebuild_v01/midi/rebuilt_fx.mid`

- REAPER build status: `reaper_cli_return_0`
- REAPER render sanity status: `reaper_render_return_0`
