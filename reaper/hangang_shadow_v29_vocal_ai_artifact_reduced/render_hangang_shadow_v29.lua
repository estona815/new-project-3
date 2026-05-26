local root = "/Users/hantaeheuk/Documents/New project 3"
local project_dir = root .. "/reaper/hangang_shadow_v29_vocal_ai_artifact_reduced"
local render_dir = root .. "/renders/hangang_shadow_v29_vocal_ai_artifact_reduced"
local tmp_dir = "/tmp/codex_hangang_shadow_v29"
local mode = _G.HANGANG_V29_RENDER_MODE or os.getenv("HANGANG_V29_RENDER_MODE") or "master_print"
local log_path = tmp_dir .. "/render.log"

os.execute("mkdir -p " .. string.format("%q", tmp_dir))
os.execute("mkdir -p " .. string.format("%q", render_dir))

local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\n")
    f:close()
  end
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

local function max_active_item_end()
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

local function set_print_fx_enabled(enabled)
  local tr = find_track("PRINT_MASTER_BUS")
  if not tr then return end
  for i = 0, reaper.TrackFX_GetCount(tr) - 1 do
    reaper.TrackFX_SetEnabled(tr, i, enabled)
  end
end

local function lin(db)
  return 10 ^ (db / 20)
end

local function set_track_state(name, mute, db)
  local tr = find_track(name)
  if not tr then return end
  if mute ~= nil then
    reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", mute and 1 or 0)
  end
  if db ~= nil then
    reaper.SetMediaTrackInfo_Value(tr, "D_VOL", lin(db))
  end
end

local function apply_mode_state(render_mode)
  -- Defaults are the chosen blended balance: vocal slightly tucked, density layer quiet,
  -- and music bus carrying enough body that the lead does not sit painfully on top.
  set_track_state("vocal_processed - male lead 12 Vocals", false, -6.85)
  set_track_state("VOCAL NATURAL DENSITY PARALLEL - no tune", false, -24.0)
  set_track_state("VOCAL SHORT ROOM SLAP - dark blend", false, -31.0)
  set_track_state("MALE_MAIN_VOCAL_BUS", false, -0.85)
  set_track_state("instrumental", false, 0.30)
  set_track_state("mix_bus", false, -2.35)
  set_track_state("PRINT_MASTER_BUS", false, 0.0)

  if render_mode == "cleanup_light" then
    set_track_state("vocal_processed - male lead 12 Vocals", false, -6.15)
    set_track_state("VOCAL NATURAL DENSITY PARALLEL - no tune", true, nil)
    set_track_state("VOCAL SHORT ROOM SLAP - dark blend", true, nil)
    set_track_state("MALE_MAIN_VOCAL_BUS", false, -0.40)
    set_track_state("instrumental", false, 0.05)
    set_print_fx_enabled(false)
  elseif render_mode == "cleanup_medium" then
    set_track_state("vocal_processed - male lead 12 Vocals", false, -6.45)
    set_track_state("VOCAL NATURAL DENSITY PARALLEL - no tune", false, -26.0)
    set_track_state("VOCAL SHORT ROOM SLAP - dark blend", false, -33.0)
    set_track_state("MALE_MAIN_VOCAL_BUS", false, -0.55)
    set_track_state("instrumental", false, 0.12)
    set_print_fx_enabled(true)
  elseif render_mode == "cleanup_blended" or render_mode == "master_print" then
    set_print_fx_enabled(true)
  elseif render_mode == "premaster" then
    set_print_fx_enabled(false)
  elseif render_mode == "vocal_stem" then
    set_track_state("instrumental", true, nil)
    set_track_state("mix_bus", false, -0.20)
    set_print_fx_enabled(false)
  elseif render_mode == "instrumental_stem" then
    set_track_state("vocal_processed - male lead 12 Vocals", true, nil)
    set_track_state("VOCAL NATURAL DENSITY PARALLEL - no tune", true, nil)
    set_track_state("VOCAL SHORT ROOM SLAP - dark blend", true, nil)
    set_track_state("MALE_MAIN_VOCAL_BUS", true, nil)
    set_track_state("mix_bus", false, -0.20)
    set_print_fx_enabled(false)
  else
    set_print_fx_enabled(true)
  end
end

local function validate_safety()
  local failures = {}
  for _, name in ipairs({
    "reference_bus",
    "FEMALE_DOUBLE_LAYER_BUS_MUTED_REFERENCE",
    "original_reference_track - muted full mix",
    "vocal_raw - muted unprocessed male lead",
    "MUTED FEMALE LEAD CANDIDATE - v19 0 Lead Vocals",
    "MUTED V19 INSTRUMENTAL REF",
    "MUTED ARTIFACT CANDIDATE - 8 Guitar",
    "MUTED OLD FEMALE DOUBLE - 11 Backing_Vocals ALIGN FAIL",
    "MUTED NEW FEMALE RAW REF - 0 Lead Vocals",
    "MUTED NEW FEMALE INSTRUMENTAL REF",
  }) do
    local tr = find_track(name)
    if not tr or reaper.GetMediaTrackInfo_Value(tr, "B_MUTE") < 0.5 then
      failures[#failures + 1] = name .. " is not muted"
    end
  end
  for _, name in ipairs({
    "vocal_processed - male lead 12 Vocals",
    "MALE_MAIN_VOCAL_BUS",
    "instrumental",
    "mix_bus",
    "PRINT_MASTER_BUS",
  }) do
    local tr = find_track(name)
    if not tr then
      failures[#failures + 1] = name .. " missing"
    elseif reaper.GetMediaTrackInfo_Value(tr, "B_MUTE") > 0.5 then
      failures[#failures + 1] = name .. " muted"
    end
  end
  return failures
end

log("render prep start mode=" .. tostring(mode))
apply_mode_state(mode)
if mode ~= "vocal_stem" and mode ~= "instrumental_stem" then
  local failures = validate_safety()
  if #failures > 0 then
    for _, failure in ipairs(failures) do log("render safety failure: " .. failure) end
    error("Render blocked: " .. table.concat(failures, "; "))
  end
end

local pattern = "final_mix_vocal_ai_artifact_reduced"
local temp_project = tmp_dir .. "/hangang_shadow_v29_REAPERPRINT_RENDER.rpp"
if mode == "premaster" then
  pattern = "hangang_shadow_mashup_v29_vocal_ai_artifact_reduced_PREMASTER_24-48"
  temp_project = tmp_dir .. "/hangang_shadow_v29_PREMASTER_RENDER.rpp"
elseif mode == "cleanup_light" then
  pattern = "vocal_cleanup_light"
  temp_project = tmp_dir .. "/hangang_shadow_v29_LIGHT_RENDER.rpp"
elseif mode == "cleanup_medium" then
  pattern = "vocal_cleanup_medium"
  temp_project = tmp_dir .. "/hangang_shadow_v29_MEDIUM_RENDER.rpp"
elseif mode == "cleanup_blended" then
  pattern = "vocal_cleanup_blended"
  temp_project = tmp_dir .. "/hangang_shadow_v29_BLENDED_RENDER.rpp"
elseif mode == "vocal_stem" then
  pattern = "vocal_processed_stem"
  temp_project = tmp_dir .. "/hangang_shadow_v29_VOCAL_STEM_RENDER.rpp"
elseif mode == "instrumental_stem" then
  pattern = "instrumental_processed_stem"
  temp_project = tmp_dir .. "/hangang_shadow_v29_INSTRUMENTAL_STEM_RENDER.rpp"
end

local render_end = max_active_item_end() + 3.5
if reaper.GetSetProjectInfo then
  reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
  reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 0, true)
  reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0.0, true)
  reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", render_end, true)
end
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", render_dir, true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", pattern, true)
reaper.UpdateArrange()
reaper.Main_SaveProjectEx(0, temp_project, 0)
log("render prep done mode=" .. tostring(mode) .. " temp_project=" .. temp_project .. " pattern=" .. pattern .. " end=" .. tostring(render_end))
