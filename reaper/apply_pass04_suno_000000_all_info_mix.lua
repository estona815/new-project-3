-- Pass 04: all-info mix/master pass with Suno 000000 stem candidate archived.
-- Starts from PASS03. The new Suno 000000 stems are imported muted because
-- they are a 39.92s candidate, not a full-length aligned replacement vocal.

local root = "/Users/hantaeheuk/Documents/New project 3"
local pass_path = root .. "/reaper/FRESH_MIX_MASTER_PASS_04_SUNO_000000_ALL_INFO.rpp"
local log_path = "/tmp/codex_fresh_reaper/apply_pass04_suno_000000_all_info_mix.log"

local suno_stems = {
  {name = "SUNO000000 CANDIDATE - Lead Vocals", path = root .. "/downloads/suno_pass04/stems/0 Lead Vocals.wav", db = -18.0, pan = 0.0},
  {name = "SUNO000000 CANDIDATE - Drums", path = root .. "/downloads/suno_pass04/stems/1 Drums.wav", db = -18.0, pan = 0.0},
  {name = "SUNO000000 CANDIDATE - Bass", path = root .. "/downloads/suno_pass04/stems/2 Bass.wav", db = -18.0, pan = 0.0},
  {name = "SUNO000000 CANDIDATE - Synth", path = root .. "/downloads/suno_pass04/stems/3 Synth.wav", db = -18.0, pan = 0.0},
  {name = "SUNO000000 CANDIDATE - Other", path = root .. "/downloads/suno_pass04/stems/4 Other.wav", db = -18.0, pan = 0.0},
}

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

local function ensure_track(name, db, pan, mute)
  local tr = find_track(name)
  if tr then
    set_track(tr, db, pan, mute)
    return tr
  end
  reaper.InsertTrackAtIndex(reaper.CountTracks(0), true)
  tr = reaper.GetTrack(0, reaper.CountTracks(0) - 1)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", name, true)
  set_track(tr, db, pan, mute)
  log("created track " .. name)
  return tr
end

local function ensure_send_db(src, dest, db)
  if not src or not dest then return false end
  local dest_idx = get_track_index(dest)
  for i = 0, reaper.GetTrackNumSends(src, 0) - 1 do
    local maybe_dest = reaper.GetTrackSendInfo_Value(src, 0, i, "P_DESTTRACK")
    if maybe_dest == dest or (type(maybe_dest) == "userdata" and get_track_index(maybe_dest) == dest_idx) then
      reaper.SetTrackSendInfo_Value(src, 0, i, "D_VOL", lin(db))
      return true
    end
  end
  local send_idx = reaper.CreateTrackSend(src, dest)
  if send_idx >= 0 then
    reaper.SetTrackSendInfo_Value(src, 0, send_idx, "D_VOL", lin(db))
    return true
  end
  return false
end

local function set_send_db(src_name, dest_name, db)
  local src = find_track(src_name)
  local dest = find_track(dest_name)
  if ensure_send_db(src, dest, db) then
    log("send " .. src_name .. " -> " .. dest_name .. " = " .. tostring(db) .. " dB")
  else
    log("send missing src=" .. tostring(src_name) .. " dest=" .. tostring(dest_name))
  end
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
      reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass04_fx_" .. label, add_name, true)
      log("added fx " .. tostring(add_name) .. " on " .. track_name(track))
      return idx
    end
  end
  reaper.GetSetMediaTrackInfo_String(track, "P_EXT:missing_pass04_fx_" .. label, table.concat(add_names, " | "), true)
  log("missing fx any " .. table.concat(add_names, " | ") .. " on " .. track_name(track))
  return -1
end

local function add_media_item(track, file_path)
  if not track or reaper.CountTrackMediaItems(track) > 0 then return end
  local source = reaper.PCM_Source_CreateFromFile(file_path)
  if not source then
    log("media source failed: " .. tostring(file_path))
    return
  end
  local length = reaper.GetMediaSourceLength(source)
  local item = reaper.AddMediaItemToTrack(track)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, source)
  reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0.0)
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", length)
  reaper.SetMediaItemInfo_Value(item, "B_MUTE", 0)
  reaper.GetSetMediaItemTakeInfo_String(take, "P_NAME", file_path:match("([^/]+)$") or file_path, true)
  log("imported media " .. tostring(file_path) .. " length=" .. tostring(length))
end

local function import_suno_candidate_stems()
  local bus = ensure_track("SUNO_000000_CANDIDATE_BUS", -18.0, 0.0, true)
  reaper.SetMediaTrackInfo_Value(bus, "B_MAINSEND", 0)
  local mix_bus = find_track("MIX_BUS")
  if mix_bus then ensure_send_db(bus, mix_bus, 0.0) end
  reaper.GetSetMediaTrackInfo_String(bus, "P_EXT:pass04_candidate_note", "Muted by default. 000000 Suno stems are a 39.92s candidate with incomplete/garbled Korean lyric capture; audition only, not active production replacement.", true)

  for _, stem in ipairs(suno_stems) do
    local tr = ensure_track(stem.name, stem.db, stem.pan, true)
    reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0)
    ensure_send_db(tr, bus, 0.0)
    add_media_item(tr, stem.path)
    reaper.GetSetMediaTrackInfo_String(tr, "P_EXT:source_class", "suno_000000_candidate_muted", true)
    reaper.GetSetMediaTrackInfo_String(tr, "P_EXT:pass04_candidate_note", "Generated with selected Suno voice 000000 and downloaded as all detected WAV stems. Muted because duration/lyrics/timing are not a full replacement for the main production.", true)
  end
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
  reaper.DeleteEnvelopePointRange(env, 0.0, 170.0)
  local base = lin(1.2)
  local under_vocal = lin(0.45)
  local open_hook = lin(1.7)
  local segments = {
    {4.0, 35.6},
    {59.8, 79.4},
    {89.7, 103.7},
  }
  reaper.InsertEnvelopePoint(env, 0.0, base, 0, 0, false, true)
  reaper.InsertEnvelopePoint(env, 170.0, base, 0, 0, false, true)
  for _, seg in ipairs(segments) do
    local s = seg[1]
    local e = seg[2]
    reaper.InsertEnvelopePoint(env, math.max(0, s - 0.20), base, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, s, under_vocal, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, e, under_vocal, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, e + 0.25, open_hook, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, e + 3.00, base, 0, 0, false, true)
  end
  reaper.Envelope_SortPoints(env)
  if track then
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass04_music_presence", "Beat-forward automation: +1.2 dB baseline, +0.45 dB under vocals, short +1.7 dB lift after dense vocal phrases.", true)
  end
end

local function write_vocal_fx_tuck_envelope()
  local track = find_track("VOCAL_FX_BUS")
  local env = ensure_volume_envelope(track)
  if not env then return end
  reaper.DeleteEnvelopePointRange(env, 0.0, 170.0)
  local base = lin(-1.8)
  local dense = lin(-3.0)
  local segments = {
    {4.0, 35.6},
    {59.8, 79.4},
    {89.7, 103.7},
  }
  reaper.InsertEnvelopePoint(env, 0.0, base, 0, 0, false, true)
  reaper.InsertEnvelopePoint(env, 170.0, base, 0, 0, false, true)
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
  reaper.DeleteEnvelopePointRange(env, 0.0, 170.0)
  local base = lin(-5.8)
  local throw = lin(-1.5)
  local throw_times = {4.587, 5.995, 18.240, 21.845, 24.064, 28.395, 34.197, 60.992, 69.355, 72.320, 77.440, 90.859, 92.779, 101.248}
  reaper.InsertEnvelopePoint(env, 0.0, base, 0, 0, false, true)
  reaper.InsertEnvelopePoint(env, 170.0, base, 0, 0, false, true)
  for _, t in ipairs(throw_times) do
    reaper.InsertEnvelopePoint(env, math.max(0, t - 0.20), base, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, t - 0.03, throw, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, t + 0.24, throw, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, t + 0.48, base, 0, 0, false, true)
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

log("apply pass04 start")
reaper.Undo_BeginBlock()

import_suno_candidate_stems()

-- Keep safety/mute rules intact.
set_named_track("REF_BUS", nil, nil, true)
set_named_track("ARTIFACT_QUARANTINE_BUS", nil, nil, true)
set_named_track("SUNO_000000_CANDIDATE_BUS", -18.0, 0.0, true)
for _, stem in ipairs(suno_stems) do
  set_named_track(stem.name, stem.db, stem.pan, true)
end
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

-- User direction: beat/main melody should be more obvious and vocal should sit lower.
set_named_track("12_Vocals", -6.7, 0.0, false)
set_named_track("MALE_LEAD_VOX_BUS", -0.4, 0.0, false)
set_named_track("Female BGV R - 11_Backing_Vocals", -31.5, 0.38, false)
set_named_track("FEMALE_BGV_BUS", -9.5, 0.0, false)

set_named_track("04_Synth", -11.0, 0.0, false)
set_named_track("07_Keyboard", -11.5, 0.0, false)
set_named_track("01_Woodwinds", -12.9, -0.05, false)
set_named_track("05_Strings", -13.2, 0.0, false)
set_named_track("02_Brass", -13.6, 0.05, false)
set_named_track("MUSIC_BUS", 1.9, 0.0, false)

set_named_track("10_Drums", -9.6, 0.0, false)
set_named_track("06_Percussion", -12.0, 0.0, false)
set_named_track("DRUM_BUS", -0.4, 0.0, false)
set_named_track("09_Bass", -11.4, 0.0, false)
set_named_track("BASS_808_BUS", -1.0, 0.0, false)
set_named_track("MIX_BUS", 0.0, 0.0, false)
set_named_track("MASTER_PREMIX_BUS", 0.0, 0.0, false)

set_named_track("VOCAL_PLATE_SEND", -9.0, 0.0, false)
set_named_track("VOCAL_DELAY_SEND", -13.5, 0.0, false)
set_named_track("SHORT_ROOM_SEND", -16.0, 0.0, false)
set_named_track("VOCAL_FX_BUS", -9.5, 0.0, false)

set_send_db("12_Vocals", "VOCAL_PLATE_SEND", -26.0)
set_send_db("12_Vocals", "VOCAL_DELAY_SEND", -32.0)
set_send_db("12_Vocals", "SHORT_ROOM_SEND", -39.0)
set_send_db("Female BGV R - 11_Backing_Vocals", "VOCAL_PLATE_SEND", -21.0)
set_send_db("Female BGV R - 11_Backing_Vocals", "SHORT_ROOM_SEND", -25.0)

write_music_presence_envelope()
write_vocal_fx_tuck_envelope()
write_delay_throw_tuck()

local lead_bus = find_track("MALE_LEAD_VOX_BUS")
if lead_bus then
  reaper.GetSetMediaTrackInfo_String(lead_bus, "P_EXT:pass04_dynamic_eq_intent", "Lead lowered slightly; dynamic EQ remains focused on 260 Hz mud, 950 Hz nasal tone, 3.8 kHz harshness, and 7.2 kHz sibilance so the lower level still reads clearly.", true)
end
local music_bus = find_track("MUSIC_BUS")
if music_bus then
  reaper.GetSetMediaTrackInfo_String(music_bus, "P_EXT:pass04_dynamic_eq_intent", "Music is louder, but existing dynamic bands should keep 2.2 kHz and 4.2 kHz from masking the vocal. Manual ear check required.", true)
end
local bass_bus = find_track("BASS_808_BUS")
if bass_bus then
  reaper.GetSetMediaTrackInfo_String(bass_bus, "P_EXT:pass04_dynamic_eq_intent", "Bass kept mono/controlled. Existing 180 Hz and 280 Hz dynamic controls remain active to reduce mud while keeping beat weight.", true)
end

local print_bus = find_track("PRINT_MASTER_BUS")
local horizon_idx = ensure_fx_any(print_bus, {"event horizon", "eventhorizon"}, {"JS: Event Horizon Limiter/Clipper", "sstillwell/eventhorizon2"}, "print_master_event_horizon_limiter")
if print_bus and horizon_idx >= 0 then
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 0, -21.6)
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 1, -1.0)
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 2, 380.0)
  reaper.GetSetMediaTrackInfo_String(print_bus, "P_EXT:pass04_event_horizon_settings", "Threshold -21.6 dB, ceiling -1 dB, release 380 ms. Loud beat-forward review target around -6 LUFS; reject if pumping or vocal tear is audible.", true)
end
ensure_fx_any(print_bus, {"realimit"}, {"ReaLimit"}, "print_master_safety_limiter")
ensure_fx_any(print_bus, {"loudness"}, {"JS: Loudness Meter Peak/RMS/LUFS"}, "print_master_meter")

add_marker_once(0.0, "PASS04: Suno 000000 stems imported muted; active mix uses raw production stems")
add_marker_once(15.68, "PASS04 CHECK: vocal lower, beat/main melody should lead")
add_marker_once(40.0, "PASS04 NOTE: downloaded 000000 candidate ends here; not aligned full replacement")
add_marker_once(60.0, "PASS04 CHECK: hook melody forward without harsh vocal masking")

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
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "PASS04_MASTER_ALL_INFO_LOUD_24bit_48k", true)
reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", "PASS04 all-info pass. Suno 000000 all-detected stems downloaded/imported muted as a short candidate. Active mix remains based on raw production stems, with vocal lower, beat/main melody more forward, tighter vocal FX, and loud conservative -6 LUFS review master target.", true)

reaper.UpdateArrange()
if reaper.Main_SaveProjectEx then
  reaper.Main_SaveProjectEx(0, pass_path, 0)
end
reaper.Undo_EndBlock("Apply pass 04 Suno 000000 all-info mix", -1)
log("apply pass04 done positions_ok=" .. tostring(positions_ok) .. " render_end=" .. tostring(render_end))
