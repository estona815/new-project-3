#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "status=unavailable"
  echo "reason=not_macos"
  exit 0
fi

if [[ ! -d "/Applications/Logic Pro.app" ]]; then
  echo "status=unavailable"
  echo "reason=logic_app_missing"
  exit 0
fi

if ! command -v osascript >/dev/null 2>&1; then
  echo "status=unavailable"
  echo "reason=osascript_missing"
  exit 0
fi

echo "status=available"
echo "logic_app=/Applications/Logic Pro.app"
echo "osascript=$(command -v osascript)"

