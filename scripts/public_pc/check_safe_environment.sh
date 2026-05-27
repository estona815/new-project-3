#!/usr/bin/env bash
set -u

echo "Public PC safe environment check"
echo "No installation will be performed."

for cmd in git python3 python ffmpeg reaper; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "[info] $cmd found at $(command -v "$cmd")"
  else
    echo "[info] $cmd not found"
  fi
done

echo "[ok] Dry-run safety check complete."

