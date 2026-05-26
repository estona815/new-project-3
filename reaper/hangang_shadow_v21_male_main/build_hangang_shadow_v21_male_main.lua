-- Build a focused REAPER mix/master session for Hangang Shadow v21 male-main.
-- Active render path uses the latest v19 two-stem export to preserve structure.
-- Full-stem material is imported only as muted reference context.

local root = "/Users/hantaeheuk/Documents/New project 3"
local work = root .. "/audio_work/hangang_shadow_v20_commercial_polish"
local project_dir = root .. "/reaper/hangang_shadow_v21_male_main"
local project_path = project_dir .. "/hangang_shadow_mashup_v21_male_main.rpp"
local log_path = "/tmp/codex_hangang_shadow_v21/build.log"

os.execute("mkdir -p /tmp/codex_hangang_shadow_v21")
os.execute("mkdir -p " .. string.format("%q", project_dir))

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

local function track_name(track)
  local _, name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
  return name or ""
end

local function new_track(name, db, pan, mute, mainsend)
  local idx = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, true)
  local track = reaper.GetTrack(0, idx)
  set_name(track, name)
  reaper.SetMediaTrackInfo_Value(track, "D_VOL", lin(db or 0))
  reaper.SetMediaTrackInfo_Value(track, "D_PAN", pan or 0)
  reaper.SetMediaTrackInfo_Value(track, "B_MUTE", mute and 1 or 0)
  if mainsend ~= nil then
    reaper.SetMediaTrackInfo_Value(track, "B_MAINSEND", mainsend and 1 or 0)
  end
  return track
end

local function add_send(src, dest, db)
  if not src or not dest then return -1 end
  local send = reaper.CreateTrackSend(src, dest)
  reaper.SetTrackSendInfo_Value(src, 0, send, "D_VOL", lin(db or 0))
  return send
end

local function select_only(track)
  reaper.Main_OnCommand(40297, 0)
  reaper.SetTrackSelected(track, true)
end

local function insert_media(track, path, mute)
  local source = reaper.PCM_Source_CreateFromFile(path)
  if not source then
    log("PCM_Source_CreateFromFile failed: " .. path)
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
  log("media added to " .. track_name(track) .. " length=" .. tostring(length) .. " path=" .. path)
end

local function add_fx(track, names, label)
  for _, name in ipairs(names) do
    local idx = reaper.TrackFX_AddByName(track, name, false, -1)
    if idx >= 0 then
      reaper.GetSetMediaTrackInfo_String(track, "P_EXT:v21_fx_" .. label, name, true)
      log("added fx " .. name .. " on " .. track_name(track))
      return idx
    end
  end
  reaper.GetSetMediaTrackInfo_String(track, "P_EXT:missing_v21_fx_" .. label, table.concat(names, " | "), true)
  log("missing fx " .. label .. " on " .. track_name(track))
  return -1
end

local function set_params(track, fx_idx, values)
  if fx_idx < 0 then return end
  for param, value in pairs(values) do
    reaper.TrackFX_SetParam(track, fx_idx, param - 1, value)
  end
end

local function add_channel_polish(track, label, values)
  local idx = add_fx(track, {
    "JS: Codex V20 Channel Polish",
    "JS: codex_fresh_mix/codex_v20_channel_polish.jsfx",
    "codex_fresh_mix/codex_v20_channel_polish.jsfx",
  }, label)
  set_params(track, idx, values)
  return idx
end

local function add_dynamic_eq(track, label, values)
  local idx = add_fx(track, {
    "JS: Codex Dynamic EQ Band",
    "JS: codex_fresh_mix/codex_dynamic_eq_band.jsfx",
    "codex_fresh_mix/codex_dynamic_eq_band.jsfx",
  }, label)
  set_params(track, idx, values)
  return idx
end

local function add_noise_tamer(track, label, values)
  local idx = add_fx(track, {
    "JS: Codex Noise Floor Tamer",
    "JS: codex_fresh_mix/codex_noise_floor_tamer.jsfx",
    "codex_fresh_mix/codex_noise_floor_tamer.jsfx",
  }, label)
  set_params(track, idx, values)
  return idx
end

local function add_presence_tilt(track, label, values)
  local idx = add_fx(track, {
    "JS: Codex Presence Tilt",
    "JS: codex_fresh_mix/codex_presence_tilt.jsfx",
    "codex_fresh_mix/codex_presence_tilt.jsfx",
  }, label)
  set_params(track, idx, values)
  return idx
end

local function add_master_glue(track, values)
  local idx = add_fx(track, {
    "JS: Codex V20 Master Glue",
    "JS: codex_fresh_mix/codex_v20_master_glue.jsfx",
    "codex_fresh_mix/codex_v20_master_glue.jsfx",
  }, "master_glue")
  set_params(track, idx, values)
  return idx
end

local function clear_project()
  for i = reaper.CountTracks(0) - 1, 0, -1 do
    reaper.DeleteTrack(reaper.GetTrack(0, i))
  end
end

local function active_item_end()
  local max_end = 0
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    if reaper.GetMediaTrackInfo_Value(tr, "B_MUTE") < 0.5 then
      for j = 0, reaper.CountTrackMediaItems(tr) - 1 do
        local item = reaper.GetTrackMediaItem(tr, j)
        if reaper.GetMediaItemInfo_Value(item, "B_MUTE") < 0.5 then
          local pos = reaper.GetMediaItemInfo_Value(item, "D_POSITION")
          local len = reaper.GetMediaItemInfo_Value(item, "D_LENGTH")
          if pos + len > max_end then max_end = pos + len end
        end
      end
    end
  end
  return max_end
end

log("build start")
reaper.Undo_BeginBlock()
clear_project()

if reaper.GetSetProjectInfo then
  reaper.GetSetProjectInfo(0, "PROJECT_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "PROJECT_SRATE_USE", 1, true)
  reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
  reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 0, true)
end

reaper.GetSetProjectInfo(0, "PROJECT_TEMPO", 180, true)

local ref_bus = new_track("REF_BUS_MUTED", -18, 0, true, false)
local vocal_bus = new_track("MALE_MAIN_VOCAL_BUS", 1.25, 0, false, false)
local female_double_bus = new_track("FEMALE_DOUBLE_LAYER_BUS_LOW", -13.5, 0, false, false)
local music_bus = new_track("FULL_STEM_MUSIC_BUS", -0.85, 0, false, false)
local mix_bus = new_track("MIX_BUS_MALE_MAIN_COMMERCIAL", -4.2, 0, false, false)
local print_bus = new_track("PRINT_MASTER_BUS", 0, 0, false, true)

add_send(female_double_bus, vocal_bus, 0)
add_send(vocal_bus, mix_bus, 0)
add_send(music_bus, mix_bus, 0)
add_send(mix_bus, print_bus, 0)

local lead = new_track("MALE MAIN - 12 Vocals", -5.1, 0, false, false)
insert_media(lead, work .. "/source_full_stems/12 Vocals.wav", false)
add_send(lead, vocal_bus, 0)

local female_double = new_track("FEMALE DOUBLE LOW - 11 Backing_Vocals", -18.2, 0.0, false, false)
insert_media(female_double, work .. "/source_full_stems/11 Backing_Vocals.wav", false)
add_send(female_double, female_double_bus, 0)

local function add_music_stem(name, file, db, pan, mute)
  local tr = new_track(name, db, pan or 0, mute or false, false)
  insert_media(tr, work .. "/source_full_stems/" .. file, mute or false)
  add_send(tr, music_bus, 0)
  return tr
end

add_music_stem("MUSIC - Woodwinds", "1 Woodwinds.wav", -13.2, -0.04, false)
add_music_stem("MUSIC - Brass", "2 Brass.wav", -13.8, 0.04, false)
add_music_stem("MUSIC - FX low", "3 FX.wav", -17.5, 0, false)
add_music_stem("MUSIC - Synth", "4 Synth.wav", -11.0, 0, false)
add_music_stem("MUSIC - Strings", "5 Strings.wav", -13.3, 0, false)
add_music_stem("MUSIC - Percussion", "6 Percussion.wav", -12.2, 0, false)
add_music_stem("MUSIC - Keyboard", "7 Keyboard.wav", -11.4, 0, false)
add_music_stem("MUSIC - Bass", "9 Bass.wav", -11.2, 0, false)
add_music_stem("MUSIC - Drums", "10 Drums.wav", -9.7, 0, false)
add_music_stem("MUTED ARTIFACT CANDIDATE - 8 Guitar", "8 Guitar.wav", -24, 0, true)

local full_ref = new_track("FULL STEM REF - muted original mix", -18, 0, true, false)
insert_media(full_ref, work .. "/source_full_stems/0 한강 Shadow x 얇은 Shadow (Mashup).wav", true)
add_send(full_ref, ref_bus, -18)

local female_v19_ref = new_track("MUTED FEMALE LEAD CANDIDATE - v19 0 Lead Vocals", -18, 0, true, false)
insert_media(female_v19_ref, work .. "/source_v19_2stem/0 Lead Vocals.wav", true)
add_send(female_v19_ref, ref_bus, -18)

local v19_inst_ref = new_track("MUTED V19 INSTRUMENTAL REF", -18, 0, true, false)
insert_media(v19_inst_ref, work .. "/source_v19_2stem/1 Instrumental.wav", true)
add_send(v19_inst_ref, ref_bus, -18)

add_fx(lead, {"ReaEQ", "VST: ReaEQ (Cockos)"}, "lead_stock_eq_marker")
add_fx(lead, {"ReaTune", "VST: ReaTune (Cockos)"}, "lead_subtle_tune_marker")
add_fx(lead, {"ReaComp", "VST: ReaComp (Cockos)"}, "lead_stock_comp_marker")
add_channel_polish(lead, "lead_polish", {
  [1] = 92, [2] = 150, [3] = -0.35, [4] = 285, [5] = -0.85, [6] = 0.95,
  [7] = 3150, [8] = 1.05, [9] = 0.9, [10] = 10800, [11] = 0.55,
  [12] = -25.5, [13] = 1.72, [14] = 14, [15] = 135, [16] = 0.55,
  [17] = 0.9, [18] = 0.08, [19] = 0.98, [20] = 0.0,
})
add_dynamic_eq(lead, "lead_sibilance_dynamic_tame", {
  [1] = 6800, [2] = 1.35, [3] = -38.5, [4] = 2.2, [5] = 6.0, [6] = 85.0, [7] = 0,
})
add_presence_tilt(lead, "lead_presence_tilt", {
  [1] = 2500, [2] = 0.35, [3] = 0.65,
})

add_channel_polish(female_double, "female_double_tucked_polish", {
  [1] = 185, [2] = 220, [3] = -0.8, [4] = 520, [5] = -1.4, [6] = 1.0,
  [7] = 3600, [8] = -0.4, [9] = 0.9, [10] = 8800, [11] = -0.9,
  [12] = -29.0, [13] = 1.55, [14] = 20, [15] = 210, [16] = -0.4,
  [17] = 0.25, [18] = 0.035, [19] = 1.16, [20] = 0.0,
})
add_dynamic_eq(female_double, "female_double_deess_tucked", {
  [1] = 6200, [2] = 1.2, [3] = -43.0, [4] = 3.0, [5] = 8.0, [6] = 120.0, [7] = 0,
})

add_channel_polish(vocal_bus, "vocal_bus_polish", {
  [1] = 85, [2] = 180, [3] = 0.15, [4] = 330, [5] = -0.55, [6] = 0.85,
  [7] = 3850, [8] = 0.45, [9] = 0.9, [10] = 10200, [11] = 0.25,
  [12] = -22.0, [13] = 1.38, [14] = 24, [15] = 170, [16] = 0.35,
  [17] = 0.55, [18] = 0.05, [19] = 0.97, [20] = 0.0,
})
add_dynamic_eq(vocal_bus, "vocal_bus_harshness_tame", {
  [1] = 4300, [2] = 1.0, [3] = -35.0, [4] = 1.5, [5] = 8.0, [6] = 120.0, [7] = 0,
})

add_channel_polish(music_bus, "music_bus_polish", {
  [1] = 24, [2] = 90, [3] = -0.1, [4] = 290, [5] = -0.3, [6] = 0.75,
  [7] = 1700, [8] = -0.25, [9] = 0.9, [10] = 11200, [11] = 0.25,
  [12] = -21.5, [13] = 1.16, [14] = 42, [15] = 260, [16] = 0.15,
  [17] = 0.35, [18] = 0.035, [19] = 1.04, [20] = 0.0,
})
add_dynamic_eq(music_bus, "music_bus_vocal_space", {
  [1] = 2300, [2] = 0.9, [3] = -35.0, [4] = 1.1, [5] = 16.0, [6] = 190.0, [7] = 0,
})
add_noise_tamer(music_bus, "music_high_tail_tamer", {
  [1] = 9200, [2] = -49.0, [3] = 1.5, [4] = 24.0, [5] = 320.0, [6] = 0.55,
})

add_channel_polish(mix_bus, "mix_bus_polish", {
  [1] = 22, [2] = 95, [3] = -0.15, [4] = 310, [5] = -0.35, [6] = 0.95,
  [7] = 3300, [8] = 0.18, [9] = 1.0, [10] = 11600, [11] = 0.22,
  [12] = -19.0, [13] = 1.18, [14] = 35, [15] = 240, [16] = 0.2,
  [17] = 0.4, [18] = 0.035, [19] = 1.0, [20] = 0.0,
})
add_dynamic_eq(mix_bus, "mix_bus_low_mid_tighten", {
  [1] = 310, [2] = 0.95, [3] = -29.0, [4] = 1.2, [5] = 18.0, [6] = 220.0, [7] = 0,
})

add_master_glue(print_bus, {
  [1] = 24, [2] = -0.35, [3] = 88, [4] = -0.25, [5] = 320,
  [6] = -0.22, [7] = 3850, [8] = 0.18, [9] = 11200,
  [10] = -17.5, [11] = 1.22, [12] = 34, [13] = 185, [14] = 1.1,
  [15] = 2.0, [16] = -1.2, [17] = 0.0,
})
local horizon_idx = add_fx(print_bus, {
  "JS: Event Horizon Limiter/Clipper",
  "sstillwell/eventhorizon2",
}, "event_horizon_final_catch")
set_params(print_bus, horizon_idx, {
  [1] = -2.6,
  [2] = -1.0,
  [3] = 320.0,
})
add_fx(print_bus, {"JS: Loudness Meter Peak/RMS/LUFS"}, "loudness_meter")

local render_end = active_item_end() + 3.5
if reaper.GetSetProjectInfo then
  reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0, true)
  reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", render_end, true)
end

reaper.AddProjectMarker2(0, false, 0, 0, "START", -1, 0)
reaper.AddProjectMarker2(0, false, render_end * 0.25, 0, "ENERGY CHECK 1", -1, 0)
reaper.AddProjectMarker2(0, false, render_end * 0.50, 0, "MID BALANCE CHECK", -1, 0)
reaper.AddProjectMarker2(0, false, render_end * 0.75, 0, "FINAL LIFT CHECK", -1, 0)
reaper.AddProjectMarker2(0, false, render_end - 3.5, 0, "TAIL", -1, 0)

reaper.UpdateArrange()
reaper.Main_SaveProjectEx(0, project_path, 0)
reaper.Undo_EndBlock("Build Hangang Shadow v21 male-main commercial polish", -1)
log("build done project=" .. project_path .. " render_end=" .. tostring(render_end))
