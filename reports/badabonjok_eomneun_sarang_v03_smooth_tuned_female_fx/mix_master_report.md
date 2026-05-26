# badabonjok_eomneun_sarang_v03_smooth_tuned_female_fx Revision Notes

## Status
- Source: user-provided Suno stems from `badabonjok_eomneun_sarang_v01_anime_rock`.
- Revision goal: smoother vocal compression, less crackle, more audible female layer, vocal tune feel, delay/reverb, and balanced full master EQ.
- Male lead remains the main vocal.
- Suno female candidate was included only in the separate experiment render because it is an MP3 full mix, not an isolated stem.

## Outputs
- Clear vocal master: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v03_smooth_tuned_female_fx/badabonjok_eomneun_sarang_v03_smooth_tuned_female_fx_MASTER_clear_vocal_48k16.wav`
- Female layer mix: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v03_smooth_tuned_female_fx/badabonjok_eomneun_sarang_v03_smooth_tuned_female_fx_MASTER_female_layer_mix_48k16.wav`
- Premaster: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v03_smooth_tuned_female_fx/badabonjok_eomneun_sarang_v03_smooth_tuned_female_fx_premaster_48k16.wav`
- Clean vocal reference: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v03_smooth_tuned_female_fx/badabonjok_eomneun_sarang_v03_smooth_tuned_female_fx_vocal_clean_reference_48k16.wav`
- REAPER project: `/Users/hantaeheuk/Documents/New project 3/reaper/badabonjok_eomneun_sarang_v03_smooth_tuned_female_fx/badabonjok_eomneun_sarang_v03_smooth_tuned_female_fx.rpp`

## Mix Moves
- Added envelope-based cleanup to lead/backing vocals to lower quiet hiss and tail noise.
- Re-EQed lead vocal with less mud, less harsh upper glare, and smoother 1.7 kHz / 4.8 kHz intelligibility.
- Added a gentle tune-gloss double, tempo-style vocal delay, and short room reverb to the lead vocal.
- Reduced compressor ratio and master saturation so the vocal breaks up less than v02.
- Tucked backing vocal and widened it slightly so it supports instead of clouding the lead.
- Reduced instrumental masking around the vocal presence band, especially synth/other bed and drum bite.
- Master EQ is brighter in the vocal presence range but rolled off above the harsh air band.
- Female layer mix uses the Suno MP3 candidate as an audible center-focused texture while filtering out as much MP3/full-mix residue as possible.

## QC
```json
{
  "slug": "badabonjok_eomneun_sarang_v03_smooth_tuned_female_fx",
  "source_slug": "badabonjok_eomneun_sarang_v01_anime_rock",
  "sample_rate": 48000,
  "duration_seconds": 76.04,
  "clear_master_metrics": {
    "peak_dbfs": -1.0,
    "rms_dbfs": -9.98,
    "rough_integrated_lufs": -10.7,
    "stereo_correlation": 0.989
  },
  "female_layer_mix_metrics": {
    "peak_dbfs": -1.0,
    "rms_dbfs": -10.11,
    "rough_integrated_lufs": -10.83,
    "stereo_correlation": 0.989
  },
  "premaster_metrics": {
    "peak_dbfs": -8.72,
    "rms_dbfs": -19.06,
    "rough_integrated_lufs": -19.78,
    "stereo_correlation": 0.989
  },
  "female_candidate_used": "/Users/hantaeheuk/Documents/New project 3/audio_work/badabonjok_eomneun_sarang_v01_anime_rock/suno_generated_candidates/suno_anime_rock_female_candidate_7016b495.wav",
  "female_candidate_note": "MP3-derived full mix, not isolated vocal stem; used only as a low tucked layer."
}
```
