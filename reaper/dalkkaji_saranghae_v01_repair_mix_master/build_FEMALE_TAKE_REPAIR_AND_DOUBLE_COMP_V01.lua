local slug = os.getenv("DALKK_SLUG") or "dalkkaji_saranghae_v01_repair_mix_master"
local root = os.getenv("DALKK_ROOT") or "/Users/hantaeheuk/Documents/New project 3"
local project_path = root .. "/reaper/" .. slug .. "/FEMALE_TAKE_REPAIR_AND_DOUBLE_COMP_V01.rpp"
local tmp_dir = "/tmp/codex_dalkkaji_repair_v01"
local log_path = tmp_dir .. "/build.log"

os.execute("mkdir -p " .. string.format("%q", tmp_dir))
os.remove(log_path)

local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\n")
    f:close()
  end
end

local function lin(db)
  return 10 ^ ((db or 0) / 20)
end

local function set_name(track, name)
  reaper.GetSetMediaTrackInfo_String(track, "P_NAME", name, true)
end

local function track_name(track)
  local _, name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
  return name or ""
end

local function clear_project()
  for i = reaper.CountTracks(0) - 1, 0, -1 do
    reaper.DeleteTrack(reaper.GetTrack(0, i))
  end
end

local function new_track(name, db, mute)
  local idx = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, true)
  local track = reaper.GetTrack(0, idx)
  set_name(track, name)
  reaper.SetMediaTrackInfo_Value(track, "D_VOL", lin(db or 0))
  reaper.SetMediaTrackInfo_Value(track, "B_MUTE", mute and 1 or 0)
  return track
end

local function insert_media(track, path, mute)
  if not path or path == "" then return nil end
  local source = reaper.PCM_Source_CreateFromFile(path)
  if not source then
    log("source load failed: " .. tostring(path))
    return nil
  end
  local length = reaper.GetMediaSourceLength(source)
  local item = reaper.AddMediaItemToTrack(track)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, source)
  reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0)
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", length)
  reaper.SetMediaItemInfo_Value(item, "B_MUTE", mute and 1 or 0)
  reaper.GetSetMediaItemTakeInfo_String(take, "P_NAME", path:match("([^/]+)$") or path, true)
  return item
end

local function add_fx(track, candidates, label)
  for _, name in ipairs(candidates) do
    local lower = string.lower(name)
    if lower:find("antares") or lower:find("auto%-tune") or lower:find("autotune") then
      log("blocked paid/Antares candidate: " .. name)
    else
      local idx = reaper.TrackFX_AddByName(track, name, false, -1)
      if idx >= 0 then
        reaper.GetSetMediaTrackInfo_String(track, "P_EXT:codex_fx_" .. label, name, true)
        log("added fx " .. name .. " on " .. track_name(track))
        return idx
      end
    end
  end
  log("missing fx " .. label .. " on " .. track_name(track))
  return -1
end

local function add_vocal_cleanup_chain(track)
  -- Stage 1: Soothe2 / Pro-Q style cleanup with free/local equivalents.
  add_fx(track, {"ReaEQ (Cockos)", "VST: ReaEQ (Cockos)"}, "reaeq_hpf_mud_deess")
  add_fx(track, {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: TDR Nova (Tokyo Dawn Labs)", "TDR Nova"}, "tdr_nova_dynamic_eq")
  add_fx(track, {"ReaXcomp (Cockos)", "VST: ReaXcomp (Cockos)"}, "reaxcomp_soothe_ds_optional")
  -- Stage 2: Black Box / Decapitator style parallel thickness, kept subtle.
  add_fx(track, {"JS: Saturation", "JS: LOSER/Saturation", "JS: Stillwell/saturation", "JS: waveshaping_distortion"}, "sat_hg2_decap_alt")
  add_fx(track, {"JS: Exciter", "JS: LOSER/exciter", "JS: Stillwell/exciter"}, "air_exciter_ozone_alt")
  -- Stage 3: 1176-style fast control.
  add_fx(track, {"ReaComp (Cockos)", "VST: ReaComp (Cockos)"}, "reacomp_light")
end

local function add_music_chain(track)
  -- Pro-Q / Nova style resonance carving plus compressor and clipped texture.
  add_fx(track, {"ReaEQ (Cockos)", "VST: ReaEQ (Cockos)"}, "reaeq_tone")
  add_fx(track, {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: TDR Nova (Tokyo Dawn Labs)", "TDR Nova"}, "tdr_nova_resonance_carve")
  add_fx(track, {"ReaComp (Cockos)", "VST: ReaComp (Cockos)"}, "reacomp_glue")
  add_fx(track, {"JS: Saturation", "JS: LOSER/Saturation", "JS: Stillwell/saturation", "JS: waveshaping_distortion"}, "sat_texture")
  add_fx(track, {"JS: Soft Clipper/Limiter", "JS: Event Horizon Limiter/Clipper", "JS: LOSER/masterLimiter", "ReaLimit (Cockos)"}, "clip_texture")
end

local function add_print_chain(track)
  -- Ozone Stabilizer / Exciter / Pro-L2 style final safety using local equivalents.
  add_fx(track, {"ReaEQ (Cockos)", "VST: ReaEQ (Cockos)"}, "print_reaeq_safety")
  add_fx(track, {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: TDR Nova (Tokyo Dawn Labs)", "TDR Nova"}, "print_dynamic_stabilizer")
  add_fx(track, {"ReaXcomp (Cockos)", "VST: ReaXcomp (Cockos)"}, "print_reaxcomp_safety")
  add_fx(track, {"JS: Exciter", "JS: LOSER/exciter", "JS: Stillwell/exciter"}, "print_air_exciter")
  add_fx(track, {"ReaComp (Cockos)", "VST: ReaComp (Cockos)"}, "print_reacomp_light")
  add_fx(track, {"ReaLimit (Cockos)", "JS: Event Horizon Limiter/Clipper", "JS: Soft Clipper/Limiter", "JS: LOSER/masterLimiter"}, "print_limit_clip_safety")
end

local function add_endpoint_fx_chain(track)
  add_fx(track, {"ReaEQ (Cockos)", "VST: ReaEQ (Cockos)"}, "endpoint_reaeq_hpf_lp")
  add_fx(track, {"VST: ReaDelay (Cockos)", "ReaDelay (Cockos)"}, "endpoint_readelay")
  add_fx(track, {"VST: ReaVerbate (Cockos)", "ReaVerbate (Cockos)"}, "endpoint_reaverbate")
  add_fx(track, {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: TDR Nova (Tokyo Dawn Labs)", "TDR Nova"}, "endpoint_dynamic_tame")
end

local function add_delay_bus_chain(track)
  add_fx(track, {"ReaEQ (Cockos)", "VST: ReaEQ (Cockos)"}, "delay_bus_hilo_cut")
  add_fx(track, {"VST: ReaDelay (Cockos)", "ReaDelay (Cockos)"}, "echoboy_alt_readelay")
  add_fx(track, {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: TDR Nova (Tokyo Dawn Labs)", "TDR Nova"}, "delay_bus_dynamic_tame")
  add_fx(track, {"ReaComp (Cockos)", "VST: ReaComp (Cockos)"}, "delay_bus_duck_comp")
end

local function add_reverb_bus_chain(track)
  add_fx(track, {"ReaEQ (Cockos)", "VST: ReaEQ (Cockos)"}, "reverb_bus_hilo_cut")
  add_fx(track, {"VST: ReaVerbate (Cockos)", "ReaVerbate (Cockos)", "VST: ReaVerb (Cockos)", "ReaVerb (Cockos)"}, "altiverb_seventh_heaven_alt")
  add_fx(track, {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: TDR Nova (Tokyo Dawn Labs)", "TDR Nova"}, "reverb_bus_dynamic_tame")
  add_fx(track, {"ReaComp (Cockos)", "VST: ReaComp (Cockos)"}, "reverb_bus_duck_comp")
end

local function find_track(name)
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    if track_name(tr) == name then return tr end
  end
  return nil
end

local function add_send(src_name, dest_name, db)
  local src = find_track(src_name)
  local dest = find_track(dest_name)
  if not src or not dest then
    log("missing send endpoint: " .. tostring(src_name) .. " -> " .. tostring(dest_name))
    return
  end
  local send = reaper.CreateTrackSend(src, dest)
  reaper.SetTrackSendInfo_Value(src, 0, send, "D_VOL", lin(db or -24))
  log("send " .. src_name .. " -> " .. dest_name .. " " .. tostring(db) .. " dB")
end

local tracks = {
  {"FULL_MIX_REFERENCE", root .. "/audio_work/" .. slug .. "/source/0 달까지 사랑해.wav", true, -12.0, "reference"},
  {"INSTRUMENTAL_OR_BEAT", root .. "/audio_work/" .. slug .. "/processed_stems/instrumental_or_beat_processed.wav", false, -0.5, "music"},
  {"MAIN_MELODY_PRESENCE_LIFT", root .. "/audio_work/" .. slug .. "/processed_stems/main_melody_presence_lift.wav", false, -12.0, "music"},
  {"MAIN_MALE_VOCAL_REFERENCE", root .. "/audio_work/" .. slug .. "/processed_stems/main_male_vocal_clean.wav", false, -5.5, "vocal"},
  {"FEMALE_TAKE_01_RAW", root .. "/audio_work/" .. slug .. "/source/11 Backing_Vocals.wav", true, -18.0, "reference"},
  {"FEMALE_TAKE_02_RAW", root .. "/audio_work/" .. slug .. "/source/13 여자목소리1.wav", true, -18.0, "reference"},
  {"FEMALE_TAKE_03_RAW", root .. "/audio_work/" .. slug .. "/source/14 달까지 사랑해 (Vocals) (Add Instrumental).wav", true, -18.0, "reference"},
  {"FEMALE_TAKE_04_RAW", root .. "/audio_work/" .. slug .. "/source/15 달까지 사랑해 (Vocals) (Add Instrumental).wav", true, -18.0, "reference"},
  {"FEMALE_TAKE_05_RAW", root .. "/audio_work/" .. slug .. "/source/16 달까지 사랑해 (Vocals) (Add Instrumental).wav", true, -18.0, "reference"},
  {"FEMALE_CLEAN_CANDIDATES", root .. "/audio_work/" .. slug .. "/processed_stems/female_layer_A_clean_subtle.wav", true, -14.0, "vocal"},
  {"FEMALE_DOUBLE_EDIT", root .. "/audio_work/" .. slug .. "/processed_stems/female_double_edit_stem.wav", false, -13.8, "vocal"},
  {"FEMALE_ADLIB_EDIT", root .. "/audio_work/" .. slug .. "/processed_stems/female_adlib_edit_stem.wav", false, -16.0, "vocal"},
  {"FEMALE_TEXTURE_EDIT", root .. "/audio_work/" .. slug .. "/processed_stems/female_texture_edit_stem.wav", false, -20.0, "vocal"},
  {"FEMALE_ENDPOINT_REVERB_THROW", root .. "/audio_work/" .. slug .. "/processed_stems/female_endpoint_reverb_throw.wav", false, -18.0, "endpoint"},
  {"VOCAL_DELAY_SEND_ECHOBOY_ALT", "", false, -18.0, "delay_bus"},
  {"VOCAL_REVERB_SEND_ALTIVERB_ALT", "", false, -18.0, "reverb_bus"},
  {"REJECTED_TAKES_MUTED", root .. "/audio_work/" .. slug .. "/processed_stems/rejected_takes_muted_reference.wav", true, -24.0, "reference"},
  {"VOCAL_BUS", "", false, -0.5, "vocal_bus"},
  {"PRINT_PREVIEW", root .. "/renders/" .. slug .. "/preview_with_female_layer.wav", true, -10.0, "print"},
}

clear_project()
for _, row in ipairs(tracks) do
  local tr = new_track(row[1], row[4], row[3])
  insert_media(tr, row[2], false)
  if row[5] == "vocal" then
    add_vocal_cleanup_chain(tr)
  elseif row[5] == "music" then
    add_music_chain(tr)
  elseif row[5] == "endpoint" then
    add_endpoint_fx_chain(tr)
  elseif row[5] == "delay_bus" then
    add_delay_bus_chain(tr)
  elseif row[5] == "reverb_bus" then
    add_reverb_bus_chain(tr)
  elseif row[5] == "print" then
    add_print_chain(tr)
  end
end

add_send("MAIN_MALE_VOCAL_REFERENCE", "VOCAL_DELAY_SEND_ECHOBOY_ALT", -28.0)
add_send("FEMALE_DOUBLE_EDIT", "VOCAL_DELAY_SEND_ECHOBOY_ALT", -32.0)
add_send("FEMALE_TEXTURE_EDIT", "VOCAL_DELAY_SEND_ECHOBOY_ALT", -35.0)
add_send("MAIN_MALE_VOCAL_REFERENCE", "VOCAL_REVERB_SEND_ALTIVERB_ALT", -30.0)
add_send("FEMALE_DOUBLE_EDIT", "VOCAL_REVERB_SEND_ALTIVERB_ALT", -34.0)
add_send("FEMALE_ENDPOINT_REVERB_THROW", "VOCAL_REVERB_SEND_ALTIVERB_ALT", -26.0)

reaper.GetSetProjectInfo(0, "PROJECT_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "PROJECT_SRATE_USE", 1, true)
reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", root .. "/renders/" .. slug, true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "preview_with_female_layer_reaperprint", true)
reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", "FEMALE_TAKE_REPAIR_AND_DOUBLE_COMP_V01. Main male vocal preserved. Paid reference chain mapped to local equivalents: Soothe2/Pro-Q -> ReaEQ/TDR Nova/ReaXcomp, HG-2/Decapitator -> JS saturation/clipper, Pro-DS -> Nova/ReaXcomp, 1176 -> fast ReaComp, Ozone/Pro-L -> Nova/ReaXcomp/ReaLimit/Event Horizon, EchoBoy/Altiverb -> ReaDelay/ReaVerbate sends. No Antares/login-required chain.", true)
reaper.Main_SaveProjectEx(0, project_path, 0)
log("saved " .. project_path)
