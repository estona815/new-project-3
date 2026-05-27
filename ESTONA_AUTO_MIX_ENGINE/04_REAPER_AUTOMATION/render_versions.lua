-- ESTONA versioned render helper.
-- Creates render filenames like estona_song_v29_normal_20260525.wav.

local mode = "normal" -- edit or call with extstate in advanced wrappers
local version = reaper.GetExtState("ESTONA_AUTO_MIX_ENGINE", "version")
if version == "" then version = "29" end

local _, project_path = reaper.EnumProjects(-1, "")
local song = project_path:match("([^/\\]+)%.rpp$") or "song"
song = song:gsub("[^%w_%-]+", "_")
local date = os.date("%Y%m%d")
local sep = package.config:sub(1,1)
local script_path = ({reaper.get_action_context()})[2]
local root = script_path:match("^(.*)" .. sep .. "04_REAPER_AUTOMATION" .. sep) or "."
local outdir = root .. sep .. "06_OUTPUTS" .. sep .. "renders"
os.execute('mkdir -p "' .. outdir .. '"')
os.execute('mkdir -p "' .. root .. sep .. "06_OUTPUTS" .. sep .. "logs" .. '"')
local outbase = outdir .. sep .. "estona_" .. song .. "_v" .. version .. "_" .. mode .. "_" .. date

reaper.GetSetProjectInfo_String(0, "RENDER_FILE", outdir, true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", outbase:match("([^/\\]+)$"), true)
reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
reaper.AddProjectMarker2(0, false, 0, 0, "ESTONA render prepared: " .. outbase .. ".wav", -1, 0)
local log = io.open(root .. sep .. "06_OUTPUTS" .. sep .. "logs" .. sep .. "reaper_render_versions_log.txt", "a")
if log then
  log:write(os.date("%Y-%m-%d %H:%M:%S") .. " render prepared " .. outbase .. ".wav\n")
  log:close()
end
reaper.Main_OnCommand(41824, 0) -- File: Render project, using the most recent render settings
