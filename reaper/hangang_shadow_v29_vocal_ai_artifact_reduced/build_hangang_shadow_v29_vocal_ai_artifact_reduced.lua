-- Build a focused REAPER vocal artifact-reduction session for Hangang Shadow v29.
-- Start from the v27/v28 timing-safe structure, keep the male lead as the only active vocal,
-- and reduce Suno-style metallic/sandy top texture without heavy pitch correction.

local root = "/Users/hantaeheuk/Documents/New project 3"
local work = root .. "/audio_work/hangang_shadow_v20_commercial_polish"
local female_source_work = root .. "/audio_work/hangang_shadow_v23_new_female_gated_pan"
local project_dir = root .. "/reaper/hangang_shadow_v29_vocal_ai_artifact_reduced"
local project_path = project_dir .. "/hangang_shadow_mashup_v29_vocal_ai_artifact_reduced.rpp"
local log_path = "/tmp/codex_hangang_shadow_v29/build.log"

os.execute("mkdir -p /tmp/codex_hangang_shadow_v29")
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
  return item
end

local function add_fx(track, names, label)
  for _, name in ipairs(names) do
    local idx = reaper.TrackFX_AddByName(track, name, false, -1)
    if idx >= 0 then
      reaper.GetSetMediaTrackInfo_String(track, "P_EXT:v29_fx_" .. label, name, true)
      log("added fx " .. name .. " on " .. track_name(track))
      return idx
    end
  end
  reaper.GetSetMediaTrackInfo_String(track, "P_EXT:missing_v29_fx_" .. label, table.concat(names, " | "), true)
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

local function add_ms_melody_tuck(track, label, values)
  local idx = add_fx(track, {
    "JS: Codex MS Melody Tuck",
    "JS: codex_fresh_mix/codex_ms_melody_tuck.jsfx",
    "codex_fresh_mix/codex_ms_melody_tuck.jsfx",
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

local ref_bus = new_track("reference_bus", -18, 0, true, false)
local vocal_bus = new_track("MALE_MAIN_VOCAL_BUS", -0.35, 0, false, false)
local female_double_bus = new_track("FEMALE_DOUBLE_LAYER_BUS_MUTED_REFERENCE", -60.0, 0, true, false)
local music_bus = new_track("instrumental", 0.20, 0, false, false)
local mix_bus = new_track("mix_bus", -2.30, 0, false, false)
local print_bus = new_track("PRINT_MASTER_BUS", 0, 0, false, true)

add_send(vocal_bus, mix_bus, 0)
add_send(music_bus, mix_bus, 0)
add_send(mix_bus, print_bus, 0)

local lead = new_track("vocal_processed - male lead 12 Vocals", -6.70, 0, false, false)
insert_media(lead, work .. "/source_full_stems/12 Vocals.wav", false)
add_send(lead, vocal_bus, 0)

local lead_density = new_track("VOCAL NATURAL DENSITY PARALLEL - no tune", -24.0, 0, false, false)
insert_media(lead_density, work .. "/source_full_stems/12 Vocals.wav", false)
add_send(lead_density, vocal_bus, 0)

local lead_room = new_track("VOCAL SHORT ROOM SLAP - dark blend", -31.0, 0, false, false)
local lead_room_item = insert_media(lead_room, work .. "/source_full_stems/12 Vocals.wav", false)
if lead_room_item then
  reaper.SetMediaItemInfo_Value(lead_room_item, "D_POSITION", 0.046)
end
add_send(lead_room, vocal_bus, 0)

local old_female_bgv_ref = new_track("MUTED OLD FEMALE DOUBLE - 11 Backing_Vocals ALIGN FAIL", -60.0, 0.0, true, false)
insert_media(old_female_bgv_ref, work .. "/source_full_stems/11 Backing_Vocals.wav", true)
add_send(old_female_bgv_ref, ref_bus, -18)

local vocal_raw_ref = new_track("vocal_raw - muted unprocessed male lead", -18, 0, true, false)
insert_media(vocal_raw_ref, work .. "/source_full_stems/12 Vocals.wav", true)
add_send(vocal_raw_ref, ref_bus, -18)

local function add_music_stem(name, file, db, pan, mute)
  local tr = new_track(name, db, pan or 0, mute or false, false)
  insert_media(tr, work .. "/source_full_stems/" .. file, mute or false)
  add_send(tr, music_bus, 0)
  return tr
end

local woodwinds = add_music_stem("MUSIC - Woodwinds", "1 Woodwinds.wav", -10.7, -0.04, false)
local brass = add_music_stem("MUSIC - Brass", "2 Brass.wav", -11.3, 0.04, false)
local fx_low = add_music_stem("MUSIC - FX low", "3 FX.wav", -15.0, 0, false)
local synth = add_music_stem("MUSIC - Synth", "4 Synth.wav", -9.25, 0, false)
local strings = add_music_stem("MUSIC - Strings", "5 Strings.wav", -10.8, 0, false)
local percussion = add_music_stem("MUSIC - Percussion", "6 Percussion.wav", -9.7, 0, false)
local keyboard = add_music_stem("MUSIC - Keyboard", "7 Keyboard.wav", -8.8, 0, false)
local bass = add_music_stem("MUSIC - Bass", "9 Bass.wav", -7.55, 0, false)
local drums = add_music_stem("MUSIC - Drums", "10 Drums.wav", -6.45, 0, false)
add_music_stem("MUTED ARTIFACT CANDIDATE - 8 Guitar", "8 Guitar.wav", -24, 0, true)

local full_ref = new_track("original_reference_track - muted full mix", -18, 0, true, false)
insert_media(full_ref, work .. "/source_full_stems/0 한강 Shadow x 얇은 Shadow (Mashup).wav", true)
add_send(full_ref, ref_bus, -18)

local female_v19_ref = new_track("MUTED FEMALE LEAD CANDIDATE - v19 0 Lead Vocals", -18, 0, true, false)
insert_media(female_v19_ref, work .. "/source_v19_2stem/0 Lead Vocals.wav", true)
add_send(female_v19_ref, ref_bus, -18)

local v19_inst_ref = new_track("MUTED V19 INSTRUMENTAL REF", -18, 0, true, false)
insert_media(v19_inst_ref, work .. "/source_v19_2stem/1 Instrumental.wav", true)
add_send(v19_inst_ref, ref_bus, -18)

local new_female_raw_ref = new_track("MUTED NEW FEMALE RAW REF - 0 Lead Vocals", -18, 0, true, false)
insert_media(new_female_raw_ref, female_source_work .. "/source_new_female_2stem/0 Lead Vocals.wav", true)
add_send(new_female_raw_ref, ref_bus, -18)

local new_female_inst_ref = new_track("MUTED NEW FEMALE INSTRUMENTAL REF", -18, 0, true, false)
insert_media(new_female_inst_ref, female_source_work .. "/source_new_female_2stem/1 Instrumental.wav", true)
add_send(new_female_inst_ref, ref_bus, -18)

add_fx(lead, {"ReaEQ", "VST: ReaEQ (Cockos)"}, "lead_stock_eq_marker_documentation")
add_fx(lead, {"ReaComp", "VST: ReaComp (Cockos)"}, "lead_stock_comp_marker_documentation")
add_channel_polish(lead, "lead_ai_artifact_reduction_polish", {
  [1] = 90, [2] = 155, [3] = -0.15, [4] = 285, [5] = -0.72, [6] = 0.90,
  [7] = 3150, [8] = -0.18, [9] = 0.90, [10] = 9800, [11] = -0.42,
  [12] = -25.4, [13] = 1.65, [14] = 18, [15] = 142, [16] = 0.20,
  [17] = 1.15, [18] = 0.070, [19] = 0.98, [20] = -0.10,
})
add_noise_tamer(lead, "lead_gap_fizz_tamer_not_gate", {
  [1] = 7900, [2] = -51.0, [3] = 1.55, [4] = 12.0, [5] = 245.0, [6] = 0.62,
})
add_dynamic_eq(lead, "lead_low_mid_buildup_dynamic", {
  [1] = 315, [2] = 1.00, [3] = -38.5, [4] = 1.2, [5] = 18.0, [6] = 150.0, [7] = 0,
})
add_dynamic_eq(lead, "lead_plastic_nasal_dynamic", {
  [1] = 950, [2] = 1.05, [3] = -40.5, [4] = 1.1, [5] = 16.0, [6] = 150.0, [7] = 0,
})
add_dynamic_eq(lead, "lead_harsh_ai_attack_dynamic", {
  [1] = 3550, [2] = 1.10, [3] = -39.0, [4] = 1.8, [5] = 10.0, [6] = 115.0, [7] = 0,
})
add_dynamic_eq(lead, "lead_sandy_sibilance_dynamic", {
  [1] = 6800, [2] = 1.35, [3] = -40.5, [4] = 2.7, [5] = 6.0, [6] = 95.0, [7] = 0,
})
add_dynamic_eq(lead, "lead_digital_fizz_dynamic", {
  [1] = 10400, [2] = 1.05, [3] = -45.0, [4] = 1.6, [5] = 8.0, [6] = 105.0, [7] = 0,
})
add_presence_tilt(lead, "lead_presence_tilt", {
  [1] = 2600, [2] = -0.08, [3] = 0.44,
})

add_channel_polish(lead_density, "lead_no_tune_parallel_mid_density", {
  [1] = 140, [2] = 190, [3] = -0.20, [4] = 480, [5] = -0.85, [6] = 0.85,
  [7] = 2700, [8] = -0.30, [9] = 0.90, [10] = 8200, [11] = -1.35,
  [12] = -32.0, [13] = 2.35, [14] = 16, [15] = 92, [16] = -0.25,
  [17] = 1.9, [18] = 0.12, [19] = 0.86, [20] = -1.2,
})
add_dynamic_eq(lead_density, "lead_density_harshness_control", {
  [1] = 3300, [2] = 1.0, [3] = -43.0, [4] = 1.6, [5] = 12.0, [6] = 125.0, [7] = 0,
})
add_dynamic_eq(lead_density, "lead_density_deess_control", {
  [1] = 7200, [2] = 1.15, [3] = -45.5, [4] = 1.8, [5] = 8.0, [6] = 130.0, [7] = 0,
})

add_channel_polish(lead_room, "lead_short_room_dark_blend", {
  [1] = 170, [2] = 220, [3] = -0.4, [4] = 520, [5] = -1.4, [6] = 0.9,
  [7] = 3300, [8] = -1.35, [9] = 1.0, [10] = 7200, [11] = -5.2,
  [12] = -34.0, [13] = 1.5, [14] = 22, [15] = 220, [16] = -0.8,
  [17] = 0.45, [18] = 0.035, [19] = 1.22, [20] = -1.0,
})
add_noise_tamer(lead_room, "lead_room_high_fizz_guard", {
  [1] = 6600, [2] = -54.0, [3] = 2.2, [4] = 18.0, [5] = 320.0, [6] = 0.72,
})

add_channel_polish(bass, "bass_saturation_texture", {
  [1] = 24, [2] = 58, [3] = 1.7, [4] = 230, [5] = -0.70, [6] = 0.8,
  [7] = 980, [8] = 0.58, [9] = 0.9, [10] = 7600, [11] = -0.25,
  [12] = -25.0, [13] = 1.34, [14] = 30, [15] = 250, [16] = 0.28,
  [17] = 3.7, [18] = 0.27, [19] = 0.72, [20] = -0.30,
})
add_dynamic_eq(bass, "bass_low_mid_control_after_sat", {
  [1] = 205, [2] = 0.9, [3] = -33.0, [4] = 1.45, [5] = 16.0, [6] = 220.0, [7] = 0,
})

add_channel_polish(drums, "drum_kick_saturation_punch", {
  [1] = 24, [2] = 64, [3] = 1.5, [4] = 285, [5] = -0.48, [6] = 0.85,
  [7] = 2200, [8] = 0.52, [9] = 0.85, [10] = 9800, [11] = -0.05,
  [12] = -22.6, [13] = 1.22, [14] = 22, [15] = 175, [16] = 0.18,
  [17] = 2.9, [18] = 0.21, [19] = 0.94, [20] = -0.20,
})
add_dynamic_eq(drums, "kick_body_transient_tighten", {
  [1] = 95, [2] = 1.0, [3] = -29.0, [4] = 0.9, [5] = 8.0, [6] = 120.0, [7] = 0,
})

add_channel_polish(synth, "synth_ai_edge_soften", {
  [1] = 42, [2] = 120, [3] = -0.10, [4] = 360, [5] = -0.48, [6] = 0.85,
  [7] = 2600, [8] = -0.82, [9] = 0.9, [10] = 8800, [11] = -1.22,
  [12] = -25.0, [13] = 1.18, [14] = 44, [15] = 250, [16] = -0.03,
  [17] = 0.42, [18] = 0.045, [19] = 1.0, [20] = 0.22,
})
add_dynamic_eq(synth, "synth_ai_presence_tame", {
  [1] = 3150, [2] = 1.05, [3] = -40.5, [4] = 2.4, [5] = 12.0, [6] = 190.0, [7] = 0,
})
add_dynamic_eq(synth, "synth_resonance_before_lift", {
  [1] = 1180, [2] = 0.95, [3] = -38.5, [4] = 1.55, [5] = 11.0, [6] = 175.0, [7] = 0,
})
add_noise_tamer(synth, "synth_top_tail_tamer", {
  [1] = 8200, [2] = -51.0, [3] = 1.4, [4] = 28.0, [5] = 280.0, [6] = 0.55,
})
add_ms_melody_tuck(synth, "synth_mseq_audible_buried", {
  [1] = 1650, [2] = -0.62, [3] = 1.05, [4] = 330, [5] = -0.26, [6] = 1.18, [7] = 0.38,
})
add_ms_melody_tuck(keyboard, "keyboard_mseq_audible_buried", {
  [1] = 1550, [2] = -0.40, [3] = 1.10, [4] = 330, [5] = -0.22, [6] = 1.18, [7] = 0.15,
})
add_ms_melody_tuck(woodwinds, "woodwinds_mseq_back_edge", {
  [1] = 1700, [2] = -0.55, [3] = 0.90, [4] = 360, [5] = -0.26, [6] = 1.16, [7] = 0.05,
})

add_channel_polish(vocal_bus, "vocal_bus_polish", {
  [1] = 82, [2] = 175, [3] = 0.05, [4] = 330, [5] = -0.45, [6] = 0.85,
  [7] = 3800, [8] = -0.10, [9] = 0.95, [10] = 10000, [11] = -0.25,
  [12] = -22.8, [13] = 1.35, [14] = 25, [15] = 175, [16] = -0.05,
  [17] = 0.55, [18] = 0.050, [19] = 0.97, [20] = -0.18,
})
add_dynamic_eq(vocal_bus, "vocal_bus_harshness_tame", {
  [1] = 4300, [2] = 1.0, [3] = -37.8, [4] = 1.6, [5] = 10.0, [6] = 135.0, [7] = 0,
})
add_dynamic_eq(vocal_bus, "vocal_bus_fizz_after_density", {
  [1] = 9300, [2] = 0.95, [3] = -44.0, [4] = 1.2, [5] = 12.0, [6] = 150.0, [7] = 0,
})

add_channel_polish(music_bus, "music_bus_polish", {
  [1] = 22, [2] = 76, [3] = 0.22, [4] = 290, [5] = -0.18, [6] = 0.75,
  [7] = 1700, [8] = -0.55, [9] = 0.9, [10] = 11200, [11] = -0.16,
  [12] = -22.0, [13] = 1.18, [14] = 40, [15] = 265, [16] = 0.12,
  [17] = 0.5, [18] = 0.055, [19] = 1.14, [20] = -0.02,
})
add_dynamic_eq(music_bus, "music_bus_vocal_space", {
  [1] = 2300, [2] = 0.9, [3] = -36.0, [4] = 1.25, [5] = 15.0, [6] = 190.0, [7] = 0,
})
add_noise_tamer(music_bus, "music_high_tail_tamer", {
  [1] = 8600, [2] = -51.0, [3] = 1.8, [4] = 20.0, [5] = 340.0, [6] = 0.68,
})

add_channel_polish(mix_bus, "mix_bus_polish", {
  [1] = 22, [2] = 78, [3] = 0.2, [4] = 310, [5] = -0.22, [6] = 0.95,
  [7] = 3300, [8] = -0.28, [9] = 1.0, [10] = 11600, [11] = -0.18,
  [12] = -19.8, [13] = 1.18, [14] = 34, [15] = 245, [16] = 0.12,
  [17] = 0.55, [18] = 0.055, [19] = 1.06, [20] = -0.05,
})
add_dynamic_eq(mix_bus, "mix_bus_low_mid_tighten", {
  [1] = 310, [2] = 0.95, [3] = -30.0, [4] = 1.35, [5] = 17.0, [6] = 230.0, [7] = 0,
})

add_master_glue(print_bus, {
  [1] = 23, [2] = 0.12, [3] = 70, [4] = -0.05, [5] = 300,
  [6] = -0.56, [7] = 3500, [8] = -0.30, [9] = 10400,
  [10] = -18.8, [11] = 1.14, [12] = 38, [13] = 215, [14] = 0.86,
  [15] = 1.45, [16] = -1.1, [17] = -0.12,
})
local horizon_idx = add_fx(print_bus, {
  "JS: Event Horizon Limiter/Clipper",
  "sstillwell/eventhorizon2",
}, "event_horizon_final_catch")
set_params(print_bus, horizon_idx, {
  [1] = -1.20,
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
reaper.Undo_EndBlock("Build Hangang Shadow v29 vocal AI artifact reduction", -1)
log("build done project=" .. project_path .. " render_end=" .. tostring(render_end))
