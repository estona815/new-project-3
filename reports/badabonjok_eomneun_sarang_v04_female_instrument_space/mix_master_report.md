# badabonjok_eomneun_sarang_v04_female_instrument_space Revision Notes

## Status
- Source: user-provided Suno stems from `badabonjok_eomneun_sarang_v01_anime_rock`.
- Revision goal: place the female voice like an instrument with panned delay/reverb, tuck the lead vocal slightly into the track, add hard-tune feel, reduce hard-tune noise, and rebalance with dynamic-EQ-style deharshing.
- Male lead remains the main vocal.
- Suno female candidate is MP3-derived full mix material, not an isolated vocal stem, so it is filtered and used as a wide texture layer rather than a lead replacement.

## Outputs
- Clear vocal master: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v04_female_instrument_space/badabonjok_eomneun_sarang_v04_female_instrument_space_MASTER_clear_vocal_48k16.wav`
- Female layer mix: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v04_female_instrument_space/badabonjok_eomneun_sarang_v04_female_instrument_space_MASTER_female_layer_mix_48k16.wav`
- Premaster: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v04_female_instrument_space/badabonjok_eomneun_sarang_v04_female_instrument_space_premaster_48k16.wav`
- Clean vocal reference: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v04_female_instrument_space/badabonjok_eomneun_sarang_v04_female_instrument_space_vocal_clean_reference_48k16.wav`
- REAPER project: `/Users/hantaeheuk/Documents/New project 3/reaper/badabonjok_eomneun_sarang_v04_female_instrument_space/badabonjok_eomneun_sarang_v04_female_instrument_space.rpp`

## Mix Moves
- Lead vocal was tucked slightly lower and treated with hard-tune-style pitch doubling.
- Added dynamic-EQ-style deharshing around vocal presence/air bands to reduce brittle tune noise.
- Reduced compressor ratio and master saturation to avoid vocal break-up.
- Female layer was high-passed, deharshened, ducked against the lead, and widened with ping-pong delay plus plate-style reverb.
- Female layer is intentionally placed as a panned atmospheric instrument layer rather than a center lead vocal.
- Instrument beds were carved around the vocal bands so the vocal sits inside the track instead of poking out.

## QC
```json
{
  "slug": "badabonjok_eomneun_sarang_v04_female_instrument_space",
  "source_slug": "badabonjok_eomneun_sarang_v01_anime_rock",
  "sample_rate": 48000,
  "duration_seconds": 76.04,
  "clear_master_metrics": {
    "peak_dbfs": -1.0,
    "rms_dbfs": -10.35,
    "rough_integrated_lufs": -11.06,
    "stereo_correlation": 0.988
  },
  "female_layer_mix_metrics": {
    "peak_dbfs": -1.0,
    "rms_dbfs": -11.2,
    "rough_integrated_lufs": -11.93,
    "stereo_correlation": 0.984
  },
  "premaster_metrics": {
    "peak_dbfs": -9.11,
    "rms_dbfs": -19.46,
    "rough_integrated_lufs": -20.17,
    "stereo_correlation": 0.988
  },
  "female_candidate_used": "/Users/hantaeheuk/Documents/New project 3/audio_work/badabonjok_eomneun_sarang_v01_anime_rock/suno_generated_candidates/suno_anime_rock_female_candidate_7016b495.wav",
  "female_candidate_note": "MP3-derived full mix, not isolated vocal stem; used as a wide panned delay/reverb texture layer."
}
```
