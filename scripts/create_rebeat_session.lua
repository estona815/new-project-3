-- Evidence-first REAPER rebeat session scaffold.
-- Configure with project extstates before running:
--   reaper.SetExtState("codex_rebeat", "source_path", "/path/source.wav", false)
--   reaper.SetExtState("codex_rebeat", "report_path", "/path/reports/song_vNEXT_rebeat_report.md", false)

local function ext(key, fallback)
  local value = reaper.GetExtState("codex_rebeat", key)
  if value == nil or value == "" then return fallback end
  return value
end

local function add_track(name, unavailable_note)
  local index = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(index, true)
  local track = reaper.GetTrack(0, index)
  reaper.GetSetMediaTrackInfo_String(track, "P_NAME", name, true)
  if unavailable_note ~= nil and unavailable_note ~= "" then
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:codex_rebeat_note", unavailable_note, true)
  end
  return track
end

local function add_media_item(track, source_path)
  if source_path == nil or source_path == "" then return end
  local source = reaper.PCM_Source_CreateFromFile(source_path)
  if source == nil then return end
  local item = reaper.AddMediaItemToTrack(track)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, source)
  local length = reaper.GetMediaSourceLength(source)
  reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0)
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", length)
  reaper.UpdateItemInProject(item)
end

reaper.Undo_BeginBlock()
reaper.Main_OnCommand(40023, 0) -- New project

local source_path = ext("source_path", "")
local report_path = ext("report_path", "")
local mode = ext("mode", "audit_scaffold")
local has_drum_midi = ext("has_drum_midi", "false") == "true"
local has_bass_midi = ext("has_bass_midi", "false") == "true"
local has_music_midi = ext("has_music_midi", "false") == "true"
local has_vocal_path = ext("has_vocal_path", "false") == "true"

local ref = add_track("01_REF_ORIGINAL", "Reference only; not proof of stem rebuild or rebeat.")
add_media_item(ref, source_path)
reaper.SetMediaTrackInfo_Value(ref, "B_MUTE", 1)

local working = add_track("02_WORKING_FULLMIX", "Active only for fullmix rescue, drum reinforcement, or support.")
if mode == "fullmix_rescue" or mode == "drum_reinforcement" or mode == "partial_rebeat" then
  add_media_item(working, source_path)
else
  reaper.SetMediaTrackInfo_Value(working, "B_MUTE", 1)
end

add_track("03_GRID_MARKERS", "Tempo/grid markers are written by the tempo-grid harness where available.")
add_track(has_drum_midi and "04_KICK_REBUILD_MIDI" or "04_KICK_REBUILD_UNAVAILABLE", has_drum_midi and "" or "No kick MIDI evidence supplied.")
add_track(has_drum_midi and "05_SNARE_CLAP_REBUILD_MIDI" or "05_SNARE_CLAP_REBUILD_UNAVAILABLE", has_drum_midi and "" or "No snare/clap MIDI evidence supplied.")
add_track(has_drum_midi and "06_HAT_PERC_REBUILD_MIDI" or "06_HAT_PERC_REBUILD_UNAVAILABLE", has_drum_midi and "" or "No hat/percussion MIDI evidence supplied.")
add_track("07_DRUMS_AUDIO_SUPPORT", "Use only for real samples/support audio. Empty track is not rebeat evidence.")
add_track(has_bass_midi and "08_BASS_REBUILD_MIDI" or "08_BASS_REBUILD_UNAVAILABLE", has_bass_midi and "" or "Bass reconstruction unavailable until pitch/stem/MIDI evidence exists.")
add_track("09_BASS_AUDIO_SUPPORT", "Use only when bass support audio exists and phase/headroom pass.")
add_track(has_music_midi and "10_MUSIC_REBUILD_MIDI" or "10_MUSIC_MIDI_NOT_CONFIDENT", has_music_midi and "" or "No reliable chord/lead reconstruction evidence supplied.")
add_track("11_MUSIC_STEMS_OR_AUDIO_SUPPORT", "Import stems/support here; label machine-separated stems in reports.")
add_track(has_vocal_path and "12_VOCAL_OR_FULLMIX_DERIVED_VOCAL_REPAIR" or "12_VOCAL_STEM_MISSING", has_vocal_path and "" or "No isolated vocal evidence supplied.")
add_track("13_DEAI_NOISE_REDUCTION_BUS", "Suno DeAI/custom noise reduction chain must be plugin-audited.")
add_track("14_PARALLEL_DRUM_COMP", "Use only when drum support exists and transient QC passes.")
add_track("15_MID_SIDE_REPAIR_BUS", "M/S EQ/side wash control must follow engineering rulebook.")
add_track("16_MIX_BUS", "Active mix routing.")
add_track("17_MASTER_BUS", "Dynamic EQ, limiter, output guard.")
add_track("18_MASTER_PRINT", "Final print target; render only after QC gates pass.")

if report_path ~= "" then
  reaper.GetSetProjectNotes(0, true, "Codex rebeat evidence scaffold\nReport: " .. report_path .. "\nMode: " .. mode)
end

local save_path = ext("save_path", "")
if save_path ~= "" then
  reaper.Main_SaveProjectEx(0, save_path, 0)
end

reaper.Undo_EndBlock("Create evidence-first rebeat session", -1)
