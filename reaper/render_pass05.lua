local root = "/Users/hantaeheuk/Documents/New project 3"
local render_dir = root .. "/renders"
local tmp_dir = "/tmp/codex_fresh_reaper"
local mode = _G.FRESH_RENDER_MODE or os.getenv("FRESH_RENDER_MODE") or "master"
local log_path = tmp_dir .. "/render_pass05.log"

os.execute("mkdir -p " .. tmp_dir)

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

local function set_print_fx_bypass(bypass)
  local tr = find_track("PRINT_MASTER_BUS")
  if not tr then return end
  for i = 0, reaper.TrackFX_GetCount(tr) - 1 do
    reaper.TrackFX_SetEnabled(tr, i, not bypass)
  end
end

local function validate_render_safety()
  local failures = {}
  for _, name in ipairs({
    "REF_BUS",
    "ARTIFACT_QUARANTINE_BUS",
    "QUARANTINE - 03_FX",
    "QUARANTINE - 08_Guitar",
    "Female BGV L - 0 Lead Vocals",
    "Female BGV L - female_vocal_candidate_clean",
    "SUNO_000000_CANDIDATE_BUS",
    "SUNO000000 CANDIDATE - Lead Vocals",
    "SUNO000000 CANDIDATE - Drums",
    "SUNO000000 CANDIDATE - Bass",
    "SUNO000000 CANDIDATE - Synth",
    "SUNO000000 CANDIDATE - Other",
  }) do
    local tr = find_track(name)
    if not tr or reaper.GetMediaTrackInfo_Value(tr, "B_MUTE") < 0.5 then
      failures[#failures + 1] = name .. " is not muted"
    end
  end
  local lead = find_track("12_Vocals")
  if not lead or reaper.GetMediaTrackInfo_Value(lead, "B_MUTE") > 0.5 then
    failures[#failures + 1] = "Lead vocal missing or muted"
  end
  return failures
end

log("render prep start mode=" .. tostring(mode))
local failures = validate_render_safety()
if #failures > 0 then
  for _, failure in ipairs(failures) do log("render safety failure: " .. failure) end
  error("Render blocked: " .. table.concat(failures, "; "))
end

local pattern = "PASS05_MASTER_CLEAN_MELODY_FORWARD_24bit_48k"
local temp_project = tmp_dir .. "/PASS05_MASTER_RENDER.rpp"
if mode == "premaster" then
  pattern = "PASS05_PREMASTER_CLEAN_MELODY_FORWARD_24bit_48k"
  temp_project = tmp_dir .. "/PASS05_PREMASTER_RENDER.rpp"
  set_print_fx_bypass(true)
else
  set_print_fx_bypass(false)
end

local render_end = max_active_item_end() + 4.0
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

if reaper.Main_SaveProjectEx then
  reaper.Main_SaveProjectEx(0, temp_project, 0)
end
log("render prep done mode=" .. tostring(mode) .. " temp_project=" .. temp_project .. " pattern=" .. pattern .. " end=" .. tostring(render_end))
