-- ESTONA_AUTO_MIX_ENGINE apply_policy_to_reaper.lua
-- Reads mix_policy.json, finds tracks by name, applies conservative track gain/pan/width hints.
-- Stock FX/JSFX-first. No paid plugin dependency.

local sep = package.config:sub(1,1)
local script_path = ({reaper.get_action_context()})[2]
local root = script_path:match("^(.*)" .. sep .. "04_REAPER_AUTOMATION" .. sep) or "."
local policy_path = root .. sep .. "03_POLICY_ENGINE" .. sep .. "mix_policy.json"
local log_path = root .. sep .. "06_OUTPUTS" .. sep .. "logs" .. sep .. "reaper_apply_policy_log.txt"
local warnings_path = root .. sep .. "06_OUTPUTS" .. sep .. "logs" .. sep .. "reaper_track_match_warnings.json"

local function shell_quote(path)
  return '"' .. tostring(path):gsub('"', '\\"') .. '"'
end

local function append_log(message)
  os.execute('mkdir -p ' .. shell_quote(root .. sep .. "06_OUTPUTS" .. sep .. "logs"))
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S") .. " " .. message .. "\n")
    f:close()
  end
end

local function json_escape(value)
  return tostring(value)
    :gsub("\\", "\\\\")
    :gsub('"', '\\"')
    :gsub("\n", "\\n")
    :gsub("\r", "\\r")
end

local function write_track_match_warnings(warnings)
  os.execute('mkdir -p ' .. shell_quote(root .. sep .. "06_OUTPUTS" .. sep .. "logs"))
  local f = io.open(warnings_path, "w")
  if not f then
    append_log("WARN unable to write track match warnings JSON: " .. warnings_path)
    return
  end
  f:write("{\n")
  f:write('  "engine": "ESTONA_AUTO_MIX_ENGINE",\n')
  f:write('  "warning_type": "uncertain_reaper_track_matches",\n')
  f:write('  "generated_at": "' .. json_escape(os.date("%Y-%m-%d %H:%M:%S")) .. '",\n')
  f:write('  "policy_path": "' .. json_escape(policy_path) .. '",\n')
  f:write('  "warnings": [\n')
  for i, warning in ipairs(warnings) do
    f:write("    {\n")
    f:write('      "track_role": "' .. json_escape(warning.track_role) .. '",\n')
    f:write('      "matched_count": ' .. tostring(warning.matched_count) .. ',\n')
    f:write('      "message": "' .. json_escape(warning.message) .. '"\n')
    f:write("    }" .. (i < #warnings and "," or "") .. "\n")
  end
  f:write("  ]\n")
  f:write("}\n")
  f:close()
end

local function read_file(path)
  local f = io.open(path, "r")
  if not f then return nil end
  local s = f:read("*a"); f:close(); return s
end

local function policy_value(text, key, fallback)
  local block = text:match('"' .. key .. '"%s*:%s*{%s*"value"%s*:%s*([^,%n}]+)')
  if not block then return fallback end
  block = block:gsub('"', ''):gsub("%s+", "")
  return tonumber(block) or block or fallback
end

local function track_name(track)
  local _, name = reaper.GetTrackName(track)
  return (name or ""):lower()
end

local function find_tracks(patterns)
  local hits = {}
  for i = 0, reaper.CountTracks(0)-1 do
    local tr = reaper.GetTrack(0, i)
    local name = track_name(tr)
    for _, pat in ipairs(patterns) do
      if name:find(pat) then table.insert(hits, tr); break end
    end
  end
  return hits
end

local function db_to_amp(db)
  return 10^(db/20)
end

local function trim_tracks(tracks, db)
  for _, tr in ipairs(tracks) do
    local vol = reaper.GetMediaTrackInfo_Value(tr, "D_VOL")
    reaper.SetMediaTrackInfo_Value(tr, "D_VOL", vol * db_to_amp(db))
  end
end

local function add_marker(text)
  reaper.AddProjectMarker2(0, false, 0, 0, text, -1, 0)
end

local policy_text = read_file(policy_path)
if not policy_text then
  append_log("ERROR mix_policy.json not found: " .. policy_path)
  reaper.ShowMessageBox("mix_policy.json not found: " .. policy_path, "ESTONA policy apply", 0)
  return
end

reaper.Undo_BeginBlock()
reaper.PreventUIRefresh(1)
local project = reaper.EnumProjects(-1, "")
reaper.Main_SaveProject(project, true)
local _, project_path = reaper.EnumProjects(-1, "")
if project_path and project_path ~= "" then
  local backup_path = project_path:gsub("%.rpp$", "") .. "_ESTONA_POLICY_BACKUP_" .. os.date("%Y%m%d_%H%M%S") .. ".rpp"
  reaper.Main_SaveProject(project, false)
  local src = io.open(project_path, "rb")
  local dst = io.open(backup_path, "wb")
  if src and dst then
    dst:write(src:read("*a"))
    append_log("backup created: " .. backup_path)
  else
    append_log("WARN backup copy failed for: " .. tostring(project_path))
  end
  if src then src:close() end
  if dst then dst:close() end
end

local lead = find_tracks({"lead", "main", "vocal", "vox"})
local backing = find_tracks({"backing", "double", "harmony", "female", "adlib", "bgv"})
local beat = find_tracks({"beat", "inst", "instrumental"})
local drums = find_tracks({"drum", "kick", "snare"})
local bass = find_tracks({"808", "bass", "sub"})

trim_tracks(lead, policy_value(policy_text, "lead_vocal_gain_db", 0))
trim_tracks(backing, policy_value(policy_text, "backing_vocal_gain_db", 0))

local backing_width = tonumber(policy_value(policy_text, "backing_width_increase", 0)) or 0
for _, tr in ipairs(backing) do
  reaper.SetMediaTrackInfo_Value(tr, "D_WIDTH", math.min(1.8, 1.0 + backing_width))
end

for _, tr in ipairs(lead) do
  local fx = reaper.TrackFX_AddByName(tr, "estona_Vocal_AntiAI_Harsh", false, -1)
  if fx < 0 then append_log("WARN JSFX missing: estona_Vocal_AntiAI_Harsh") end
end
for _, tr in ipairs(beat) do
  local fx = reaper.TrackFX_AddByName(tr, "estona_Vocal_Beat_Glue", false, -1)
  if fx < 0 then append_log("WARN JSFX missing: estona_Vocal_Beat_Glue") end
end
for _, tr in ipairs(drums) do
  local fx = reaper.TrackFX_AddByName(tr, "estona_DigiClip", false, -1)
  if fx < 0 then append_log("WARN JSFX missing: estona_DigiClip") end
end
for _, tr in ipairs(bass) do
  local fx = reaper.TrackFX_AddByName(tr, "estona_MonoSub_Guard", false, -1)
  if fx < 0 then append_log("WARN JSFX missing: estona_MonoSub_Guard") end
end

local track_match_warnings = {}
if #lead == 0 then
  local message = "ESTONA: lead vocal track uncertain - user confirmation needed"
  add_marker(message)
  table.insert(track_match_warnings, {track_role = "lead_vocal", matched_count = #lead, message = message})
end
if #beat == 0 then
  local message = "ESTONA: beat track uncertain - user confirmation needed"
  add_marker(message)
  table.insert(track_match_warnings, {track_role = "beat", matched_count = #beat, message = message})
end
write_track_match_warnings(track_match_warnings)
add_marker("ESTONA policy applied from mix_policy.json; references remain muted/out of premaster by rule")
reaper.SetProjExtState(0, "ESTONA_AUTO_MIX_ENGINE", "last_policy_path", policy_path)
reaper.SetProjExtState(0, "ESTONA_AUTO_MIX_ENGINE", "last_policy_apply_time", os.date("%Y-%m-%d %H:%M:%S"))
append_log("policy applied lead=" .. #lead .. " backing=" .. #backing .. " beat=" .. #beat .. " drums=" .. #drums .. " bass=" .. #bass)

reaper.UpdateArrange()
reaper.PreventUIRefresh(-1)
reaper.Undo_EndBlock("Apply ESTONA mix policy", -1)
