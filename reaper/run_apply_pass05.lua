local log_path = "/tmp/codex_fresh_reaper/run_apply_pass05.log"
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
  reaper.Main_openProject("/Users/hantaeheuk/Documents/New project 3/reaper/FRESH_MIX_MASTER_PASS_04_SUNO_000000_ALL_INFO.rpp")
  dofile("/Users/hantaeheuk/Documents/New project 3/reaper/apply_pass05_clean_melody_forward.lua")
  log("wrapper ok")
end, debug.traceback)

if not ok then
  log("wrapper error: " .. tostring(err))
end

reaper.defer(function()
  reaper.Main_OnCommand(40004, 0)
end)
