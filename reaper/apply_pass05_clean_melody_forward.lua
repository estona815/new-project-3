-- Pass 05: clean, melody-forward commercial polish.
-- Starts from PASS04. Keeps reference/candidate/quarantine material muted,
-- reduces noise-prone ambience and high-band tails, and moves the main
-- synth/keyboard melody forward without simply crushing the limiter harder.

local root = "/Users/hantaeheuk/Documents/New project 3"
local pass_path = root .. "/reaper/FRESH_MIX_MASTER_PASS_05_CLEAN_MELODY_FORWARD.rpp"
local log_path = "/tmp/codex_fresh_reaper/apply_pass05_clean_melody_forward.log"

os.execute("mkdir -p /tmp/codex_fresh_reaper")

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
      reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass05_fx_" .. label, add_name, true)
      log("added fx " .. tostring(add_name) .. " on " .. track_name(track))
      return idx
    end
  end
  reaper.GetSetMediaTrackInfo_String(track, "P_EXT:missing_pass05_fx_" .. label, table.concat(add_names, " | "), true)
  log("missing fx any " .. table.concat(add_names, " | ") .. " on " .. track_name(track))
  return -1
end

local function add_fx_any(track, add_names, label)
  if not track then return -1 end
  for _, add_name in ipairs(add_names) do
    local idx = reaper.TrackFX_AddByName(track, add_name, false, -1)
    if idx >= 0 then
      reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass05_fx_" .. label, add_name, true)
      log("added fx " .. tostring(add_name) .. " on " .. track_name(track))
      return idx
    end
  end
  reaper.GetSetMediaTrackInfo_String(track, "P_EXT:missing_pass05_fx_" .. label, table.concat(add_names, " | "), true)
  log("missing fx add " .. table.concat(add_names, " | ") .. " on " .. track_name(track))
  return -1
end

local function remove_fx_matching(track_name_text, search)
  local track = find_track(track_name_text)
  if not track then return end
  for i = reaper.TrackFX_GetCount(track) - 1, 0, -1 do
    local _, fx_name = reaper.TrackFX_GetFXName(track, i, "")
    if string.find(string.lower(fx_name or ""), string.lower(search), 1, true) then
      reaper.TrackFX_Delete(track, i)
      log("removed fx " .. tostring(search) .. " on " .. track_name_text)
    end
  end
end

local function ensure_dynamic_band(track_name_text, label, freq, q, threshold_db, max_cut_db, attack_ms, release_ms)
  local track = find_track(track_name_text)
  local idx = add_fx_any(
    track,
    {"JS: Codex Dynamic EQ Band", "JS: codex_fresh_mix/codex_dynamic_eq_band.jsfx", "codex_fresh_mix/codex_dynamic_eq_band.jsfx"},
    label
  )
  if track and idx >= 0 then
    reaper.TrackFX_SetParam(track, idx, 0, freq)
    reaper.TrackFX_SetParam(track, idx, 1, q)
    reaper.TrackFX_SetParam(track, idx, 2, threshold_db)
    reaper.TrackFX_SetParam(track, idx, 3, max_cut_db)
    reaper.TrackFX_SetParam(track, idx, 4, attack_ms)
    reaper.TrackFX_SetParam(track, idx, 5, release_ms)
    reaper.TrackFX_SetParam(track, idx, 6, 0.0)
    reaper.GetSetMediaTrackInfo_String(
      track,
      "P_EXT:pass05_dynamic_eq_" .. label,
      string.format("Codex Dynamic EQ: %.0f Hz Q %.2f threshold %.1f dB max cut %.1f dB attack %.1f ms release %.1f ms", freq, q, threshold_db, max_cut_db, attack_ms, release_ms),
      true
    )
  end
end

local function ensure_noise_tamer(track_name_text, label, split_hz, threshold_db, max_atten_db, attack_ms, release_ms, mix)
  local track = find_track(track_name_text)
  local idx = ensure_fx_any(
    track,
    {"codex_noise_floor_tamer", "Codex Noise Floor Tamer"},
    {"JS: Codex Noise Floor Tamer", "JS: codex_fresh_mix/codex_noise_floor_tamer.jsfx", "codex_fresh_mix/codex_noise_floor_tamer.jsfx"},
    label
  )
  if track and idx >= 0 then
    reaper.TrackFX_SetParam(track, idx, 0, split_hz)
    reaper.TrackFX_SetParam(track, idx, 1, threshold_db)
    reaper.TrackFX_SetParam(track, idx, 2, max_atten_db)
    reaper.TrackFX_SetParam(track, idx, 3, attack_ms)
    reaper.TrackFX_SetParam(track, idx, 4, release_ms)
    reaper.TrackFX_SetParam(track, idx, 5, mix)
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass05_noise_tamer_" .. label, string.format("High split %.0f Hz, close threshold %.1f dB, max attenuation %.1f dB.", split_hz, threshold_db, max_atten_db), true)
  end
end

local function ensure_presence_tilt(track_name_text, label, split_hz, gain_db, mix)
  local track = find_track(track_name_text)
  local idx = ensure_fx_any(
    track,
    {"codex_presence_tilt", "Codex Presence Tilt"},
    {"JS: Codex Presence Tilt", "JS: codex_fresh_mix/codex_presence_tilt.jsfx", "codex_fresh_mix/codex_presence_tilt.jsfx"},
    label
  )
  if track and idx >= 0 then
    reaper.TrackFX_SetParam(track, idx, 0, split_hz)
    reaper.TrackFX_SetParam(track, idx, 1, gain_db)
    reaper.TrackFX_SetParam(track, idx, 2, mix)
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass05_presence_tilt_" .. label, string.format("Upper band split %.0f Hz, gain %.1f dB, mix %.2f.", split_hz, gain_db, mix), true)
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
  local base = lin(1.45)
  local under_vocal = lin(0.85)
  local open_hook = lin(2.2)
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
    reaper.InsertEnvelopePoint(env, e + 0.20, open_hook, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, e + 3.00, base, 0, 0, false, true)
  end
  reaper.Envelope_SortPoints(env)
  if track then
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass05_music_presence", "Melody-forward automation: +1.45 dB baseline, +0.85 dB under vocals, short +2.2 dB post-phrase lift.", true)
  end
end

local function write_vocal_fx_tuck_envelope()
  local track = find_track("VOCAL_FX_BUS")
  local env = ensure_volume_envelope(track)
  if not env then return end
  reaper.DeleteEnvelopePointRange(env, 0.0, 170.0)
  local base = lin(-2.6)
  local dense = lin(-4.2)
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
  local base = lin(-7.0)
  local throw = lin(-2.8)
  local throw_times = {4.587, 5.995, 18.240, 21.845, 24.064, 28.395, 34.197, 60.992, 69.355, 72.320, 77.440, 90.859, 92.779, 101.248}
  reaper.InsertEnvelopePoint(env, 0.0, base, 0, 0, false, true)
  reaper.InsertEnvelopePoint(env, 170.0, base, 0, 0, false, true)
  for _, t in ipairs(throw_times) do
    reaper.InsertEnvelopePoint(env, math.max(0, t - 0.18), base, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, t - 0.03, throw, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, t + 0.20, throw, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, t + 0.42, base, 0, 0, false, true)
  end
  reaper.Envelope_SortPoints(env)
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

local function add_marker_once(time, name)
  local _, markers, regions = reaper.CountProjectMarkers(0)
  local total = markers + regions
  for i = 0, total - 1 do
    local _, is_region, pos, _, marker_name = reaper.EnumProjectMarkers(i)
    if not is_region and math.abs((pos or 0) - time) < 0.001 and marker_name == name then return end
  end
  reaper.AddProjectMarker(0, false, time, time, name, -1)
end

log("apply pass05 start")
reaper.Undo_BeginBlock()

-- Render safety: keep references, quarantine, guide MIDI, and short candidate stems muted.
set_named_track("REF_BUS", nil, nil, true)
set_named_track("ARTIFACT_QUARANTINE_BUS", nil, nil, true)
set_named_track("SUNO_000000_CANDIDATE_BUS", -18.0, 0.0, true)
for _, name in ipairs({
  "SUNO000000 CANDIDATE - Lead Vocals",
  "SUNO000000 CANDIDATE - Drums",
  "SUNO000000 CANDIDATE - Bass",
  "SUNO000000 CANDIDATE - Synth",
  "SUNO000000 CANDIDATE - Other",
  "00_REF_Full_Mix",
  "1 Instrumental",
  "PROBLEM REF - hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_24-48",
  "PROBLEM REF - hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_320k",
  "TECH REF - 동반자살 WAV",
  "QUARANTINE - 03_FX",
  "QUARANTINE - 08_Guitar",
  "Female BGV L - 0 Lead Vocals",
  "Female BGV L - female_vocal_candidate_clean",
}) do
  set_named_track(name, nil, nil, true)
end
for i = 0, reaper.CountTracks(0) - 1 do
  local tr = reaper.GetTrack(0, i)
  if string.find(track_name(tr), "Guide MIDI", 1, true) then set_track(tr, -18.0, 0.0, true) end
end

-- Clean commercial balance: keep vocal readable, but let synth/keyboard melody lead.
set_named_track("12_Vocals", -6.4, 0.0, false)
set_named_track("MALE_LEAD_VOX_BUS", -0.2, 0.0, false)
set_named_track("Female BGV R - 11_Backing_Vocals", -34.0, 0.38, false)
set_named_track("FEMALE_BGV_BUS", -11.5, 0.0, false)

set_named_track("04_Synth", -9.8, 0.0, false)
set_named_track("07_Keyboard", -10.5, 0.0, false)
set_named_track("01_Woodwinds", -12.6, -0.05, false)
set_named_track("05_Strings", -12.9, 0.0, false)
set_named_track("02_Brass", -14.2, 0.05, false)
set_named_track("MUSIC_BUS", 2.2, 0.0, false)

set_named_track("10_Drums", -9.8, 0.0, false)
set_named_track("06_Percussion", -12.4, 0.0, false)
set_named_track("DRUM_BUS", -0.6, 0.0, false)
set_named_track("09_Bass", -11.8, 0.0, false)
set_named_track("BASS_808_BUS", -1.3, 0.0, false)
set_named_track("FX_BUS", -10.0, 0.0, false)
set_named_track("MIX_BUS", 0.0, 0.0, false)
set_named_track("MASTER_PREMIX_BUS", 0.0, 0.0, false)

set_named_track("VOCAL_PLATE_SEND", -11.0, 0.0, false)
set_named_track("VOCAL_DELAY_SEND", -15.0, 0.0, false)
set_named_track("SHORT_ROOM_SEND", -18.0, 0.0, false)
set_named_track("OPTIONAL_WIDE_THROW_SEND", -20.0, 0.0, false)
set_named_track("VOCAL_FX_BUS", -11.5, 0.0, false)

set_send_db("12_Vocals", "VOCAL_PLATE_SEND", -28.5)
set_send_db("12_Vocals", "VOCAL_DELAY_SEND", -35.0)
set_send_db("12_Vocals", "SHORT_ROOM_SEND", -42.0)
set_send_db("Female BGV R - 11_Backing_Vocals", "VOCAL_PLATE_SEND", -24.0)
set_send_db("Female BGV R - 11_Backing_Vocals", "SHORT_ROOM_SEND", -29.0)

write_music_presence_envelope()
write_vocal_fx_tuck_envelope()
write_delay_throw_tuck()

-- Replace broad previous dynamic bands with a cleaner, less vocal-pocketed set.
for _, dynamic_track in ipairs({"MALE_LEAD_VOX_BUS", "FEMALE_BGV_BUS", "BASS_808_BUS", "MUSIC_BUS", "DRUM_BUS", "MIX_BUS"}) do
  remove_fx_matching(dynamic_track, "codex_dynamic_eq_band")
  remove_fx_matching(dynamic_track, "Codex Dynamic EQ Band")
end
for _, t in ipairs({"MALE_LEAD_VOX_BUS", "FEMALE_BGV_BUS", "VOCAL_FX_BUS", "FX_BUS", "MUSIC_BUS", "04_Synth", "07_Keyboard"}) do
  remove_fx_matching(t, "codex_noise_floor_tamer")
  remove_fx_matching(t, "Codex Noise Floor Tamer")
end
for _, t in ipairs({"MUSIC_BUS", "04_Synth", "07_Keyboard"}) do
  remove_fx_matching(t, "codex_presence_tilt")
  remove_fx_matching(t, "Codex Presence Tilt")
end

ensure_dynamic_band("MALE_LEAD_VOX_BUS", "lead_mud_240", 240, 1.10, -36.0, 2.2, 12.0, 190.0)
ensure_dynamic_band("MALE_LEAD_VOX_BUS", "lead_harsh_4100", 4100, 1.05, -37.0, 2.4, 5.0, 130.0)
ensure_dynamic_band("MALE_LEAD_VOX_BUS", "lead_sibilance_7400", 7400, 1.55, -42.0, 3.0, 3.0, 120.0)
ensure_dynamic_band("FEMALE_BGV_BUS", "bgv_compete_3200", 3200, 1.10, -45.0, 3.2, 7.0, 170.0)
ensure_dynamic_band("FEMALE_BGV_BUS", "bgv_sibilance_7900", 7900, 1.55, -48.0, 3.0, 4.0, 150.0)
ensure_dynamic_band("BASS_808_BUS", "bass_mud_180", 180, 1.00, -35.0, 2.0, 18.0, 240.0)
ensure_dynamic_band("BASS_808_BUS", "bass_lowmid_285", 285, 1.05, -37.0, 1.8, 18.0, 240.0)
ensure_dynamic_band("MUSIC_BUS", "music_lowmid_noise_320", 320, 0.85, -37.0, 1.6, 24.0, 300.0)
ensure_dynamic_band("MUSIC_BUS", "music_fizz_8600", 8600, 1.10, -43.0, 2.0, 8.0, 210.0)
ensure_dynamic_band("DRUM_BUS", "drum_hat_harsh_8800", 8800, 1.25, -40.0, 2.4, 4.0, 140.0)
ensure_dynamic_band("MIX_BUS", "mix_lowmid_bloom_315", 315, 0.75, -33.0, 1.1, 25.0, 330.0)
ensure_dynamic_band("MIX_BUS", "mix_upper_noise_9000", 9000, 0.85, -42.0, 1.3, 8.0, 240.0)

ensure_noise_tamer("MALE_LEAD_VOX_BUS", "lead_high_tail", 7200, -47.0, 2.2, 18.0, 260.0, 0.75)
ensure_noise_tamer("FEMALE_BGV_BUS", "bgv_high_tail", 6600, -50.0, 5.0, 16.0, 300.0, 0.95)
ensure_noise_tamer("VOCAL_FX_BUS", "fx_high_tail", 6200, -46.0, 5.5, 12.0, 420.0, 1.0)
ensure_noise_tamer("FX_BUS", "general_fx_high_tail", 6400, -50.0, 4.5, 14.0, 360.0, 0.9)
ensure_noise_tamer("MUSIC_BUS", "music_tail", 9000, -51.0, 1.8, 25.0, 300.0, 0.55)
ensure_noise_tamer("04_Synth", "synth_tail", 9000, -52.0, 2.0, 18.0, 260.0, 0.55)
ensure_noise_tamer("07_Keyboard", "keyboard_tail", 9200, -52.0, 1.6, 18.0, 260.0, 0.5)

ensure_presence_tilt("MUSIC_BUS", "melody_bus_presence", 1500, 0.85, 0.85)
ensure_presence_tilt("04_Synth", "synth_melody_presence", 1700, 0.70, 0.75)
ensure_presence_tilt("07_Keyboard", "keyboard_melody_presence", 1650, 0.65, 0.70)

local print_bus = find_track("PRINT_MASTER_BUS")
local horizon_idx = ensure_fx_any(print_bus, {"event horizon", "eventhorizon"}, {"JS: Event Horizon Limiter/Clipper", "sstillwell/eventhorizon2"}, "print_master_event_horizon_limiter")
if print_bus and horizon_idx >= 0 then
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 0, -21.0)
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 1, -1.0)
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 2, 420.0)
  reaper.GetSetMediaTrackInfo_String(print_bus, "P_EXT:pass05_event_horizon_settings", "Threshold -21.0 dB, ceiling -1 dB, release 420 ms. Clean loud review target; less aggressive than PASS03 to reduce pumping/noise lift.", true)
end
ensure_fx_any(print_bus, {"realimit"}, {"ReaLimit"}, "print_master_safety_limiter")
ensure_fx_any(print_bus, {"loudness"}, {"JS: Loudness Meter Peak/RMS/LUFS"}, "print_master_meter")

add_marker_once(0.0, "PASS05: clean melody-forward commercial polish")
add_marker_once(15.68, "PASS05 CHECK: synth/keyboard melody forward, vocal readable, less noisy FX")
add_marker_once(60.0, "PASS05 CHECK: hook melody present without limiter fizz")

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
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "PASS05_MASTER_CLEAN_MELODY_FORWARD_24bit_48k", true)
reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", "PASS05 clean melody-forward polish. PASS04 base, reference/candidate/quarantine muted, vocal ambience/noise tails reduced with custom JSFX, synth/keyboard melody raised and presence-tilted, master kept loud but less pump-prone than PASS03.", true)

reaper.UpdateArrange()
if reaper.Main_SaveProjectEx then
  reaper.Main_SaveProjectEx(0, pass_path, 0)
end
reaper.Undo_EndBlock("Apply pass 05 clean melody-forward polish", -1)
log("apply pass05 done positions_ok=" .. tostring(positions_ok) .. " render_end=" .. tostring(render_end))
