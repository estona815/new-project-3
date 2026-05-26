-- Fresh mix/master pass 01 chain application.
-- Run after opening reaper/FRESH_MIX_REBUILD.rpp. Saves a progressed copy as
-- reaper/FRESH_MIX_MASTER_PASS_01.rpp without rebuilding or reimporting stems.

local root = "/Users/hantaeheuk/Documents/New project 3"
local pass_path = root .. "/reaper/FRESH_MIX_MASTER_PASS_01.rpp"
local log_path = "/tmp/codex_fresh_reaper/apply_fresh_mix_chains.log"

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

local function track_name(track)
  local _, name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
  return name or ""
end

local function find_track(name)
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    if track_name(tr) == name then return tr end
  end
  return nil
end

local function get_track_index(track)
  if not track then return -1 end
  local idx = reaper.GetMediaTrackInfo_Value(track, "IP_TRACKNUMBER")
  return math.floor(idx or -1) - 1
end

local function ensure_fx(track, search, add_name, label)
  if not track then return -1 end
  for i = 0, reaper.TrackFX_GetCount(track) - 1 do
    local _, fx_name = reaper.TrackFX_GetFXName(track, i, "")
    if string.find(string.lower(fx_name or ""), string.lower(search), 1, true) then
      return i
    end
  end
  local idx = reaper.TrackFX_AddByName(track, add_name, false, -1)
  if idx < 0 then
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:missing_fx_" .. label, add_name, true)
    log("missing fx " .. tostring(add_name) .. " on " .. track_name(track))
  else
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass01_fx_" .. label, add_name, true)
    log("added fx " .. tostring(add_name) .. " on " .. track_name(track))
  end
  return idx
end

local function ensure_fx_any(track, searches, add_names, label)
  if not track then return -1 end
  for _, search in ipairs(searches) do
    for i = 0, reaper.TrackFX_GetCount(track) - 1 do
      local _, fx_name = reaper.TrackFX_GetFXName(track, i, "")
      if string.find(string.lower(fx_name or ""), string.lower(search), 1, true) then
        return i
      end
    end
  end
  for _, add_name in ipairs(add_names) do
    local idx = reaper.TrackFX_AddByName(track, add_name, false, -1)
    if idx >= 0 then
      reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass01_fx_" .. label, add_name, true)
      log("added fx " .. tostring(add_name) .. " on " .. track_name(track))
      return idx
    end
  end
  reaper.GetSetMediaTrackInfo_String(track, "P_EXT:missing_fx_" .. label, table.concat(add_names, " | "), true)
  log("missing fx any " .. table.concat(add_names, " | ") .. " on " .. track_name(track))
  return -1
end

local function set_track(track, db, pan, mute)
  if not track then return end
  if db ~= nil then reaper.SetMediaTrackInfo_Value(track, "D_VOL", lin(db)) end
  if pan ~= nil then reaper.SetMediaTrackInfo_Value(track, "D_PAN", pan) end
  if mute ~= nil then reaper.SetMediaTrackInfo_Value(track, "B_MUTE", mute and 1 or 0) end
end

local function set_named_track(name, db, pan, mute)
  set_track(find_track(name), db, pan, mute)
end

local function set_send_db(src_name, dest_name, db)
  local src = find_track(src_name)
  local dest = find_track(dest_name)
  if not src or not dest then
    log("send missing src=" .. tostring(src_name) .. " dest=" .. tostring(dest_name))
    return false
  end
  local dest_idx = get_track_index(dest)
  local count = reaper.GetTrackNumSends(src, 0)
  for i = 0, count - 1 do
    local maybe_dest = reaper.GetTrackSendInfo_Value(src, 0, i, "P_DESTTRACK")
    if maybe_dest == dest or (type(maybe_dest) == "userdata" and get_track_index(maybe_dest) == dest_idx) then
      reaper.SetTrackSendInfo_Value(src, 0, i, "D_VOL", lin(db))
      log("send " .. src_name .. " -> " .. dest_name .. " = " .. tostring(db) .. " dB")
      return true
    end
  end
  log("send not found src=" .. tostring(src_name) .. " dest=" .. tostring(dest_name))
  return false
end

local function validate_items_start_zero()
  local ok = true
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    local name = track_name(tr)
    for j = 0, reaper.CountTrackMediaItems(tr) - 1 do
      local item = reaper.GetTrackMediaItem(tr, j)
      local pos = reaper.GetMediaItemInfo_Value(item, "D_POSITION")
      if math.abs(pos) > 0.0001 then
        ok = false
        log("nonzero item position track=" .. name .. " pos=" .. tostring(pos))
      end
    end
  end
  return ok
end

local function add_marker_once(time, name)
  local _, markers, regions = reaper.CountProjectMarkers(0)
  local total = markers + regions
  for i = 0, total - 1 do
    local _, is_region, pos, _, marker_name = reaper.EnumProjectMarkers(i)
    if not is_region and math.abs((pos or 0) - time) < 0.001 and marker_name == name then
      return
    end
  end
  reaper.AddProjectMarker(0, false, time, time, name, -1)
end

local function max_active_item_end()
  local max_end = 0.0
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

local function soften_item_edges()
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    for j = 0, reaper.CountTrackMediaItems(tr) - 1 do
      local item = reaper.GetTrackMediaItem(tr, j)
      reaper.SetMediaItemInfo_Value(item, "D_FADEINLEN", 0.005)
      reaper.SetMediaItemInfo_Value(item, "D_FADEOUTLEN", 0.020)
    end
  end
end

log("apply pass01 start")
reaper.Undo_BeginBlock()

if reaper.GetSetProjectInfo then
  reaper.GetSetProjectInfo(0, "PROJECT_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "PROJECT_SRATE_USE", 1, true)
end

-- Keep references, guide placeholders, and artifact quarantine safely muted.
set_named_track("REF_BUS", nil, nil, true)
set_named_track("ARTIFACT_QUARANTINE_BUS", nil, nil, true)
set_named_track("00_REF_Full_Mix", -18.0, 0.0, true)
set_named_track("1 Instrumental", -18.0, 0.0, true)
set_named_track("PROBLEM REF - hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_24-48", -18.0, 0.0, true)
set_named_track("PROBLEM REF - hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_320k", -18.0, 0.0, true)
set_named_track("TECH REF - 동반자살 WAV", -18.0, 0.0, true)
set_named_track("QUARANTINE - 03_FX", -24.0, 0.0, true)
set_named_track("QUARANTINE - 08_Guitar", -24.0, 0.0, true)
for i = 0, reaper.CountTracks(0) - 1 do
  local tr = reaper.GetTrack(0, i)
  local name = track_name(tr)
  if string.find(name, "Guide MIDI", 1, true) then set_track(tr, -18.0, 0.0, true) end
end

-- Vocal-forward, conservative starting balance.
set_named_track("12_Vocals", -5.2, 0.0, false)
set_named_track("Female BGV R - 11_Backing_Vocals", -22.5, 0.40, false)
set_named_track("Female BGV L - 0 Lead Vocals", -24.0, -0.40, false)
set_named_track("Female BGV L - female_vocal_candidate_clean", -25.5, -0.35, false)
set_named_track("10_Drums", -10.5, 0.0, false)
set_named_track("06_Percussion", -12.5, 0.0, false)
set_named_track("09_Bass", -11.5, 0.0, false)
set_named_track("01_Woodwinds", -15.0, -0.05, false)
set_named_track("02_Brass", -15.5, 0.05, false)
set_named_track("04_Synth", -14.2, 0.0, false)
set_named_track("05_Strings", -15.0, 0.0, false)
set_named_track("07_Keyboard", -14.8, 0.0, false)

set_named_track("DRUM_BUS", -0.8, 0.0, false)
set_named_track("BASS_808_BUS", -1.2, 0.0, false)
set_named_track("MUSIC_BUS", -2.6, 0.0, false)
set_named_track("MALE_LEAD_VOX_BUS", 0.8, 0.0, false)
set_named_track("FEMALE_BGV_BUS", -3.2, 0.0, false)
set_named_track("VOCAL_FX_BUS", -6.5, 0.0, false)
set_named_track("FX_BUS", -7.0, 0.0, false)
set_named_track("MIX_BUS", -1.5, 0.0, false)
set_named_track("MASTER_PREMIX_BUS", -0.7, 0.0, false)
set_named_track("PRINT_MASTER_BUS", 0.0, 0.0, false)
set_named_track("VOCAL_PLATE_SEND", -4.5, 0.0, false)
set_named_track("VOCAL_DELAY_SEND", -8.5, 0.0, false)
set_named_track("SHORT_ROOM_SEND", -12.0, 0.0, false)
set_named_track("OPTIONAL_WIDE_THROW_SEND", -18.0, 0.0, false)

-- Send-based ambience: keep the lead close, use throws/markers for manual automation.
set_send_db("12_Vocals", "VOCAL_PLATE_SEND", -20.0)
set_send_db("12_Vocals", "VOCAL_DELAY_SEND", -24.0)
set_send_db("12_Vocals", "SHORT_ROOM_SEND", -31.0)
set_send_db("Female BGV R - 11_Backing_Vocals", "VOCAL_PLATE_SEND", -23.0)
set_send_db("Female BGV R - 11_Backing_Vocals", "SHORT_ROOM_SEND", -26.0)
set_send_db("Female BGV L - 0 Lead Vocals", "VOCAL_PLATE_SEND", -24.0)
set_send_db("Female BGV L - 0 Lead Vocals", "SHORT_ROOM_SEND", -27.0)
set_send_db("Female BGV L - female_vocal_candidate_clean", "VOCAL_PLATE_SEND", -26.0)
set_send_db("Female BGV L - female_vocal_candidate_clean", "SHORT_ROOM_SEND", -29.0)

-- Stock/fallback chain anchors. Parameter-specific surgical moves remain manual notes.
ensure_fx(find_track("MALE_LEAD_VOX_BUS"), "reaeq", "ReaEQ", "lead_bus_cleanup_tone_eq")
ensure_fx(find_track("MALE_LEAD_VOX_BUS"), "reaxcomp", "ReaXcomp", "lead_bus_dynamic_eq_deess")
ensure_fx(find_track("MALE_LEAD_VOX_BUS"), "reacomp", "ReaComp", "lead_bus_serial_leveling")
ensure_fx(find_track("MALE_LEAD_VOX_BUS"), "saturation", "JS: Saturation", "lead_bus_light_saturation")
ensure_fx(find_track("FEMALE_BGV_BUS"), "reaeq", "ReaEQ", "bgv_bus_hpf_soften_eq")
ensure_fx(find_track("FEMALE_BGV_BUS"), "reaxcomp", "ReaXcomp", "bgv_bus_deess_control")
ensure_fx(find_track("FEMALE_BGV_BUS"), "reacomp", "ReaComp", "bgv_bus_smooth_compression")
ensure_fx(find_track("FEMALE_BGV_BUS"), "stereowidth", "JS: Stereo Width", "bgv_bus_width_control")
ensure_fx(find_track("DRUM_BUS"), "reaeq", "ReaEQ", "drum_bus_hat_tone_eq")
ensure_fx(find_track("DRUM_BUS"), "reacomp", "ReaComp", "drum_bus_punch_glue")
ensure_fx(find_track("BASS_808_BUS"), "reaeq", "ReaEQ", "bass_bus_mono_low_mud_eq")
ensure_fx(find_track("BASS_808_BUS"), "reaxcomp", "ReaXcomp", "bass_bus_dynamic_control")
ensure_fx(find_track("MUSIC_BUS"), "reaeq", "ReaEQ", "music_bus_vocal_pocket_eq")
ensure_fx(find_track("MUSIC_BUS"), "reaxcomp", "ReaXcomp", "music_bus_masking_dynamic_control")
ensure_fx(find_track("MUSIC_BUS"), "stereowidth", "JS: Stereo Width", "music_bus_width_control")
ensure_fx(find_track("VOCAL_FX_BUS"), "reaeq", "ReaEQ", "vocal_fx_return_filter_eq")
ensure_fx(find_track("VOCAL_FX_BUS"), "reacomp", "ReaComp", "vocal_fx_ducking_placeholder")
ensure_fx(find_track("VOCAL_PLATE_SEND"), "reaverbate", "ReaVerbate", "plate_return")
ensure_fx(find_track("VOCAL_PLATE_SEND"), "reaeq", "ReaEQ", "plate_return_filter")
ensure_fx(find_track("VOCAL_DELAY_SEND"), "readelay", "ReaDelay", "delay_return")
ensure_fx(find_track("VOCAL_DELAY_SEND"), "reaeq", "ReaEQ", "delay_return_filter")
ensure_fx(find_track("SHORT_ROOM_SEND"), "reaverbate", "ReaVerbate", "short_room_return")
ensure_fx(find_track("SHORT_ROOM_SEND"), "reaeq", "ReaEQ", "short_room_return_filter")
ensure_fx(find_track("MIX_BUS"), "reaxcomp", "ReaXcomp", "mix_bus_dynamic_control")
ensure_fx(find_track("MIX_BUS"), "reaeq", "ReaEQ", "mix_bus_ms_or_tone_eq")
ensure_fx(find_track("MASTER_PREMIX_BUS"), "reacomp", "ReaComp", "master_premix_light_glue")
local print_bus = find_track("PRINT_MASTER_BUS")
local horizon_idx = ensure_fx_any(print_bus, {"event horizon", "eventhorizon"}, {"JS: Event Horizon Limiter/Clipper", "sstillwell/eventhorizon2"}, "print_master_event_horizon_limiter")
if print_bus and horizon_idx >= 0 then
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 0, -16.0)
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 1, -1.0)
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 2, 250.0)
  reaper.GetSetMediaTrackInfo_String(print_bus, "P_EXT:pass01_event_horizon_settings", "Threshold -16 dB, ceiling -1 dB, release 250 ms. Used as stock short-form pop loudness stage; verify by ear for pumping.", true)
end
ensure_fx(find_track("PRINT_MASTER_BUS"), "realimit", "ReaLimit", "print_master_safety_limiter")
ensure_fx(find_track("PRINT_MASTER_BUS"), "loudness", "JS: Loudness Meter Peak/RMS/LUFS", "print_master_meter")

-- Save manual intent on tracks so plugin claims stay honest.
local lead_bus = find_track("MALE_LEAD_VOX_BUS")
if lead_bus then
  reaper.GetSetMediaTrackInfo_String(lead_bus, "P_EXT:pass01_tuning_status", "ReaTune fallback present/anchored; key uncertain, manual pitch correction still required for unstable sections.", true)
  reaper.GetSetMediaTrackInfo_String(lead_bus, "P_EXT:pass01_dynamic_eq_intent", "Control 180-350 Hz mud, 3-5 kHz harshness, and 5.5-9 kHz sibilance using ReaXcomp or manual plugin upgrade.", true)
end

soften_item_edges()
local positions_ok = validate_items_start_zero()

add_marker_once(15.68, "LEAD REPAIR: check abrupt cut / pitch stability")
add_marker_once(38.64, "LEAD REPAIR: check energy spike / harsh consonant")
local throw_times = {4.587, 5.995, 18.240, 21.845, 24.064, 28.395, 34.197, 60.992, 69.355, 72.320, 77.440, 90.859, 92.779, 101.248}
for _, t in ipairs(throw_times) do
  add_marker_once(t, "DELAY THROW CANDIDATE: phrase end")
end

local render_end = max_active_item_end() + 4.0
if reaper.GetSetProjectInfo then
  reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
  reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 0, true)
  reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0.0, true)
  reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", render_end, true)
end

reaper.GetSetProjectInfo_String(0, "RENDER_FILE", root .. "/renders", true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "FRESH_MASTER_24bit_48k", true)
reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", "Fresh mix/master pass 01 applied by Codex. References and quarantine muted. Guide MIDI placeholders remain muted. Lead vocal centered/dominant; female BGV support only. Stock fallback plugins anchored; manual tuning and exact dynamic EQ parameters still require human review.", true)

reaper.UpdateArrange()
if reaper.Main_SaveProjectEx then
  reaper.Main_SaveProjectEx(0, pass_path, 0)
end
reaper.Undo_EndBlock("Apply fresh mix/master pass 01", -1)
log("apply pass01 done positions_ok=" .. tostring(positions_ok) .. " render_end=" .. tostring(render_end))
