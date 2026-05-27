#!/usr/bin/env bash
set -u

echo "macOS plugin path dry-run verification"
for path in \
  "/Library/Audio/Plug-Ins/VST3" \
  "/Library/Audio/Plug-Ins/Components" \
  "$HOME/Library/Audio/Plug-Ins/VST3" \
  "$HOME/Library/Audio/Plug-Ins/Components"; do
  if [[ -d "$path" ]]; then
    echo "[found] $path"
  else
    echo "[missing] $path"
  fi
done
echo "[ok] No plugin scan performed."

