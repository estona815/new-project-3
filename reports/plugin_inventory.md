# Plugin Inventory

- Harness version: fresh_mix_rebuild.v0.6
- Plugin map: `/Users/hantaeheuk/Documents/New project 3/config/plugin_map.yaml`
- Safe scan sources inspected: 110
- Available plugin name hints: 60
- Claim rule: detected plugins are hints only; rendered/plugin-applied claims require REAPER verification.

| role | selected | fallback? | detected preferred | fallback |
| --- | --- | --- | --- | --- |
| pitch_correction | Auto-Tune Pro | false | Auto-Tune Pro, Auto-Tune EFX+, Auburn Sounds Graillon 3 | ReaTune |
| surgical_eq | TDR Nova | false | TDR Nova | ReaEQ |
| dynamic_eq | TDR Nova | false | TDR Nova | ReaXcomp |
| deesser | TDR Nova | false | TDR Nova | ReaXcomp |
| compressor_clean | ReaComp | true | none | ReaComp |
| compressor_character | uaudio_teletronix_la-2a_tc | false | uaudio_teletronix_la-2a_tc, uaudio_ua_1176 | ReaComp |
| saturation | Decapitator | false | Decapitator, Fresh Air | JS: Saturation |
| multiband_compressor | ReaXcomp | true | none | ReaXcomp |
| stereo_imager | Ozone Imager 2 | false | Ozone Imager 2 | JS: Stereo Width |
| mid_side_eq | TDR Nova | false | TDR Nova | ReaEQ |
| reverb_plate | ReaVerbate | true | none | ReaVerbate |
| reverb_room | ReaVerbate | true | none | ReaVerbate |
| delay | ReaDelay | true | none | ReaDelay |
| limiter | ReaLimit | true | none | ReaLimit |
| loudness_meter | ffmpeg ebur128 / JS: Loudness Meter Peak/RMS/LUFS | true | none | ffmpeg ebur128 / JS: Loudness Meter Peak/RMS/LUFS |
| noise_reduction | ReaFIR | true | none | ReaFIR |
