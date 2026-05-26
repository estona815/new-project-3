-- Pass 02 commercial balance repair.
-- Run after opening reaper/FRESH_MIX_MASTER_PASS_01.rpp. This does not reimport
-- stems; it validates and reshapes the existing fresh session, then saves:
-- reaper/FRESH_MIX_MASTER_PASS_02_COMMERCIAL_BALANCE.rpp

local root = "/Users/hantaeheuk/Documents/New project 3"
local pass_path = root .. "/reaper/FRESH_MIX_MASTER_PASS_02_COMMERCIAL_BALANCE.rpp"
local log_path = "/tmp/codex_fresh_reaper/apply_pass02_commercial_balance.log"

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
      reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass02_fx_" .. label, add_name, true)
      log("added fx " .. tostring(add_name) .. " on " .. track_name(track))
      return idx
    end
  end
  reaper.GetSetMediaTrackInfo_String(track, "P_EXT:missing_pass02_fx_" .. label, table.concat(add_names, " | "), true)
  log("missing fx any " .. table.concat(add_names, " | ") .. " on " .. track_name(track))
  return -1
end

local function add_fx_any(track, add_names, label)
  if not track then return -1 end
  for _, add_name in ipairs(add_names) do
    local idx = reaper.TrackFX_AddByName(track, add_name, false, -1)
    if idx >= 0 then
      reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass02_fx_" .. label, add_name, true)
      log("added fx " .. tostring(add_name) .. " on " .. track_name(track))
      return idx
    end
  end
  reaper.GetSetMediaTrackInfo_String(track, "P_EXT:missing_pass02_fx_" .. label, table.concat(add_names, " | "), true)
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
      log("removed existing pass02 dynamic fx on " .. track_name_text)
    end
  end
end

local function ensure_dynamic_band(track_name_text, label, freq, q, threshold_db, max_cut_db, attack_ms, release_ms)
  local track = find_track(track_name_text)
  local idx = add_fx_any(
    track,
    {
      "JS: Codex Dynamic EQ Band",
      "JS: codex_fresh_mix/codex_dynamic_eq_band.jsfx",
      "codex_fresh_mix/codex_dynamic_eq_band.jsfx"
    },
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
      "P_EXT:pass02_dynamic_eq_" .. label,
      string.format("Codex Dynamic EQ: %.0f Hz Q %.2f threshold %.1f dB max cut %.1f dB attack %.1f ms release %.1f ms", freq, q, threshold_db, max_cut_db, attack_ms, release_ms),
      true
    )
  end
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

local function select_only_track(track)
  reaper.Main_OnCommand(40297, 0) -- Track: Unselect all tracks
  reaper.SetTrackSelected(track, true)
end

local function ensure_volume_envelope(track)
  if not track then return nil end
  local env = reaper.GetTrackEnvelopeByName(track, "Volume")
  if env then return env end
  select_only_track(track)
  reaper.Main_OnCommand(40406, 0) -- Track: Toggle track volume envelope visible
  return reaper.GetTrackEnvelopeByName(track, "Volume")
end

local function clear_and_write_duck(track_name_text, segments, duck_db, label)
  local track = find_track(track_name_text)
  local env = ensure_volume_envelope(track)
  if not env then
    log("no volume envelope for " .. tostring(track_name_text))
    return
  end
  local duck = lin(duck_db)
  reaper.DeleteEnvelopePointRange(env, 0.0, 160.0)
  for _, seg in ipairs(segments) do
    local s = seg[1]
    local e = seg[2]
    reaper.InsertEnvelopePoint(env, math.max(0.0, s - 0.20), 1.0, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, s, duck, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, e, duck, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, e + 0.25, 1.0, 0, 0, false, true)
  end
  reaper.Envelope_SortPoints(env)
  if track then
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass02_automation_" .. label, "Volume duck " .. tostring(duck_db) .. " dB during lead vocal phrases.", true)
  end
  log("automation duck written " .. tostring(track_name_text) .. " " .. tostring(label))
end

local function clear_and_write_delay_throws(track_name_text, throw_times)
  local track = find_track(track_name_text)
  local env = ensure_volume_envelope(track)
  if not env then
    log("no delay throw envelope for " .. tostring(track_name_text))
    return
  end
  reaper.DeleteEnvelopePointRange(env, 0.0, 160.0)
  reaper.InsertEnvelopePoint(env, 0.0, 0.52, 0, 0, false, true)
  reaper.InsertEnvelopePoint(env, 160.0, 0.52, 0, 0, false, true)
  for _, t in ipairs(throw_times) do
    reaper.InsertEnvelopePoint(env, math.max(0.0, t - 0.22), 0.52, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, t - 0.04, 1.00, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, t + 0.34, 1.00, 0, 0, false, true)
    reaper.InsertEnvelopePoint(env, t + 0.62, 0.52, 0, 0, false, true)
  end
  reaper.Envelope_SortPoints(env)
  if track then
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:pass02_automation_delay_throws", "Delay return stays tucked down and opens only around phrase-end throw markers.", true)
  end
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

log("apply pass02 start")
reaper.Undo_BeginBlock()

if reaper.GetSetProjectInfo then
  reaper.GetSetProjectInfo(0, "PROJECT_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "PROJECT_SRATE_USE", 1, true)
end

-- Safety first: references, guide placeholders, and artifact quarantine stay out.
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

-- Vocal-first pass. The external female lead candidate is late/lead-like, so remove
-- it from active balance instead of letting it fight the main lead.
set_named_track("12_Vocals", -4.2, 0.0, false)
set_named_track("Female BGV R - 11_Backing_Vocals", -27.5, 0.38, false)
set_named_track("Female BGV L - 0 Lead Vocals", -42.0, -0.40, true)
set_named_track("Female BGV L - female_vocal_candidate_clean", -42.0, -0.35, true)

-- Rebuild the balance around the vocal pocket.
set_named_track("10_Drums", -10.8, 0.0, false)
set_named_track("06_Percussion", -13.2, 0.0, false)
set_named_track("09_Bass", -12.6, 0.0, false)
set_named_track("01_Woodwinds", -16.2, -0.05, false)
set_named_track("02_Brass", -16.6, 0.05, false)
set_named_track("04_Synth", -16.0, 0.0, false)
set_named_track("05_Strings", -16.2, 0.0, false)
set_named_track("07_Keyboard", -16.0, 0.0, false)

set_named_track("DRUM_BUS", -1.4, 0.0, false)
set_named_track("BASS_808_BUS", -2.0, 0.0, false)
set_named_track("MUSIC_BUS", -4.0, 0.0, false)
set_named_track("MALE_LEAD_VOX_BUS", 1.7, 0.0, false)
set_named_track("FEMALE_BGV_BUS", -7.2, 0.0, false)
set_named_track("VOCAL_FX_BUS", -7.4, 0.0, false)
set_named_track("FX_BUS", -8.0, 0.0, false)
set_named_track("MIX_BUS", -0.5, 0.0, false)
set_named_track("MASTER_PREMIX_BUS", 0.0, 0.0, false)
set_named_track("PRINT_MASTER_BUS", 0.0, 0.0, false)
set_named_track("VOCAL_PLATE_SEND", -6.5, 0.0, false)
set_named_track("VOCAL_DELAY_SEND", -10.8, 0.0, false)
set_named_track("SHORT_ROOM_SEND", -13.8, 0.0, false)
set_named_track("OPTIONAL_WIDE_THROW_SEND", -18.0, 0.0, false)

-- More controlled, send-based depth. Lead stays close; BGV is wet but quiet.
set_send_db("12_Vocals", "VOCAL_PLATE_SEND", -23.0)
set_send_db("12_Vocals", "VOCAL_DELAY_SEND", -28.5)
set_send_db("12_Vocals", "SHORT_ROOM_SEND", -35.0)
set_send_db("Female BGV R - 11_Backing_Vocals", "VOCAL_PLATE_SEND", -18.5)
set_send_db("Female BGV R - 11_Backing_Vocals", "SHORT_ROOM_SEND", -22.0)
set_send_db("Female BGV L - 0 Lead Vocals", "VOCAL_PLATE_SEND", -50.0)
set_send_db("Female BGV L - 0 Lead Vocals", "SHORT_ROOM_SEND", -50.0)
set_send_db("Female BGV L - female_vocal_candidate_clean", "VOCAL_PLATE_SEND", -50.0)
set_send_db("Female BGV L - female_vocal_candidate_clean", "SHORT_ROOM_SEND", -50.0)

-- Real dynamic-EQ-style JSFX bands, plus existing stock fallback anchors.
for _, dynamic_track in ipairs({"MALE_LEAD_VOX_BUS", "FEMALE_BGV_BUS", "BASS_808_BUS", "MUSIC_BUS", "DRUM_BUS", "MIX_BUS"}) do
  remove_fx_matching(dynamic_track, "codex_dynamic_eq_band")
  remove_fx_matching(dynamic_track, "Codex Dynamic EQ Band")
end
ensure_dynamic_band("MALE_LEAD_VOX_BUS", "lead_mud_260", 260, 1.20, -35.0, 2.5, 12.0, 180.0)
ensure_dynamic_band("MALE_LEAD_VOX_BUS", "lead_nasal_950", 950, 1.35, -34.0, 2.0, 10.0, 160.0)
ensure_dynamic_band("MALE_LEAD_VOX_BUS", "lead_harsh_3800", 3800, 1.10, -36.0, 2.8, 5.0, 120.0)
ensure_dynamic_band("MALE_LEAD_VOX_BUS", "lead_sibilance_7200", 7200, 1.65, -40.0, 3.2, 3.0, 110.0)
ensure_dynamic_band("FEMALE_BGV_BUS", "bgv_compete_3200", 3200, 1.10, -42.0, 3.0, 7.0, 160.0)
ensure_dynamic_band("FEMALE_BGV_BUS", "bgv_sibilance_7600", 7600, 1.55, -45.0, 2.5, 4.0, 130.0)
ensure_dynamic_band("BASS_808_BUS", "bass_mud_180", 180, 1.00, -34.0, 2.5, 18.0, 220.0)
ensure_dynamic_band("BASS_808_BUS", "bass_lowmid_280", 280, 1.10, -36.0, 2.0, 18.0, 220.0)
ensure_dynamic_band("MUSIC_BUS", "music_vocal_pocket_2200", 2200, 0.90, -37.0, 1.8, 20.0, 260.0)
ensure_dynamic_band("MUSIC_BUS", "music_upper_mask_4200", 4200, 0.95, -38.0, 1.5, 18.0, 240.0)
ensure_dynamic_band("MUSIC_BUS", "music_side_mud_proxy_260", 260, 0.80, -36.0, 1.6, 24.0, 280.0)
ensure_dynamic_band("DRUM_BUS", "drum_hat_harsh_8500", 8500, 1.20, -38.0, 2.2, 4.0, 130.0)
ensure_dynamic_band("MIX_BUS", "mix_lowmid_bloom_300", 300, 0.75, -32.0, 1.1, 25.0, 320.0)
ensure_dynamic_band("MIX_BUS", "mix_upper_edge_7800", 7800, 0.85, -39.0, 1.0, 8.0, 220.0)

-- Controlled automation: duck music/FX during dense vocal, and make delay throws
-- phrase-end events instead of constant haze.
local vocal_segments = {
  {4.0, 35.6},
  {59.8, 79.4},
  {89.7, 103.7},
}
clear_and_write_duck("MUSIC_BUS", vocal_segments, -1.4, "music_vocal_duck")
clear_and_write_duck("VOCAL_FX_BUS", vocal_segments, -1.8, "vocal_fx_duck")
local throw_times = {4.587, 5.995, 18.240, 21.845, 24.064, 28.395, 34.197, 60.992, 69.355, 72.320, 77.440, 90.859, 92.779, 101.248}
clear_and_write_delay_throws("VOCAL_DELAY_SEND", throw_times)
for _, t in ipairs(throw_times) do
  add_marker_once(t, "PASS02 DELAY THROW: open delay only at phrase end")
end

-- Reset unsafe master pressure for balance work. Final render can enable the
-- limiter, but the premaster render script bypasses PRINT_MASTER_BUS FX.
local print_bus = find_track("PRINT_MASTER_BUS")
local horizon_idx = ensure_fx_any(print_bus, {"event horizon", "eventhorizon"}, {"JS: Event Horizon Limiter/Clipper", "sstillwell/eventhorizon2"}, "print_master_event_horizon_limiter")
if print_bus and horizon_idx >= 0 then
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 0, -16.6)
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 1, -1.0)
  reaper.TrackFX_SetParam(print_bus, horizon_idx, 2, 320.0)
  reaper.GetSetMediaTrackInfo_String(print_bus, "P_EXT:pass02_event_horizon_settings", "Threshold -16.6 dB, ceiling -1 dB, release 320 ms. Final review loudness is applied only after balance repair; premaster render bypasses this chain.", true)
end
ensure_fx_any(print_bus, {"realimit"}, {"ReaLimit"}, "print_master_safety_limiter")
ensure_fx_any(print_bus, {"loudness"}, {"JS: Loudness Meter Peak/RMS/LUFS"}, "print_master_meter")

local lead_bus = find_track("MALE_LEAD_VOX_BUS")
if lead_bus then
  reaper.GetSetMediaTrackInfo_String(lead_bus, "P_EXT:pass02_intent", "Lead is the anchor. Dynamic bands control mud, nasal edge, 3-5 kHz harshness, and sibilance while preserving consonants.", true)
end
local bgv_bus = find_track("FEMALE_BGV_BUS")
if bgv_bus then
  reaper.GetSetMediaTrackInfo_String(bgv_bus, "P_EXT:pass02_bgv_status", "Only 11_Backing_Vocals remains active as quiet support. External/candidate female lead layers are muted due timing and AI/dropout risk.", true)
end

add_marker_once(3.72, "PASS02 BGV MUTED: external female has cut/timing risk")
add_marker_once(15.68, "PASS02 LEAD REPAIR: pitch/cut review")
add_marker_once(38.64, "PASS02 LEAD REPAIR: harsh consonant / energy spike")

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
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "PASS02_MASTER_24bit_48k", true)
reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", "Pass 02 commercial balance repair by Codex. Existing fresh session retained. References/quarantine muted. External/candidate female lead layers muted; raw BGV kept quiet/wet. Lead vocal raised/centered. Music/bass/drums carved and dynamically controlled with stock/custom fallback JSFX. Premaster bypasses master limiter; master uses conservative safety limiting only.", true)

reaper.UpdateArrange()
if reaper.Main_SaveProjectEx then
  reaper.Main_SaveProjectEx(0, pass_path, 0)
end
reaper.Undo_EndBlock("Apply pass 02 commercial balance repair", -1)
log("apply pass02 done positions_ok=" .. tostring(positions_ok) .. " render_end=" .. tostring(render_end))
