#!/usr/bin/env bash
set -euo pipefail

ROOT="${DALKK_ROOT:-/Users/hantaeheuk/Documents/New project 3}"
SOURCE_DIR="${DALKK_SOURCE_DIR:-/Users/hantaeheuk/Downloads/달까지 사랑해}"
SLUG="${DALKK_SLUG:-dalkkaji_saranghae_v02_final_mseq_reverb_clip}"
PYTHON="${PYTHON:-python3}"
REAPER_BIN="${REAPER_BIN:-/Applications/REAPER.app/Contents/MacOS/REAPER}"

export DALKK_ROOT="$ROOT"
export DALKK_SOURCE_DIR="$SOURCE_DIR"
export DALKK_SLUG="$SLUG"

cd "$ROOT"

"$PYTHON" tools/dalkkaji_saranghae_v01_repair_mix_master.py

if [[ -x "$REAPER_BIN" ]]; then
  "$REAPER_BIN" -newinst -nosplash -new "$ROOT/reaper/dalkkaji_saranghae_v01_repair_mix_master/run_build_FEMALE_TAKE_REPAIR_AND_DOUBLE_COMP_V01.lua"
else
  echo "REAPER binary not found at $REAPER_BIN; audio renders were created, but .rpp plugin-chain rebuild was skipped." >&2
fi

cp -f "$ROOT/renders/$SLUG/${SLUG}_MASTER_24bit.wav" "$ROOT/renders/$SLUG/FINAL_dalkkaji_saranghae_max_chain_24bit.wav"
cp -f "$ROOT/renders/$SLUG/preview_with_female_layer_320k.mp3" "$ROOT/renders/$SLUG/FINAL_dalkkaji_saranghae_max_chain_320k.mp3"

echo "$ROOT/renders/$SLUG/FINAL_dalkkaji_saranghae_max_chain_24bit.wav"
echo "$ROOT/renders/$SLUG/FINAL_dalkkaji_saranghae_max_chain_320k.mp3"
echo "$ROOT/reaper/$SLUG/FEMALE_TAKE_REPAIR_AND_DOUBLE_COMP_V01.rpp"
