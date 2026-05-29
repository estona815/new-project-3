-- Create explicit partial rebeat tracks from evidence flags.
-- Empty unavailable tracks are deliberately named as unavailable so audits cannot treat them as proof.

local function ext(key, fallback)
  local value = reaper.GetExtState("codex_rebeat", key)
  if value == nil or value == "" then return fallback end
  return value
end

local function add_track(name, note)
  local index = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(index, true)
  local track = reaper.GetTrack(0, index)
  reaper.GetSetMediaTrackInfo_String(track, "P_NAME", name, true)
  if note ~= nil then
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:codex_rebeat_note", note, true)
  end
  return track
end

reaper.Undo_BeginBlock()
if ext("has_bass_midi", "false") == "true" then
  add_track("08_BASS_REBUILD_MIDI", "Bass MIDI evidence supplied; audit note count before claiming.")
else
  add_track("08_BASS_REBUILD_UNAVAILABLE", "Bass reconstruction unavailable; do not fake bass MIDI.")
end

if ext("has_music_midi", "false") == "true" then
  add_track("10_MUSIC_REBUILD_MIDI", "Music/chord/lead evidence supplied; audit note count before claiming.")
else
  add_track("10_MUSIC_MIDI_NOT_CONFIDENT", "Music/chord/lead reconstruction unavailable; do not fabricate chords.")
end

if ext("has_fx_support", "false") == "true" then
  add_track("FX_MIDI_OR_AUDIO_SUPPORT", "FX support evidence supplied.")
end
reaper.Undo_EndBlock("Create partial rebeat tracks", -1)
