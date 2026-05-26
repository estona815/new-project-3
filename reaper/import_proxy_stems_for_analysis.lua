-- Import analysis-only proxy stems into REAPER.
-- These are not release stems. Use them for measurement/routing/QC only.

local files = {
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-broken_master_24-48/estona_nib-broken_master_24-48_sub_bass_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-broken_master_24-48/estona_nib-broken_master_24-48_center_vocal_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-broken_master_24-48/estona_nib-broken_master_24-48_percussive_drum_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-broken_master_24-48/estona_nib-broken_master_24-48_harmonic_music_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-broken_master_24-48/estona_nib-broken_master_24-48_side_space_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-broken_master_24-48/estona_nib-broken_master_24-48_air_hash_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-broken_master_24-48/estona_nib-broken_master_24-48_reverb_tail_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-dough_master_24-48/estona_nib-dough_master_24-48_sub_bass_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-dough_master_24-48/estona_nib-dough_master_24-48_center_vocal_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-dough_master_24-48/estona_nib-dough_master_24-48_percussive_drum_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-dough_master_24-48/estona_nib-dough_master_24-48_harmonic_music_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-dough_master_24-48/estona_nib-dough_master_24-48_side_space_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-dough_master_24-48/estona_nib-dough_master_24-48_air_hash_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-dough_master_24-48/estona_nib-dough_master_24-48_reverb_tail_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-imnk_master_24-48/estona_nib-imnk_master_24-48_sub_bass_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-imnk_master_24-48/estona_nib-imnk_master_24-48_center_vocal_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-imnk_master_24-48/estona_nib-imnk_master_24-48_percussive_drum_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-imnk_master_24-48/estona_nib-imnk_master_24-48_harmonic_music_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-imnk_master_24-48/estona_nib-imnk_master_24-48_side_space_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-imnk_master_24-48/estona_nib-imnk_master_24-48_air_hash_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-imnk_master_24-48/estona_nib-imnk_master_24-48_reverb_tail_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-lovee_master_24-48/estona_nib-lovee_master_24-48_sub_bass_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-lovee_master_24-48/estona_nib-lovee_master_24-48_center_vocal_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-lovee_master_24-48/estona_nib-lovee_master_24-48_percussive_drum_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-lovee_master_24-48/estona_nib-lovee_master_24-48_harmonic_music_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-lovee_master_24-48/estona_nib-lovee_master_24-48_side_space_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-lovee_master_24-48/estona_nib-lovee_master_24-48_air_hash_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-lovee_master_24-48/estona_nib-lovee_master_24-48_reverb_tail_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-missu_master_24-48/estona_nib-missu_master_24-48_sub_bass_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-missu_master_24-48/estona_nib-missu_master_24-48_center_vocal_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-missu_master_24-48/estona_nib-missu_master_24-48_percussive_drum_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-missu_master_24-48/estona_nib-missu_master_24-48_harmonic_music_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-missu_master_24-48/estona_nib-missu_master_24-48_side_space_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-missu_master_24-48/estona_nib-missu_master_24-48_air_hash_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-missu_master_24-48/estona_nib-missu_master_24-48_reverb_tail_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-phobia_master_24-48/estona_nib-phobia_master_24-48_sub_bass_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-phobia_master_24-48/estona_nib-phobia_master_24-48_center_vocal_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-phobia_master_24-48/estona_nib-phobia_master_24-48_percussive_drum_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-phobia_master_24-48/estona_nib-phobia_master_24-48_harmonic_music_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-phobia_master_24-48/estona_nib-phobia_master_24-48_side_space_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-phobia_master_24-48/estona_nib-phobia_master_24-48_air_hash_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-phobia_master_24-48/estona_nib-phobia_master_24-48_reverb_tail_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-stuck_in_seoul_master_24-48/estona_nib-stuck_in_seoul_master_24-48_sub_bass_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-stuck_in_seoul_master_24-48/estona_nib-stuck_in_seoul_master_24-48_center_vocal_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-stuck_in_seoul_master_24-48/estona_nib-stuck_in_seoul_master_24-48_percussive_drum_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-stuck_in_seoul_master_24-48/estona_nib-stuck_in_seoul_master_24-48_harmonic_music_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-stuck_in_seoul_master_24-48/estona_nib-stuck_in_seoul_master_24-48_side_space_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-stuck_in_seoul_master_24-48/estona_nib-stuck_in_seoul_master_24-48_air_hash_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-stuck_in_seoul_master_24-48/estona_nib-stuck_in_seoul_master_24-48_reverb_tail_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-why_master_24-48/estona_nib-why_master_24-48_sub_bass_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-why_master_24-48/estona_nib-why_master_24-48_center_vocal_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-why_master_24-48/estona_nib-why_master_24-48_percussive_drum_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-why_master_24-48/estona_nib-why_master_24-48_harmonic_music_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-why_master_24-48/estona_nib-why_master_24-48_side_space_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-why_master_24-48/estona_nib-why_master_24-48_air_hash_proxy.flac",
  "/Users/hantaeheuk/Documents/New project 3/audio_work/proxy_stems/estona_nib-why_master_24-48/estona_nib-why_master_24-48_reverb_tail_proxy.flac"
}

reaper.Undo_BeginBlock()
reaper.PreventUIRefresh(1)
for _, path in ipairs(files) do
  reaper.InsertMedia(path, 1)
end
reaper.AddProjectMarker2(0, false, 0, 0, "ESTONA proxy stems imported for analysis only", -1, 0)
reaper.PreventUIRefresh(-1)
reaper.UpdateArrange()
reaper.Undo_EndBlock("Import ESTONA proxy stems for analysis", -1)
