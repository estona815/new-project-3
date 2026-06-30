#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/hantaeheuk/Documents/New project 3"
cd "$ROOT"

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "MISSING: $path" >&2
    exit 1
  fi
  echo "OK: $path"
}

require_file "/Applications/REAPER.app/Contents/MacOS/REAPER"
require_file "/Users/hantaeheuk/Downloads/메시 1 (2).zip"
require_file "$HOME/Library/Application Support/REAPER/Effects/Codex Vocal/vocal_ai_artifact_split_tamer.jsfx"

require_file "MESI_1_SINGLE_PIPELINE.md"
require_file "REAPER_REFERENCE_MIX_PIPELINE.md"
require_file "reports/MESI_1_ACCEPTED_FINAL.json"
require_file "reports/mesi_1_v42_vocal_down_1db_final/actual_reaper_plugin_trace.json"
require_file "renders/mesi_1_v42_vocal_down_1db_final/mesi_1_v42_VOCAL_DOWN_1DB_FINAL_DELIVERABLE.zip"
require_file "renders/mesi_1_v42_vocal_down_1db_final/VOCAL_CLARITY_PASS01_FULL.wav"
require_file "renders/mesi_1_v42_vocal_down_1db_final/VOCAL_CLARITY_PASS01_FULL_320k.mp3"
require_file "renders/mesi_1_v42_vocal_down_1db_final/VOCAL_CLARITY_PASS01_REAPERPRINT_FULL_24-48.wav"
require_file "deliverables/mesi_1_ACCEPTED_FINAL_v42/Mesi_1_ACCEPTED_FINAL_v42.wav"
require_file "deliverables/mesi_1_ACCEPTED_FINAL_v42/Mesi_1_ACCEPTED_FINAL_v42_320k.mp3"

python3 tools/validate_reaper_vocal_chain_gate.py \
  --trace reports/mesi_1_v42_vocal_down_1db_final/actual_reaper_plugin_trace.json

unzip -t renders/mesi_1_v42_vocal_down_1db_final/mesi_1_v42_VOCAL_DOWN_1DB_FINAL_DELIVERABLE.zip >/dev/null

python3 -m py_compile \
  tools/mesi_1_v42_vocal_down_1db_final.py \
  tools/validate_reaper_vocal_chain_gate.py

echo "READY: Mesi v42 baseline is ready for controlled mix/master continuation."
