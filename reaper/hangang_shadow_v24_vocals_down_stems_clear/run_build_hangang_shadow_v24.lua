local log_path = "/tmp/codex_hangang_shadow_v24/run_build.log"
os.execute("mkdir -p /tmp/codex_hangang_shadow_v24")
local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\n")
    f:close()
  end
end

local ok, err = xpcall(function()
  log("wrapper start")
  dofile("/Users/hantaeheuk/Documents/New project 3/reaper/hangang_shadow_v24_vocals_down_stems_clear/build_hangang_shadow_v24_vocals_down_stems_clear.lua")
  log("wrapper ok")
end, debug.traceback)

if not ok then
  log("wrapper error: " .. tostring(err))
end

reaper.defer(function()
  reaper.Main_OnCommand(40004, 0)
end)
