#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAP_DIR="/tmp/codex_fresh_reaper"
WRAP_SCRIPT="$WRAP_DIR/run_build_fresh_mix.lua"
mkdir -p "$WRAP_DIR"
cat > "$WRAP_SCRIPT" <<'LUA'
local log_path = "/tmp/codex_fresh_reaper/build_fresh_mix.log"
local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\n")
    f:close()
  end
end
log("wrapper start")
local ok, err = xpcall(function()
  dofile("/Users/hantaeheuk/Documents/New project 3/reaper/build_fresh_mix.lua")
end, debug.traceback)
if ok then
  log("wrapper ok")
else
  log("wrapper error: " .. tostring(err))
end
LUA
open -n -a "REAPER" --args -newinst -new "$WRAP_SCRIPT"
