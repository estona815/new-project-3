local log_path = "/tmp/codex_hangang_shadow_v29/run_render_custom.log"
os.execute("mkdir -p /tmp/codex_hangang_shadow_v29")
local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\n")
    f:close()
  end
end

local ok, err = xpcall(function()
  local mode = os.getenv("HANGANG_V29_RENDER_MODE") or "master_print"
  log("wrapper start mode=" .. tostring(mode))
  _G.HANGANG_V29_RENDER_MODE = mode
  reaper.Main_openProject("/Users/hantaeheuk/Documents/New project 3/reaper/hangang_shadow_v29_vocal_ai_artifact_reduced/hangang_shadow_mashup_v29_vocal_ai_artifact_reduced.rpp")
  dofile("/Users/hantaeheuk/Documents/New project 3/reaper/hangang_shadow_v29_vocal_ai_artifact_reduced/render_hangang_shadow_v29.lua")
  log("wrapper ok mode=" .. tostring(mode))
end, debug.traceback)

if not ok then
  log("wrapper error: " .. tostring(err))
end

reaper.defer(function()
  reaper.Main_OnCommand(40004, 0)
end)
