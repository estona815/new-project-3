# badabonjok_eomneun_sarang_v01_anime_rock Mix/Master Notes

## Status
- Source: user-provided Suno stems zip.
- Workflow status: genre_based_draft with measured local audio QC.
- Duration: 76.040s, sample rate: 48000 Hz.
- Estimated tempo: 84 BPM.
- Rough tonal center: C#.
- Suno generation: anime rock Korean female vocal cover pass generated on Suno v5.5.
- Suno credits used: 20 credits total, under the requested 200-credit cap.
- Downloaded candidate: `/Users/hantaeheuk/Documents/New project 3/audio_work/badabonjok_eomneun_sarang_v01_anime_rock/suno_generated_candidates/suno_anime_rock_female_candidate_7016b495.mp3`

## Render Outputs
- Master WAV: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v01_anime_rock/badabonjok_eomneun_sarang_v01_anime_rock_MASTER_48k16.wav`
- Premaster WAV: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v01_anime_rock/badabonjok_eomneun_sarang_v01_anime_rock_premaster_48k16.wav`
- Instrumental mix: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v01_anime_rock/badabonjok_eomneun_sarang_v01_anime_rock_instrumental_mix_48k16.wav`
- Vocal reference: `/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v01_anime_rock/badabonjok_eomneun_sarang_v01_anime_rock_vocal_reference_48k16.wav`

## Mix Direction
- Anime-rock / digicore vocal-forward balance.
- Lead vocal cleaned with high-pass, mild de-harsh, compression, and top-end control.
- Backing vocal tucked/widened to leave room for a future female Suno vocal layer.
- Kick/bass given controlled saturation and low-end density without broad level pushing.
- Synth/other beds tucked and de-harshened so a generated female vocal can sit on top.

## Limitation
- Suno's `Get Stems / MIDI` menu is locked behind Premier on the active account, so I could not download an isolated female vocal stem from the generated cover. I downloaded the available MP3 candidate instead and kept it with the project. Once a vocal stem or WAV export is available, place it in `audio_work/badabonjok_eomneun_sarang_v01_anime_rock/suno_female_vocal.wav` and align/mix it against the vocal reference.
- MP3 delivery QC was replaced with AAC preview QC because `ffmpeg`/`lame` are not installed locally.

## QC
```json
{
  "slug": "badabonjok_eomneun_sarang_v01_anime_rock",
  "sample_rate": 48000,
  "duration_seconds": 76.04,
  "estimated_bpm": 84,
  "rough_key_center": "C#",
  "source_mix_metrics": {
    "peak_dbfs": -2.31,
    "rms_dbfs": -17.22,
    "rough_integrated_lufs": -17.97,
    "stereo_correlation": 0.974
  },
  "premaster_metrics": {
    "peak_dbfs": -7.6,
    "rms_dbfs": -16.84,
    "rough_integrated_lufs": -17.56,
    "stereo_correlation": 0.986
  },
  "master_metrics": {
    "peak_dbfs": -1.0,
    "rms_dbfs": -7.72,
    "rough_integrated_lufs": -8.44,
    "stereo_correlation": 0.985
  },
  "rendered_files": [
    "/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v01_anime_rock/badabonjok_eomneun_sarang_v01_anime_rock_MASTER_48k16.wav",
    "/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v01_anime_rock/badabonjok_eomneun_sarang_v01_anime_rock_premaster_48k16.wav",
    "/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v01_anime_rock/badabonjok_eomneun_sarang_v01_anime_rock_instrumental_mix_48k16.wav",
    "/Users/hantaeheuk/Documents/New project 3/renders/badabonjok_eomneun_sarang_v01_anime_rock/badabonjok_eomneun_sarang_v01_anime_rock_vocal_reference_48k16.wav"
  ]
}
```
