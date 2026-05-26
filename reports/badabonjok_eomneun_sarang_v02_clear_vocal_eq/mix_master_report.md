# badabonjok_eomneun_sarang_v02_clear_vocal_eq Revision Notes

## Status
- Source: user-provided Suno stems from `badabonjok_eomneun_sarang_v01_anime_rock`.
- Revision goal: reduce vocal noise, make the vocal clearer, and rebalance full master EQ.
- Male lead remains the main vocal.
- Suno female candidate was included only in the separate experiment render because it is an MP3 full mix, not an isolated stem.

## Outputs
- Clear vocal master: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v02_clear_vocal_eq/badabonjok_eomneun_sarang_v02_clear_vocal_eq_MASTER_clear_vocal_48k16.wav`
- Female layer experiment: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v02_clear_vocal_eq/badabonjok_eomneun_sarang_v02_clear_vocal_eq_MASTER_female_layer_experiment_48k16.wav`
- Premaster: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v02_clear_vocal_eq/badabonjok_eomneun_sarang_v02_clear_vocal_eq_premaster_48k16.wav`
- Clean vocal reference: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v02_clear_vocal_eq/badabonjok_eomneun_sarang_v02_clear_vocal_eq_vocal_clean_reference_48k16.wav`
- REAPER project: `/Users/hantaeheuk/Documents/New project 3/reaper/badabonjok_eomneun_sarang_v02_clear_vocal_eq/badabonjok_eomneun_sarang_v02_clear_vocal_eq.rpp`
- REAPER print check: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v02_clear_vocal_eq/badabonjok_eomneun_sarang_v02_clear_vocal_eq_reaper_print.wav`

## Mix Moves
- Added envelope-based cleanup to lead/backing vocals to lower quiet hiss and tail noise.
- Re-EQed lead vocal with less mud, less harsh upper glare, and more 1.7 kHz / 4.8 kHz intelligibility.
- Tucked backing vocal and widened it slightly so it supports instead of clouding the lead.
- Reduced instrumental masking around the vocal presence band, especially synth/other bed and drum bite.
- Master EQ is brighter in the vocal presence range but rolled off above the harsh air band.
- Female layer experiment uses the Suno MP3 candidate as a very low, center-focused texture only.

## QC
```json
{
  "slug": "badabonjok_eomneun_sarang_v02_clear_vocal_eq",
  "source_slug": "badabonjok_eomneun_sarang_v01_anime_rock",
  "sample_rate": 48000,
  "duration_seconds": 76.04,
  "clear_master_metrics": {
    "peak_dbfs": -1.0,
    "rms_dbfs": -8.48,
    "rough_integrated_lufs": -9.21,
    "stereo_correlation": 0.986
  },
  "female_layer_experiment_metrics": {
    "peak_dbfs": -1.0,
    "rms_dbfs": -8.44,
    "rough_integrated_lufs": -9.16,
    "stereo_correlation": 0.986
  },
  "premaster_metrics": {
    "peak_dbfs": -8.81,
    "rms_dbfs": -18.22,
    "rough_integrated_lufs": -18.94,
    "stereo_correlation": 0.986
  },
  "female_candidate_used": "/Users/hantaeheuk/Documents/New project 3/audio_work/badabonjok_eomneun_sarang_v01_anime_rock/suno_generated_candidates/suno_anime_rock_female_candidate_7016b495.wav",
  "female_candidate_note": "MP3-derived full mix, not isolated vocal stem; used only as a low tucked layer."
}
```
