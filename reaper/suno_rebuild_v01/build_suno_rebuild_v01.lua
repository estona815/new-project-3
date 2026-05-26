local project_path = "/Users/hantaeheuk/Documents/New project 3/reaper/suno_rebuild_v01/reaper_project.rpp"
local render_dir = "/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01"
local log_path = "/tmp/codex_suno_rebuild_v01_build.log"

local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\n")
    f:close()
  end
end

local function lin(db)
  return 10 ^ (db / 20)
end

local function set_name(track, name)
  reaper.GetSetMediaTrackInfo_String(track, "P_NAME", name, true)
end

local function new_track(name, db, pan, mute, mainsend)
  local idx = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, true)
  local track = reaper.GetTrack(0, idx)
  set_name(track, name)
  reaper.SetMediaTrackInfo_Value(track, "D_VOL", lin(db or 0))
  reaper.SetMediaTrackInfo_Value(track, "D_PAN", pan or 0)
  reaper.SetMediaTrackInfo_Value(track, "B_MUTE", mute and 1 or 0)
  reaper.SetMediaTrackInfo_Value(track, "B_MAINSEND", mainsend and 1 or 0)
  return track
end

local function insert_media(track, path, mute)
  local source = reaper.PCM_Source_CreateFromFile(path)
  if not source then
    log("failed source: " .. tostring(path))
    return
  end
  local length = reaper.GetMediaSourceLength(source)
  local item = reaper.AddMediaItemToTrack(track)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, source)
  reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0)
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", length)
  reaper.SetMediaItemInfo_Value(item, "B_MUTE", mute and 1 or 0)
  reaper.GetSetMediaItemTakeInfo_String(take, "P_NAME", path:match("([^/]+)$") or path, true)
end

local function add_stock_fx(track, label)
  local tried = {{"VST: ReaEQ (Cockos)"}, {"ReaEQ (Cockos)"}, {"JS: Saturation"}, {"JS: Soft Clipper/Limiter"}}
  for _, names in ipairs(tried) do
    for _, name in ipairs(names) do
      local idx = reaper.TrackFX_AddByName(track, name, false, -1)
      if idx >= 0 then
        reaper.GetSetMediaTrackInfo_String(track, "P_EXT:stock_fx_" .. label, name, true)
        return
      end
    end
  end
  reaper.GetSetMediaTrackInfo_String(track, "P_EXT:stock_fx_" .. label, "none inserted", true)
end

local function clear_project()
  for i = reaper.CountTracks(0) - 1, 0, -1 do
    reaper.DeleteTrack(reaper.GetTrack(0, i))
  end
end

log("build start")
reaper.Undo_BeginBlock()
clear_project()

reaper.GetSetProjectInfo(0, "PROJECT_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "PROJECT_SRATE_USE", 1, true)
reaper.GetSetProjectInfo(0, "PROJECT_TEMPO", 162.000162000, true)
if reaper.SetCurrentBPM then
  reaper.SetCurrentBPM(0, 162.000162000, true)
end
if reaper.SetTempoTimeSigMarker then
  reaper.SetTempoTimeSigMarker(0, -1, 0, -1, -1, 162.000162000, 4, 4, false)
end
reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 0, true)
reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0.0, true)
reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", 141.394000000, true)
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", render_dir, true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "rebuilt_full_mix_reaper_sum", true)

reaper.AddProjectMarker2(0, false, 0.000000000, 0, "intro / filtered melody sketch", 1, 0)
reaper.AddProjectMarker2(0, false, 11.851840000, 0, "verse 1 / drums enter light", 2, 0)
reaper.AddProjectMarker2(0, false, 35.555520000, 0, "hook 1 / full melody-forward lift", 3, 0)
reaper.AddProjectMarker2(0, false, 59.259200000, 0, "verse 2 / tighter groove variation", 4, 0)
reaper.AddProjectMarker2(0, false, 82.962880000, 0, "bridge / half-drop and space", 5, 0)
reaper.AddProjectMarker2(0, false, 94.814720000, 0, "hook 2 / full rebuild return", 6, 0)
reaper.AddProjectMarker2(0, false, 118.518400000, 0, "final lift / densest drums and counter melody", 7, 0)
reaper.AddProjectMarker2(0, false, 130.370240000, 0, "outro / melody decay", 8, 0)
reaper.AddProjectMarker2(0, false, 141.394000000, 0, "reference length / render end", 9, 0)

local tr = new_track("REF MUTED - Suno full mix analysis only", -18.0, 0.0, true, false)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/00_REF_Full_Mix.wav", true)
local tr = new_track("REF MUTED - Suno drums stem analysis only", -18.0, 0.0, true, false)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/10_Drums.wav", true)
local tr = new_track("REF MUTED - Suno bass stem analysis only", -18.0, 0.0, true, false)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/09_Bass.wav", true)
local tr = new_track("REF MUTED - Suno synth stem analysis only", -18.0, 0.0, true, false)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/04_Synth.wav", true)
local tr = new_track("REF MUTED - Suno FX stem analysis only", -18.0, 0.0, true, false)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/03_FX.wav", true)
local tr = new_track("REF MUTED - Suno vocal stem analysis only", -18.0, 0.0, true, false)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/12_Vocals.wav", true)
local tr = new_track("PROD DRUMS - rebuilt programmed audio", -5.5, 0.0, false, true)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01/drums_stem.wav", false)
add_stock_fx(tr, "drums")
local tr = new_track("PROD 808 BASS - rebuilt tuned B minor", -6.0, 0.0, false, true)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01/bass_808_stem.wav", false)
add_stock_fx(tr, "bass")
local tr = new_track("PROD MELODY - rebuilt piano bell pluck pad", -3.0, 0.0, false, true)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01/melody_stem.wav", false)
add_stock_fx(tr, "melody")
local tr = new_track("PROD FX - rebuilt transitions no vocal chops", -10.0, 0.0, false, true)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01/fx_stem.wav", false)
add_stock_fx(tr, "fx")
local print = new_track("PRINT CHECK MUTED - rebuilt_full_mix.wav", -12.0, 0.0, true, false)
insert_media(print, "/Users/hantaeheuk/Documents/New project 3/renders/suno_rebuild_v01/rebuilt_full_mix.wav", true)
local tr = new_track("MIDI DRUM PROGRAM - rebuilt guide", 0.0, 0.0, true, false)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/reaper/suno_rebuild_v01/midi/rebuilt_drums.mid", true)
local tr = new_track("MIDI 808 BASSLINE - rebuilt guide", 0.0, 0.0, true, false)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/reaper/suno_rebuild_v01/midi/rebuilt_bass_808.mid", true)
local tr = new_track("MIDI MELODY CHORDS - rebuilt guide", 0.0, 0.0, true, false)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/reaper/suno_rebuild_v01/midi/rebuilt_melody.mid", true)
local tr = new_track("MIDI FX CUES - rebuilt guide", 0.0, 0.0, true, false)
insert_media(tr, "/Users/hantaeheuk/Documents/New project 3/reaper/suno_rebuild_v01/midi/rebuilt_fx.mid", true)

local notes = [[
Suno reference/stems are muted and have no master send. Active production tracks are newly synthesized/printed from rebuilt MIDI programming. MIDI tracks are muted guide tracks for editability; rendered stems are active for reliable playback without third-party instruments.
]]
reaper.GetSetProjectNotes(0, true, notes)
reaper.Undo_EndBlock("Build Suno rebuild v01", -1)
reaper.UpdateArrange()
reaper.Main_SaveProjectEx(0, project_path, 0)
log("build done " .. project_path)
