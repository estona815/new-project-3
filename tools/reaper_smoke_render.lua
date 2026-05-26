local log_path = "/tmp/codex_reaper_smoke_render.log"
local render_path = "/tmp/codex_reaper_render_test.wav"
local source_path = "/tmp/codex_reaper_source_test.wav"
local project_path = "/tmp/codex_reaper_smoke_render_project.rpp"
local reaper_bin = "/Applications/REAPER.app/Contents/MacOS/REAPER"

local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\n")
    f:close()
  end
end

local function exists(path)
  local f = io.open(path, "rb")
  if f then
    f:close()
    return true
  end
  return false
end

local function api_exists(name)
  if reaper.APIExists then
    return reaper.APIExists(name)
  end
  return false
end

local function write_u16le(file, value)
  file:write(string.char(value & 0xff, (value >> 8) & 0xff))
end

local function write_u32le(file, value)
  file:write(string.char(value & 0xff, (value >> 8) & 0xff, (value >> 16) & 0xff, (value >> 24) & 0xff))
end

local function write_i24le(file, value)
  if value < 0 then
    value = value + 0x1000000
  end
  file:write(string.char(value & 0xff, (value >> 8) & 0xff, (value >> 16) & 0xff))
end

local function write_test_wav(path)
  local sample_rate = 48000
  local channels = 2
  local bits = 24
  local seconds = 2
  local frames = sample_rate * seconds
  local block_align = channels * bits / 8
  local byte_rate = sample_rate * block_align
  local data_size = frames * block_align
  local f = assert(io.open(path, "wb"))
  f:write("RIFF")
  write_u32le(f, 36 + data_size)
  f:write("WAVEfmt ")
  write_u32le(f, 16)
  write_u16le(f, 1)
  write_u16le(f, channels)
  write_u32le(f, sample_rate)
  write_u32le(f, byte_rate)
  write_u16le(f, block_align)
  write_u16le(f, bits)
  f:write("data")
  write_u32le(f, data_size)
  for i = 0, frames - 1 do
    local t = i / sample_rate
    local fade = 1.0
    if i < 1200 then
      fade = i / 1200
    elseif i > frames - 1200 then
      fade = (frames - i) / 1200
    end
    local sample = math.sin(2 * math.pi * 440 * t) * 0.25 * fade
    local integer = math.floor(sample * 8388607)
    write_i24le(f, integer)
    write_i24le(f, integer)
  end
  f:close()
end

local ok, err = xpcall(function()
  os.remove(log_path)
  os.remove(render_path)
  os.remove(source_path)
  os.remove(project_path)
  log("smoke render start")
  log("SWS_CF_GetSWSVersion=" .. tostring(api_exists("CF_GetSWSVersion")))
  log("SWS_BR_GetMouseCursorContext=" .. tostring(api_exists("BR_GetMouseCursorContext")))
  log("ReaPack_BrowsePackages=" .. tostring(api_exists("ReaPack_BrowsePackages")))
  log("ReaPack_GetOwner=" .. tostring(api_exists("ReaPack_GetOwner")))

  reaper.Main_OnCommand(40023, 0) -- File: New project
  local track_index = 0
  reaper.InsertTrackAtIndex(track_index, true)
  local track = reaper.GetTrack(0, track_index)
  reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "CODEX_SMOKE_TEST_TONE", true)

  write_test_wav(source_path)
  log("source_file_exists=" .. tostring(exists(source_path)))
  reaper.SetOnlyTrackSelected(track)
  reaper.InsertMedia(source_path, 0)

  local fx = reaper.TrackFX_AddByName(track, "ReaEQ (Cockos)", false, -1)
  log("ReaEQ_insert_index=" .. tostring(fx))

  reaper.AddProjectMarker2(0, false, 0.0, 0.0, "codex smoke marker", -1, 0)
  reaper.AddProjectMarker2(0, true, 0.0, 2.0, "codex smoke region", -1, 0)

  reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)
  reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 0, true)
  reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
  reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0.0, true)
  reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", 2.0, true)
  reaper.GetSetProjectInfo_String(0, "RENDER_FILE", "/tmp", true)
  reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "codex_reaper_render_test", true)
  reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "evaw", true)

  reaper.UpdateArrange()
  reaper.Main_SaveProjectEx(0, project_path, 0)
  log("project_file_exists=" .. tostring(exists(project_path)))
  local cmd = string.format("%q -newinst -nosplash -renderproject %q", reaper_bin, project_path)
  local code = os.execute(cmd)
  log("render_cli_exit=" .. tostring(code))
  log("render_file_exists_after_renderproject=" .. tostring(exists(render_path)))
end, debug.traceback)

if not ok then
  log("smoke render error: " .. tostring(err))
end

reaper.defer(function()
  reaper.Main_OnCommand(40004, 0)
end)
