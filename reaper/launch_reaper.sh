#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v reaper >/dev/null 2>&1; then
  reaper -newinst -reascript "$SCRIPT_DIR/build_project.lua"
else
  open -a "REAPER" --args -newinst -reascript "$SCRIPT_DIR/build_project.lua"
fi
