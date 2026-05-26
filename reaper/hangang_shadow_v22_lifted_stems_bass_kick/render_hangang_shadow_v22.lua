local root = "/Users/hantaeheuk/Documents/New project 3"
local project_dir = root .. "/reaper/hangang_shadow_v22_lifted_stems_bass_kick"
local render_dir = root .. "/renders/hangang_shadow_v22_lifted_stems_bass_kick"
local tmp_dir = "/tmp/codex_hangang_shadow_v22"
local mode = _G.HANGANG_V22_RENDER_MODE or os.getenv("HANGANG_V22_RENDER_MODE") or "master_print"
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

local function validate_safety()
  local failures = {}
  for _, name in ipairs({
    "REF_BUS_MUTED",
    "FULL STEM REF - muted original mix",
    "MUTED FEMALE LEAD CANDIDATE - v19 0 Lead Vocals",
    "MUTED V19 INSTRUMENTAL REF",
    "MUTED ARTIFACT CANDIDATE - 8 Guitar",
    "MUTED FEMALE_DOUBLE_LAYER_BUS_ALIGN_FAIL",
    "MUTED FEMALE DOUBLE - 11 Backing_Vocals ALIGN FAIL",
  }) do
    local tr = find_track(name)
    if not tr or reaper.GetMediaTrackInfo_Value(tr, "B_MUTE") < 0.5 then
      failures[#failures + 1] = name .. " is not muted"
    end
  end
  for _, name in ipairs({
    "MALE MAIN - 12 Vocals",
    "MALE_MAIN_VOCAL_BUS",
    "FULL_STEM_MUSIC_BUS",
    "MIX_BUS_MALE_MAIN_COMMERCIAL",
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
local failures = validate_safety()
if #failures > 0 then
  for _, failure in ipairs(failures) do log("render safety failure: " .. failure) end
  error("Render blocked: " .. table.concat(failures, "; "))
end

local pattern = "hangang_shadow_mashup_v22_lifted_stems_bass_kick_REAPERPRINT_24-48"
local temp_project = tmp_dir .. "/hangang_shadow_v22_REAPERPRINT_RENDER.rpp"
if mode == "premaster" then
  pattern = "hangang_shadow_mashup_v22_lifted_stems_bass_kick_PREMASTER_24-48"
  temp_project = tmp_dir .. "/hangang_shadow_v22_PREMASTER_RENDER.rpp"
  set_print_fx_enabled(false)
else
  set_print_fx_enabled(true)
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
