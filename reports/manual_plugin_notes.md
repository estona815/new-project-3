# Manual Plugin Notes

REAPER Lua will attempt safe plugin insertion by name. If a premium plugin is not present or REAPER uses a different exact name, the project still opens with stock fallbacks/placeholders.
Detected means available-name hint only; it does not prove the plugin was inserted or used in a verified render.

| role | status | manual instruction |
| --- | --- | --- |
| pitch_correction | detected candidate | Attempt `Auto-Tune Pro` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaTune` and follow the role-specific settings in the mix reports. |
| surgical_eq | detected candidate | Attempt `TDR Nova` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaEQ` and follow the role-specific settings in the mix reports. |
| dynamic_eq | detected candidate | Attempt `TDR Nova` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaXcomp` and follow the role-specific settings in the mix reports. |
| deesser | detected candidate | Attempt `TDR Nova` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaXcomp` and follow the role-specific settings in the mix reports. |
| compressor_clean | fallback | Attempt `ReaComp` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaComp` and follow the role-specific settings in the mix reports. |
| compressor_character | detected candidate | Attempt `uaudio_teletronix_la-2a_tc` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaComp` and follow the role-specific settings in the mix reports. |
| saturation | detected candidate | Attempt `Decapitator` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `JS: Saturation` and follow the role-specific settings in the mix reports. |
| multiband_compressor | fallback | Attempt `ReaXcomp` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaXcomp` and follow the role-specific settings in the mix reports. |
| stereo_imager | detected candidate | Attempt `Ozone Imager 2` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `JS: Stereo Width` and follow the role-specific settings in the mix reports. |
| mid_side_eq | detected candidate | Attempt `TDR Nova` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaEQ` and follow the role-specific settings in the mix reports. |
| reverb_plate | fallback | Attempt `ReaVerbate` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaVerbate` and follow the role-specific settings in the mix reports. |
| reverb_room | fallback | Attempt `ReaVerbate` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaVerbate` and follow the role-specific settings in the mix reports. |
| delay | fallback | Attempt `ReaDelay` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaDelay` and follow the role-specific settings in the mix reports. |
| limiter | fallback | Attempt `ReaLimit` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaLimit` and follow the role-specific settings in the mix reports. |
| loudness_meter | fallback | REAPER may not insert an ffmpeg meter as an FX. Use a JS loudness meter if present, or run ffmpeg ebur128 after rendering and document the measured LUFS/true-peak result. |
| noise_reduction | fallback | Attempt `ReaFIR` in REAPER. If the inserted FX is missing or appears as a placeholder, insert `ReaFIR` and follow the role-specific settings in the mix reports. |
