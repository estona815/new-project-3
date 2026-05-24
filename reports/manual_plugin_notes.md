# Manual Plugin Notes

REAPER Lua will attempt safe plugin insertion by name. If a premium plugin is not present or REAPER uses a different exact name, the project still opens with stock fallbacks/placeholders.

| role | manual instruction |
| --- | --- |
| pitch_correction | Use `Auto-Tune Pro` if it appears on the track. If missing, insert `ReaTune` and follow the role-specific settings in the mix reports. |
| surgical_eq | Use `TDR Nova` if it appears on the track. If missing, insert `ReaEQ` and follow the role-specific settings in the mix reports. |
| dynamic_eq | Use `TDR Nova` if it appears on the track. If missing, insert `ReaXcomp` and follow the role-specific settings in the mix reports. |
| deesser | Use `TDR Nova` if it appears on the track. If missing, insert `ReaXcomp` and follow the role-specific settings in the mix reports. |
| compressor_clean | Use `ReaComp` if it appears on the track. If missing, insert `ReaComp` and follow the role-specific settings in the mix reports. |
| compressor_character | Use `uaudio_teletronix_la-2a_tc` if it appears on the track. If missing, insert `ReaComp` and follow the role-specific settings in the mix reports. |
| saturation | Use `Decapitator` if it appears on the track. If missing, insert `JS: Saturation` and follow the role-specific settings in the mix reports. |
| multiband_compressor | Use `ReaXcomp` if it appears on the track. If missing, insert `ReaXcomp` and follow the role-specific settings in the mix reports. |
| stereo_imager | Use `Ozone Imager 2` if it appears on the track. If missing, insert `JS: Stereo Width` and follow the role-specific settings in the mix reports. |
| mid_side_eq | Use `TDR Nova` if it appears on the track. If missing, insert `ReaEQ` and follow the role-specific settings in the mix reports. |
| reverb_plate | Use `ReaVerbate` if it appears on the track. If missing, insert `ReaVerbate` and follow the role-specific settings in the mix reports. |
| reverb_room | Use `ReaVerbate` if it appears on the track. If missing, insert `ReaVerbate` and follow the role-specific settings in the mix reports. |
| delay | Use `ReaDelay` if it appears on the track. If missing, insert `ReaDelay` and follow the role-specific settings in the mix reports. |
| limiter | Use `ReaLimit` if it appears on the track. If missing, insert `ReaLimit` and follow the role-specific settings in the mix reports. |
| loudness_meter | Use `ffmpeg ebur128 / JS: Loudness Meter Peak/RMS/LUFS` if it appears on the track. If missing, insert `ffmpeg ebur128 / JS: Loudness Meter Peak/RMS/LUFS` and follow the role-specific settings in the mix reports. |
| noise_reduction | Use `ReaFIR` if it appears on the track. If missing, insert `ReaFIR` and follow the role-specific settings in the mix reports. |
