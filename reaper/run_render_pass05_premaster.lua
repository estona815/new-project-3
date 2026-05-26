local log_path = "/tmp/codex_fresh_reaper/run_render_pass05_premaster.log"
os.execute("mkdir -p /tmp/codex_fresh_reaper")
local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\n")
    f:close()
  end
end

local ok, err = xpcall(function()
  log("wrapper start")
  _G.FRESH_RENDER_MODE = "premaster"
  reaper.Main_openProject("/Users/hantaeheuk/Documents/New project 3/reaper/FRESH_MIX_MASTER_PASS_05_CLEAN_MELODY_FORWARD.rpp")
  dofile("/Users/hantaeheuk/Documents/New project 3/reaper/render_pass05.lua")
  log("wrapper ok")
end, debug.traceback)

if not ok then
  log("wrapper error: " .. tostring(err))
end

reaper.defer(function()
  reaper.Main_OnCommand(40004, 0)
end)
