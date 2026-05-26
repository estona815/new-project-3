local log_path = "/tmp/codex_hangang_shadow_v22/run_render_master.log"
os.execute("mkdir -p /tmp/codex_hangang_shadow_v22")
local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\n")
    f:close()
  end
end

local ok, err = xpcall(function()
  log("wrapper start")
  _G.HANGANG_V22_RENDER_MODE = "master_print"
  reaper.Main_openProject("/Users/hantaeheuk/Documents/New project 3/reaper/hangang_shadow_v22_lifted_stems_bass_kick/hangang_shadow_mashup_v22_lifted_stems_bass_kick.rpp")
  dofile("/Users/hantaeheuk/Documents/New project 3/reaper/hangang_shadow_v22_lifted_stems_bass_kick/render_hangang_shadow_v22.lua")
  log("wrapper ok")
end, debug.traceback)

if not ok then
  log("wrapper error: " .. tostring(err))
end

reaper.defer(function()
  reaper.Main_OnCommand(40004, 0)
end)
