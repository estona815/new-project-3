-- Pass 03: beat-forward loud revision.
-- Starts from PASS02, lowers vocal dominance, brings the main beat/melody up,
-- and prepares a louder review master around the user's -6 LUFS request.

local root = "/Users/hantaeheuk/Documents/New project 3"
local pass_path = root .. "/reaper/FRESH_MIX_MASTER_PASS_03_BEAT_FORWARD_LOUD.rpp"
local log_path = "/tmp/codex_fresh_reaper/apply_pass03_beat_forward_loud.log"

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

local function set_track(track, db, pan, mute)
  if not track then return end
  if db ~= nil then reaper.SetMediaTrackInfo_Value(track, "D_VOL", lin(db)) end
  if pan ~= nil then reaper.SetMediaTrackInfo_Value(track, "D_PAN", pan) end
  if mute ~= nil then reaper.SetMediaTrackInfo_Value(track, "B_MUTE", mute and 1 or 0) end
end

local function set_named_track(name, db, pan, mute)
  local tr = find_track(name)
  if not tr then
    log("missing track: " .. tostring(name))
    return
  end
  set_track(tr, db, pan, mute)
  log("track " .. name .. " db=" .. tostring(db) .. " pan=" .. tostring(pan) .. " mute=" .. tostring(mute))
end

local function set_send_db(src_name, dest_name, db)
  local src = find_track(src_name)
  local dest = find_track(dest_name)
  if not src or not dest then
    log("send missing src=" .. tostring(src_name) .. " dest=" .. tostring(dest_name))
    return false
  end
  local dest_idx = get_track_index(dest)
  for i = 0, reaper.GetTrackNumSends(src, 0) - 1 do
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
      reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass03_fx_" .. label, add_name, true)
      log("added fx " .. tostring(add_name) .. " on " .. track_name(track))
      return idx
    end
  end
  reaper.GetSetMediaTrackInfo_String(track, "P_EXT:missing_pass03_fx_" .. label, table.concat(add_names, " | "), true)
  log("missing fx any " .. table.concat(add_names, " | ") .. " on " .. track_name(track))
  return -1
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

local function select_only_track(track)
  reaper.Main_OnCommand(40297, 0)
  reaper.SetTrackSelected(track, true)
end

local function ensure_volume_envelope(track)
  if not track then return nil end
  local env = reaper.GetTrackEnvelopeByName(track, "Volume")
  if env then return env end
  select_only_track(track)
  reaper.Main_OnCommand(40406, 0)
  return reaper.GetTrackEnvelopeByName(track, "Volume")
end

local function write_music_presence_envelope()
  local track = find_track("MUSIC_BUS")
  local env = ensure_volume_envelope(track)
  if not env then return end
  reaper.DeleteEnvelopePointRange(env, 0.0, 160.0)
  local base = lin(0.8)
  local under_vocal = lin(0.2)
  local segments = {
    {4.0, 35.6},
    {59.8, 79.4},
    {89.7, 103.7},
  }
  reaper.InsertEnvelopePoint(env, 0.0, base, 0, 0, false, true)
  reaper.InsertEnvelopePoint(env, 160.0, base, 0, 0, false, true)
  for _, seg in ipairs(segments) do
    local s = seg[1]
    local e = seg[2]
    reaper.InsertEnvelopePoint(env, math.max(0, s - 0.20), base, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, s, under_vocal, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, e, under_vocal, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, e + 0.25, base, 0, 0, false, true)
  end
  reaper.Envelope_SortPoints(env)
  if track then
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass03_music_presence", "Music envelope nearly removes PASS02 ducking: +0.8 dB baseline, +0.2 dB under vocals so the beat melody stays present.", true)
  end
end

local function write_vocal_fx_tuck_envelope()
  local track = find_track("VOCAL_FX_BUS")
  local env = ensure_volume_envelope(track)
  if not env then return end
  reaper.DeleteEnvelopePointRange(env, 0.0, 160.0)
  local base = lin(-1.2)
  local dense = lin(-2.4)
  local segments = {
    {4.0, 35.6},
    {59.8, 79.4},
    {89.7, 103.7},
  }
  reaper.InsertEnvelopePoint(env, 0.0, base, 0, 0, false, true)
  reaper.InsertEnvelopePoint(env, 160.0, base, 0, 0, false, true)
  for _, seg in ipairs(segments) do
    local s = seg[1]
    local e = seg[2]
    reaper.InsertEnvelopePoint(env, math.max(0, s - 0.20), base, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, s, dense, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, e, dense, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, e + 0.25, base, 0, 0, false, true)
  end
  reaper.Envelope_SortPoints(env)
end

local function write_delay_throw_tuck()
  local track = find_track("VOCAL_DELAY_SEND")
  local env = ensure_volume_envelope(track)
  if not env then return end
  reaper.DeleteEnvelopePointRange(env, 0.0, 160.0)
  local base = lin(-5.0)
  local throw = lin(-1.0)
  local throw_times = {4.587, 5.995, 18.240, 21.845, 24.064, 28.395, 34.197, 60.992, 69.355, 72.320, 77.440, 90.859, 92.779, 101.248}
  reaper.InsertEnvelopePoint(env, 0.0, base, 0, 0, false, true)
  reaper.InsertEnvelopePoint(env, 160.0, base, 0, 0, false, true)
  for _, t in ipairs(throw_times) do
    reaper.InsertEnvelopePoint(env, math.max(0, t - 0.20), base, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, t - 0.03, throw, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, t + 0.28, throw, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, t + 0.54, base, 0, 0, false, true)
  end
  reaper.Envelope_SortPoints(env)
end

local function add_marker_once(time, name)
  local _, markers, regions = reaper.CountProjectMarkers(0)
  local total = markers + regions
  for i = 0, total - 1 do
    local _, is_region, pos, _, marker_name = reaper.EnumProjectMarkers(i)
    if not is_region and math.abs((pos or 0) - time) < 0.001 and marker_name == name then return end
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

log("apply pass03 start")
reaper.Undo_BeginBlock()

-- Keep safety/mute rules intact.
set_named_track("REF_BUS", nil, nil, true)
set_named_track("ARTIFACT_QUARANTINE_BUS", nil, nil, true)
set_named_track("00_REF_Full_Mix", -18.0, 0.0, true)
set_named_track("1 Instrumental", -18.0, 0.0, true)
set_named_track("PROBLEM REF - hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_24-48", -18.0, 0.0, true)
set_named_track("PROBLEM REF - hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_320k", -18.0, 0.0, true)
set_named_track("TECH REF - 동반자살 WAV", -18.0, 0.0, true)
set_named_track("QUARANTINE - 03_FX", -24.0, 0.0, true)
set_named_track("QUARANTINE - 08_Guitar", -24.0, 0.0, true)
set_named_track("Female BGV L - 0 Lead Vocals", -42.0, -0.40, true)
set_named_track("Female BGV L - female_vocal_candidate_clean", -42.0, -0.35, true)
for i = 0, reaper.CountTracks(0) - 1 do
  local tr = reaper.GetTrack(0, i)
  if string.find(track_name(tr), "Guide MIDI", 1, true) then set_track(tr, -18.0, 0.0, true) end
end

-- Requested revision: less vocal dominance, more beat/main melody.
set_named_track("12_Vocals", -5.8, 0.0, false)
set_named_track("MALE_LEAD_VOX_BUS", 0.2, 0.0, false)
set_named_track("Female BGV R - 11_Backing_Vocals", -30.0, 0.38, false)
set_named_track("FEMALE_BGV_BUS", -8.5, 0.0, false)

set_named_track("04_Synth", -11.8, 0.0, false)
set_named_track("07_Keyboard", -12.2, 0.0, false)
set_named_track("01_Woodwinds", -13.4, -0.05, false)
set_named_track("05_Strings", -13.8, 0.0, false)
set_named_track("02_Brass", -14.0, 0.05, false)
set_named_track("MUSIC_BUS", 1.6, 0.0, false)

set_named_track("10_Drums", -10.0, 0.0, false)
set_named_track("06_Percussion", -12.4, 0.0, false)
set_named_track("DRUM_BUS", -0.6, 0.0, false)
set_named_track("09_Bass", -11.6, 0.0, false)
set_named_track("BASS_808_BUS", -1.2, 0.0, false)
set_named_track("MIX_BUS", 0.0, 0.0, false)
set_named_track("MASTER_PREMIX_BUS", 0.0, 0.0, false)

set_named_track("VOCAL_PLATE_SEND", -8.0, 0.0, false)
set_named_track("VOCAL_DELAY_SEND", -12.5, 0.0, false)
set_named_track("SHORT_ROOM_SEND", -15.0, 0.0, false)
set_named_track("VOCAL_FX_BUS", -8.8, 0.0, false)

set_send_db("12_Vocals", "VOCAL_PLATE_SEND", -25.0)
set_send_db("12_Vocals", "VOCAL_DELAY_SEND", -31.0)
set_send_db("12_Vocals", "SHORT_ROOM_SEND", -38.0)
set_send_db("Female BGV R - 11_Backing_Vocals", "VOCAL_PLATE_SEND", -20.0)
set_send_db("Female BGV R - 11_Backing_Vocals", "SHORT_ROOM_SEND", -24.0)

write_music_presence_envelope()
write_vocal_fx_tuck_envelope()
write_delay_throw_tuck()

-- Loud review master. This is intentionally more aggressive than PASS02.
local print_bus = find_track("PRINT_MASTER_BUS")
local horizon_idx = ensure_fx_any(print_bus, {"event horizon", "eventhorizon"}, {"JS: Event Horizon Limiter/Clipper", "sstillwell/eventhorizon2"}, "print_master_event_horizon_limiter")
if print_bus and horizon_idx >= 0 then
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 0, -21.8)
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 1, -1.0)
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 2, 360.0)
  reaper.GetSetMediaTrackInfo_String(print_bus, "P_EXT:pass03_event_horizon_settings", "Threshold -21.8 dB, ceiling -1 dB, release 360 ms. Aggressive -6 LUFS review target; reject if pumping/distortion is audible.", true)
end
ensure_fx_any(print_bus, {"realimit"}, {"ReaLimit"}, "print_master_safety_limiter")
ensure_fx_any(print_bus, {"loudness"}, {"JS: Loudness Meter Peak/RMS/LUFS"}, "print_master_meter")

add_marker_once(0.0, "PASS03: beat-forward loud review pass")
add_marker_once(15.68, "PASS03 CHECK: vocal lower, beat should dominate without burying lyric")
add_marker_once(60.0, "PASS03 CHECK: hook melody/beat forward")

local positions_ok = validate_items_start_zero()
local render_end = max_active_item_end() + 4.0
if reaper.GetSetProjectInfo then
  reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
  reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 0, true)
  reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0.0, true)
  reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", render_end, true)
end
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", root .. "/renders", true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "PASS03_MASTER_BEAT_FORWARD_LOUD_24bit_48k", true)
reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", "PASS03 beat-forward loud revision. Vocal lowered, main melody stems raised, music ducking relaxed, master pushed toward -6 LUFS review target. References/quarantine remain muted.", true)

reaper.UpdateArrange()
if reaper.Main_SaveProjectEx then
  reaper.Main_SaveProjectEx(0, pass_path, 0)
end
reaper.Undo_EndBlock("Apply pass 03 beat-forward loud revision", -1)
log("apply pass03 done positions_ok=" .. tostring(positions_ok) .. " render_end=" .. tostring(render_end))
