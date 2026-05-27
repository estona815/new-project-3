local tmp_dir = "/tmp/codex_dalkkaji_repair_v01"
local log_path = tmp_dir .. "/run_build.log"
os.execute("mkdir -p " .. string.format("%q", tmp_dir))
os.remove(log_path)

local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\n")
    f:close()
  end
end

local ok, err = xpcall(function()
  log("wrapper start")
  dofile("/Users/hantaeheuk/Documents/New project 3/reaper/dalkkaji_saranghae_v01_repair_mix_master/build_FEMALE_TAKE_REPAIR_AND_DOUBLE_COMP_V01.lua")
  log("wrapper ok")
end, debug.traceback)

if not ok then
  log("wrapper error: " .. tostring(err))
end

reaper.defer(function()
  reaper.Main_OnCommand(40004, 0)
end)
